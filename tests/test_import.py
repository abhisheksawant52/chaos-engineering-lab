"""Smoke tests: the package imports and exposes a version."""

import chaos_lab


def test_version() -> None:
    assert chaos_lab.__version__ == "0.1.0"


def test_public_modules_import() -> None:
    from chaos_lab import catalog, cli, config, models, runner, steady_state  # noqa: F401
