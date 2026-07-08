"""Command-line entrypoint for ``chaos-lab``.

Subcommands:

* ``list``     — list discovered experiments.
* ``validate`` — parse and validate experiment manifests.
* ``run``      — apply an experiment, monitor steady state, and tear down.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from . import __version__
from .catalog import discover_experiments, get_experiment
from .config import get_settings
from .logging_config import configure_logging, get_logger
from .models import ExperimentStatus
from .runner import ExperimentRunner

logger = get_logger("cli")


@click.group()
@click.version_option(__version__, prog_name="chaos-lab")
@click.pass_context
def main(ctx: click.Context) -> None:
    """chaos-lab — run and manage chaos engineering experiments."""
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx.obj = settings


@main.command("list")
@click.option("--engine", type=click.Choice(["litmus", "chaos-mesh"]), default=None)
@click.pass_obj
def list_experiments(settings, engine: str | None) -> None:
    """List experiments discovered under the experiments directory."""
    experiments = discover_experiments(settings.experiments_dir, engine)
    if not experiments:
        click.echo(f"No experiments found under {settings.experiments_dir}.")
        return
    click.echo(f"{'NAME':<20} {'ENGINE':<12} {'DURATION':<9} DESCRIPTION")
    for exp in experiments:
        click.echo(
            f"{exp.name:<20} {exp.engine:<12} {str(exp.duration_seconds) + 's':<9} "
            f"{exp.description}"
        )


@main.command("validate")
@click.option("--engine", type=click.Choice(["litmus", "chaos-mesh"]), default=None)
@click.pass_obj
def validate(settings, engine: str | None) -> None:
    """Validate that every manifest parses and yields a known engine kind."""
    root = settings.experiments_dir
    engines = [engine] if engine else ["litmus", "chaos-mesh"]
    errors = 0
    checked = 0
    for eng in engines:
        for manifest in sorted((root / eng).glob("*.yaml")):
            checked += 1
            try:
                docs = list(yaml.safe_load_all(manifest.read_text(encoding="utf-8")))
                if not any(isinstance(d, dict) and d.get("kind") for d in docs):
                    raise ValueError("no resource with a 'kind' field")
                click.echo(f"OK   {manifest}")
            except (yaml.YAMLError, ValueError, OSError) as exc:
                errors += 1
                click.echo(f"FAIL {manifest}: {exc}")
    click.echo(f"\nChecked {checked} manifest(s); {errors} error(s).")
    if errors:
        sys.exit(1)


@main.command("run")
@click.argument("experiment")
@click.option("--engine", type=click.Choice(["litmus", "chaos-mesh"]), default=None)
@click.option("--dry-run", is_flag=True, help="Preview without applying the manifest.")
@click.pass_obj
def run(settings, experiment: str, engine: str | None, dry_run: bool) -> None:
    """Run EXPERIMENT by name (see ``chaos-lab list``)."""
    exp = get_experiment(settings.experiments_dir, experiment, engine)
    if exp is None:
        raise click.ClickException(
            f"Experiment {experiment!r} not found under {settings.experiments_dir}."
        )
    runner = ExperimentRunner(settings)
    result = runner.run(exp, dry_run=dry_run)

    click.echo(f"\nExperiment : {result.experiment}")
    click.echo(f"Engine     : {result.engine}")
    click.echo(f"Status     : {result.status.value}")
    if result.duration_seconds is not None:
        click.echo(f"Duration   : {result.duration_seconds:.1f}s")
    click.echo(f"Message    : {result.message}")
    for obs in result.observations:
        mark = "✓" if obs.holds else "✗"
        click.echo(f"  {mark} [{obs.phase}] {obs.hypothesis}: observed={obs.observed}")

    if result.status in (ExperimentStatus.FAILED, ExperimentStatus.ABORTED):
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
