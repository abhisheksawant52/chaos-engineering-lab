"""Tests for loading experiment manifests from the experiments directory."""

from pathlib import Path

from chaos_lab.catalog import (
    discover_experiments,
    get_experiment,
    load_experiment,
)

# Repository experiments directory, relative to the project root.
EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"


def test_discover_finds_all_engines() -> None:
    experiments = discover_experiments(EXPERIMENTS_DIR)
    names = {e.name for e in experiments}
    # At least one experiment from each engine ships with the repo.
    engines = {e.engine for e in experiments}
    assert "litmus" in engines
    assert "chaos-mesh" in engines
    assert names, "expected manifests to be discovered"


def test_discover_filter_by_engine() -> None:
    mesh = discover_experiments(EXPERIMENTS_DIR, engine="chaos-mesh")
    assert mesh
    assert all(e.engine == "chaos-mesh" for e in mesh)


def test_get_experiment_roundtrip() -> None:
    experiments = discover_experiments(EXPERIMENTS_DIR)
    first = experiments[0]
    found = get_experiment(EXPERIMENTS_DIR, first.name)
    assert found is not None
    assert found.name == first.name


def test_load_experiment_reads_annotations() -> None:
    manifest = EXPERIMENTS_DIR / "chaos-mesh" / "pod-kill.yaml"
    exp = load_experiment(manifest, "chaos-mesh")
    assert exp.engine == "chaos-mesh"
    assert exp.duration_seconds > 0
    assert exp.steady_state, "pod-kill should declare steady-state hypotheses"


def test_missing_experiment_returns_none() -> None:
    assert get_experiment(EXPERIMENTS_DIR, "does-not-exist") is None
