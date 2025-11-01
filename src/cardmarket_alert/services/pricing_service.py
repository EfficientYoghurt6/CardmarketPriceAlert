"""Coordinates polling, persistence, and alerting for price data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from ..api.client import CardmarketClient
from ..models import PriceEntry, WatchItem
from ..notifications.base import Notifier, PriceAlert
from ..storage.repository import CsvPriceRepository


@dataclass(slots=True)
class PricingService:
    """High-level service responsible for persisting price snapshots."""

    client: CardmarketClient
    repository: CsvPriceRepository
    notifier: Notifier

    def poll_watch_items(self, watch_items: Iterable[WatchItem]) -> None:
        """Fetch and store price snapshots for each watch item."""

        snapshots = self.client.fetch_bulk_snapshots(watch_items)
        alerts: list[PriceAlert] = []
        for watch_item in watch_items:
            entries = snapshots.get(watch_item.product_id, [])
            if not entries:
                continue
            self.repository.append_entries(watch_item, entries)
            alert = self._detect_price_movement(watch_item, entries)
            if alert is not None:
                alerts.append(alert)
        if alerts:
            self.notifier.send(alerts)

    def _detect_price_movement(self, watch_item: WatchItem, entries: list[PriceEntry]) -> PriceAlert | None:
        """Placeholder for alerting logic.

        The final implementation will compare price trends and thresholds.
        """

        if not entries:
            return None
        latest = entries[-1]
        message = (
            f"{watch_item.product_name} price is {latest.price_eur:.2f}€ with "
            f"{latest.available_quantity} available copies."
        )
        return PriceAlert(watch_item=watch_item, message=message)

    def seed_demo_data(self, watch_item: WatchItem) -> None:
        """Populate demo CSV data for UI development."""

        now = datetime.utcnow()
        entries = [
            PriceEntry(fetched_at=now, price_eur=29.99, available_quantity=3, seller="DemoShop"),
        ]
        self.repository.append_entries(watch_item, entries)
