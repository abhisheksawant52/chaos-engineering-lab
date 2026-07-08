"""Runtime configuration for the chaos lab, sourced from the environment.

Settings are loaded from environment variables (optionally via a local
``.env`` file) using :mod:`pydantic_settings`. See ``.env.example`` for the
documented set of variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ChaosEngine = Literal["litmus", "chaos-mesh"]


class Settings(BaseSettings):
    """Environment-driven configuration for the experiment runner."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kubeconfig: Path = Field(
        default=Path("~/.kube/config").expanduser(),
        alias="KUBECONFIG",
        description="Path to the kubeconfig used to reach the target cluster.",
    )
    namespace: str = Field(
        default="chaos-testing",
        alias="NAMESPACE",
        description="Namespace experiments are applied to.",
    )
    chaos_engine: ChaosEngine = Field(
        default="chaos-mesh",
        alias="CHAOS_ENGINE",
        description="Which chaos platform manifests target: 'litmus' or 'chaos-mesh'.",
    )
    experiments_dir: Path = Field(
        default=Path("experiments"),
        alias="EXPERIMENTS_DIR",
        description="Root directory holding experiment manifests.",
    )
    prometheus_url: str = Field(
        default="http://prometheus:9090",
        alias="PROMETHEUS_URL",
        description="Base URL of the Prometheus used for steady-state checks.",
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Root log level (DEBUG, INFO, WARNING, ERROR).",
    )


def get_settings() -> Settings:
    """Return a fresh :class:`Settings` instance loaded from the environment."""
    return Settings()
