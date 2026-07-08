"""The experiment runner: apply a manifest, monitor steady state, tear down.

The runner orchestrates the full lifecycle of a chaos experiment:

1. Evaluate the steady-state hypotheses *before* injecting the fault.
2. Apply the experiment manifest to the cluster.
3. Let the fault run for the experiment's configured duration.
4. Tear the experiment down.
5. Re-evaluate the steady-state hypotheses *after* recovery.

Manifests are applied with ``kubectl`` (kept for parity with the original
lab tooling); the optional ``kubernetes`` client is used to validate cluster
connectivity. Neither needs a live cluster to import this module.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings, get_settings
from .logging_config import get_logger
from .models import Experiment, ExperimentResult, ExperimentStatus
from .steady_state import PrometheusClient, evaluate_all

logger = get_logger("runner")

KUBECTL_TIMEOUT_SECONDS = 120


class KubectlError(RuntimeError):
    """Raised when a ``kubectl`` invocation fails."""


def _run_kubectl(args: list[str], kubeconfig: Path | None = None) -> str:
    """Run ``kubectl`` with the given arguments and return stdout.

    Args:
        args: Arguments passed after ``kubectl``.
        kubeconfig: Optional explicit kubeconfig path.

    Raises:
        KubectlError: If kubectl is missing, times out, or exits non-zero.
    """
    cmd = ["kubectl"]
    if kubeconfig is not None:
        cmd += ["--kubeconfig", str(kubeconfig)]
    cmd += args
    logger.debug("Running: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise KubectlError(
            "kubectl not found. Install from https://kubernetes.io/docs/tasks/tools/"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise KubectlError("kubectl command timed out") from exc
    if proc.returncode != 0:
        raise KubectlError(proc.stderr.strip() or "kubectl exited non-zero")
    return proc.stdout


class ExperimentRunner:
    """Drive chaos experiments end to end and produce structured results."""

    def __init__(
        self,
        settings: Settings | None = None,
        prometheus: PrometheusClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.prometheus = prometheus or PrometheusClient(self.settings.prometheus_url)

    # -- lifecycle steps ---------------------------------------------------

    def apply(self, manifest_path: Path) -> None:
        """Apply an experiment manifest to the cluster."""
        logger.info("Applying manifest %s", manifest_path)
        _run_kubectl(
            ["apply", "-n", self.settings.namespace, "-f", str(manifest_path)],
            self.settings.kubeconfig,
        )

    def teardown(self, manifest_path: Path) -> None:
        """Delete an experiment manifest from the cluster.

        Teardown failures are logged but not raised so a failed cleanup does
        not mask the experiment outcome; operators should still inspect logs.
        """
        logger.info("Tearing down manifest %s", manifest_path)
        try:
            _run_kubectl(
                [
                    "delete",
                    "-n",
                    self.settings.namespace,
                    "-f",
                    str(manifest_path),
                    "--ignore-not-found",
                ],
                self.settings.kubeconfig,
            )
        except KubectlError as exc:
            logger.warning("Teardown reported an error: %s", exc)

    # -- orchestration -----------------------------------------------------

    def run(self, experiment: Experiment, dry_run: bool = False) -> ExperimentResult:
        """Run a single experiment and return its :class:`ExperimentResult`.

        Args:
            experiment: The experiment to execute.
            dry_run: When true, no manifest is applied or deleted; steady-state
                hypotheses are still evaluated so operators can preview blast
                radius safely.
        """
        started = datetime.now(timezone.utc)
        result = ExperimentResult(
            experiment=experiment.name,
            engine=experiment.engine,
            status=ExperimentStatus.RUNNING,
            started_at=started,
        )

        # 1. Steady state before.
        before = evaluate_all(
            self.prometheus, experiment.steady_state, "steady-state-before"
        )
        result.observations.extend(before)
        if before and not all(obs.holds for obs in before):
            result.status = ExperimentStatus.ABORTED
            result.ended_at = datetime.now(timezone.utc)
            result.message = "Steady state not met before experiment; aborting."
            logger.warning(result.message)
            return result

        if dry_run:
            result.status = ExperimentStatus.SUCCEEDED
            result.ended_at = datetime.now(timezone.utc)
            result.message = "Dry run: manifest not applied."
            return result

        # 2-4. Apply, wait, tear down.
        try:
            self.apply(experiment.manifest_path)
            logger.info(
                "Experiment %s running for %ss", experiment.name, experiment.duration_seconds
            )
            time.sleep(experiment.duration_seconds)
        except KubectlError as exc:
            result.status = ExperimentStatus.FAILED
            result.ended_at = datetime.now(timezone.utc)
            result.message = f"Failed to apply experiment: {exc}"
            logger.error(result.message)
            return result
        finally:
            self.teardown(experiment.manifest_path)

        # 5. Steady state after recovery.
        after = evaluate_all(
            self.prometheus, experiment.steady_state, "steady-state-after"
        )
        result.observations.extend(after)
        recovered = all(obs.holds for obs in after) if after else True
        result.status = (
            ExperimentStatus.SUCCEEDED if recovered else ExperimentStatus.FAILED
        )
        result.ended_at = datetime.now(timezone.utc)
        result.message = (
            "System recovered to steady state."
            if recovered
            else "System did not recover to steady state."
        )
        logger.info("Experiment %s finished: %s", experiment.name, result.status.value)
        return result
