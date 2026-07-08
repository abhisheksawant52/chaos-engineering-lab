"""Steady-state hypothesis evaluation against Prometheus."""

from __future__ import annotations

import operator
from typing import Callable

import requests

from .logging_config import get_logger
from .models import (
    Comparator,
    HypothesisObservation,
    SteadyStateHypothesis,
)

logger = get_logger("steady_state")

# Map comparator names to callables of ``(observed, threshold) -> bool``.
_COMPARATORS: dict[Comparator, Callable[[float, float], bool]] = {
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "eq": operator.eq,
    "ne": operator.ne,
}


def compare(observed: float, comparator: Comparator, threshold: float) -> bool:
    """Return whether ``observed <comparator> threshold`` holds.

    Args:
        observed: The measured metric value.
        comparator: One of the supported comparator names.
        threshold: The value to compare against.

    Raises:
        ValueError: If ``comparator`` is not recognised.
    """
    try:
        fn = _COMPARATORS[comparator]
    except KeyError as exc:  # pragma: no cover - guarded by typing
        raise ValueError(f"Unknown comparator: {comparator!r}") from exc
    return fn(observed, threshold)


class PrometheusClient:
    """Thin wrapper over the Prometheus HTTP query API."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def instant_query(self, query: str) -> float | None:
        """Run an instant PromQL query and return the first scalar value.

        Returns ``None`` when the query yields no samples. Network and parsing
        errors are logged and surfaced as ``None`` so a failed scrape does not
        crash the runner.
        """
        url = f"{self.base_url}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": query}, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Prometheus query failed for %r: %s", query, exc)
            return None

        result = payload.get("data", {}).get("result", [])
        if not result:
            return None
        # Instant vectors expose ``value = [timestamp, "value"]``.
        try:
            return float(result[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            logger.warning("Unexpected Prometheus payload for %r", query)
            return None


def evaluate_hypothesis(
    client: PrometheusClient,
    hypothesis: SteadyStateHypothesis,
    phase: str,
) -> HypothesisObservation:
    """Evaluate a single hypothesis and return the observation.

    Args:
        client: Prometheus client used to fetch the metric.
        hypothesis: The hypothesis to evaluate.
        phase: Either ``"steady-state-before"`` or ``"steady-state-after"``.
    """
    observed = client.instant_query(hypothesis.metric)
    holds = observed is not None and compare(
        observed, hypothesis.comparator, hypothesis.threshold
    )
    logger.info(
        "Hypothesis %s [%s]: observed=%s threshold=%s holds=%s",
        hypothesis.name,
        phase,
        observed,
        hypothesis.threshold,
        holds,
    )
    return HypothesisObservation(
        hypothesis=hypothesis.name,
        metric=hypothesis.metric,
        observed=observed,
        threshold=hypothesis.threshold,
        comparator=hypothesis.comparator,
        holds=holds,
        phase=phase,  # type: ignore[arg-type]
    )


def evaluate_all(
    client: PrometheusClient,
    hypotheses: list[SteadyStateHypothesis],
    phase: str,
) -> list[HypothesisObservation]:
    """Evaluate every hypothesis for a given phase."""
    return [evaluate_hypothesis(client, h, phase) for h in hypotheses]
