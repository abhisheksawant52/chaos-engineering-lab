"""Discover and load experiment manifests into :class:`Experiment` objects.

Manifests live under ``<experiments_dir>/<engine>/<name>.yaml``. Steady-state
hypotheses and an optional duration are read from manifest annotations so the
catalog stays a single source of truth:

    metadata:
      annotations:
        chaos-lab.dev/duration-seconds: "60"
        chaos-lab.dev/steady-state: |
          - name: availability
            metric: 'sum(up{job="target"})'
            comparator: ge
            threshold: 1
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .logging_config import get_logger
from .models import Experiment, SteadyStateHypothesis

logger = get_logger("catalog")

DURATION_ANNOTATION = "chaos-lab.dev/duration-seconds"
STEADY_STATE_ANNOTATION = "chaos-lab.dev/steady-state"
DESCRIPTION_ANNOTATION = "chaos-lab.dev/description"

_ENGINE_DIRS: dict[str, str] = {"litmus": "litmus", "chaos-mesh": "chaos-mesh"}


def _load_yaml_docs(path: Path) -> list[dict]:
    """Load all YAML documents from a manifest file."""
    with path.open("r", encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if isinstance(doc, dict)]


def _parse_hypotheses(raw: str) -> list[SteadyStateHypothesis]:
    """Parse steady-state hypotheses from a YAML- or JSON-encoded string."""
    if not raw:
        return []
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        data = json.loads(raw)
    if not isinstance(data, list):
        return []
    return [SteadyStateHypothesis(**item) for item in data]


def load_experiment(path: Path, engine: str) -> Experiment:
    """Load a single manifest file into an :class:`Experiment`.

    Args:
        path: Path to the manifest YAML.
        engine: The chaos engine this manifest targets.

    Raises:
        ValueError: If the manifest has no primary resource with a name.
    """
    docs = _load_yaml_docs(path)
    if not docs:
        raise ValueError(f"No YAML documents found in {path}")

    primary = docs[0]
    metadata = primary.get("metadata", {}) or {}
    annotations = metadata.get("annotations", {}) or {}

    name = metadata.get("name") or path.stem
    duration = int(annotations.get(DURATION_ANNOTATION, 60))
    description = annotations.get(DESCRIPTION_ANNOTATION, "")
    hypotheses = _parse_hypotheses(annotations.get(STEADY_STATE_ANNOTATION, ""))

    return Experiment(
        name=name,
        engine=engine,  # type: ignore[arg-type]
        manifest_path=path,
        description=description,
        duration_seconds=duration,
        steady_state=hypotheses,
    )


def discover_experiments(
    experiments_dir: Path, engine: str | None = None
) -> list[Experiment]:
    """Discover all experiment manifests under ``experiments_dir``.

    Args:
        experiments_dir: Root directory containing per-engine subdirectories.
        engine: If given, only load manifests for this engine.

    Returns:
        Experiments sorted by name.
    """
    experiments: list[Experiment] = []
    engines = [engine] if engine else list(_ENGINE_DIRS)
    for eng in engines:
        subdir = experiments_dir / _ENGINE_DIRS[eng]
        if not subdir.is_dir():
            logger.debug("No manifest directory for engine %s at %s", eng, subdir)
            continue
        for manifest in sorted(subdir.glob("*.yaml")):
            try:
                experiments.append(load_experiment(manifest, eng))
            except (ValueError, yaml.YAMLError) as exc:
                logger.warning("Skipping invalid manifest %s: %s", manifest, exc)
    return sorted(experiments, key=lambda e: e.name)


def get_experiment(
    experiments_dir: Path, name: str, engine: str | None = None
) -> Experiment | None:
    """Return the experiment with ``name`` or ``None`` if not found."""
    for exp in discover_experiments(experiments_dir, engine):
        if exp.name == name:
            return exp
    return None
