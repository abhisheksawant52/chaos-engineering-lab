"""Domain models for chaos experiments and their results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Comparator = Literal["lt", "le", "gt", "ge", "eq", "ne"]

# Human-readable symbols for comparators, used in log/report output.
COMPARATOR_SYMBOLS: dict[str, str] = {
    "lt": "<",
    "le": "<=",
    "gt": ">",
    "ge": ">=",
    "eq": "==",
    "ne": "!=",
}


class ExperimentStatus(str, Enum):
    """Terminal or in-progress status of an experiment run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class SteadyStateHypothesis(BaseModel):
    """A single measurable expectation about the system under experiment.

    A hypothesis holds when the ``metric`` (a Prometheus query returning a
    scalar) satisfies ``comparator`` against ``threshold``.
    """

    name: str = Field(description="Human-friendly hypothesis name.")
    metric: str = Field(description="PromQL query returning a single scalar value.")
    comparator: Comparator = Field(description="Comparison operator applied to the metric.")
    threshold: float = Field(description="Value the metric is compared against.")

    def describe(self) -> str:
        """Return a compact string such as ``availability >= 0.99``."""
        return f"{self.name}: value {COMPARATOR_SYMBOLS[self.comparator]} {self.threshold}"


class Experiment(BaseModel):
    """A chaos experiment: a manifest plus its steady-state hypotheses."""

    name: str = Field(description="Unique experiment identifier, e.g. 'pod-delete'.")
    engine: Literal["litmus", "chaos-mesh"] = Field(description="Chaos platform to apply with.")
    manifest_path: Path = Field(description="Path to the experiment manifest on disk.")
    description: str = Field(default="", description="Short human description.")
    duration_seconds: int = Field(
        default=60, ge=0, description="How long to let the fault run before teardown."
    )
    steady_state: list[SteadyStateHypothesis] = Field(
        default_factory=list,
        description="Hypotheses that must hold before and after the experiment.",
    )


class HypothesisObservation(BaseModel):
    """The measured outcome of evaluating one hypothesis at a point in time."""

    hypothesis: str
    metric: str
    observed: float | None
    threshold: float
    comparator: Comparator
    holds: bool
    phase: Literal["steady-state-before", "steady-state-after"]


class ExperimentResult(BaseModel):
    """Structured result produced by running an :class:`Experiment`."""

    experiment: str
    engine: str
    status: ExperimentStatus
    started_at: datetime
    ended_at: datetime | None = None
    observations: list[HypothesisObservation] = Field(default_factory=list)
    message: str = ""

    @property
    def duration_seconds(self) -> float | None:
        """Wall-clock duration of the run, if it has ended."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()
