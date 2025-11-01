"""Notification abstractions for the price alert system."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from ..models import WatchItem


@dataclass(slots=True)
class PriceAlert:
    """Container describing a significant price movement."""

    watch_item: WatchItem
    message: str


class Notifier(ABC):
    """Base class for delivering alerts to the user."""

    @abstractmethod
    def send(self, alerts: Iterable[PriceAlert]) -> None:
        """Dispatch the provided alerts."""


class NullNotifier(Notifier):
    """Fallback notifier used during development."""

    def send(self, alerts: Iterable[PriceAlert]) -> None:  # pragma: no cover - placeholder
        _ = list(alerts)


class PopupNotifier(Notifier):
    """Desktop popup implementation placeholder."""

    def send(self, alerts: Iterable[PriceAlert]) -> None:  # pragma: no cover - placeholder
        for alert in alerts:
            print(f"Popup alert: {alert.message}")
