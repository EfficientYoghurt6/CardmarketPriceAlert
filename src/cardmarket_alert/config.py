"""Configuration settings for the Cardmarket price alert application."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class PollingConfig:
    """Settings related to polling the Cardmarket API for price updates."""

    interval_seconds: int = 900
    """How frequently to poll for updates."""

    max_concurrent_requests: int = 4
    """Upper bound on concurrent API calls to avoid hitting rate limits."""


@dataclass(slots=True)
class AppConfig:
    """Top-level configuration for the application."""

    environment: Literal["development", "production"] = "development"
    data_directory: Path = field(default_factory=lambda: Path("data"))
    polling: PollingConfig = field(default_factory=PollingConfig)

    def ensure_data_directories(self) -> None:
        """Create data directories required by the application."""

        self.data_directory.mkdir(parents=True, exist_ok=True)
        (self.data_directory / "exports").mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = AppConfig()
