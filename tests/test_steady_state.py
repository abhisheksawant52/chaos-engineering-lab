"""Tests for steady-state comparator logic and hypothesis evaluation."""

import pytest

from chaos_lab.models import SteadyStateHypothesis
from chaos_lab.steady_state import (
    PrometheusClient,
    compare,
    evaluate_hypothesis,
)


@pytest.mark.parametrize(
    ("observed", "comparator", "threshold", "expected"),
    [
        (0.99, "ge", 0.95, True),
        (0.90, "ge", 0.95, False),
        (10.0, "lt", 20.0, True),
        (5.0, "eq", 5.0, True),
        (5.0, "ne", 5.0, False),
        (3.0, "le", 3.0, True),
        (4.0, "gt", 3.0, True),
    ],
)
def test_compare(observed, comparator, threshold, expected) -> None:
    assert compare(observed, comparator, threshold) is expected


def test_compare_unknown_comparator() -> None:
    with pytest.raises(ValueError):
        compare(1.0, "approx", 1.0)  # type: ignore[arg-type]


def test_evaluate_hypothesis_uses_client(monkeypatch) -> None:
    client = PrometheusClient("http://prometheus:9090")
    monkeypatch.setattr(client, "instant_query", lambda q: 0.995)
    hypo = SteadyStateHypothesis(
        name="availability",
        metric='avg(up{job="target"})',
        comparator="ge",
        threshold=0.99,
    )
    obs = evaluate_hypothesis(client, hypo, "steady-state-before")
    assert obs.holds is True
    assert obs.observed == 0.995
    assert obs.phase == "steady-state-before"


def test_evaluate_hypothesis_missing_metric(monkeypatch) -> None:
    client = PrometheusClient("http://prometheus:9090")
    monkeypatch.setattr(client, "instant_query", lambda q: None)
    hypo = SteadyStateHypothesis(
        name="latency", metric="p99", comparator="lt", threshold=0.5
    )
    obs = evaluate_hypothesis(client, hypo, "steady-state-after")
    assert obs.holds is False
    assert obs.observed is None
