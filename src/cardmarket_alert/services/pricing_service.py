"""Coordinates polling, persistence, and alerting for price data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
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

        items = list(watch_items)
        if not items:
            return

        snapshots = self.client.fetch_bulk_snapshots(items)
        alerts: list[PriceAlert] = []
        for watch_item in items:
            entries = snapshots.get(watch_item.product_id, [])
            if not entries:
                continue

            previous_entry = self.repository.latest_entry(watch_item)
            self.repository.append_entries(watch_item, entries)
            alert = self._detect_price_movement(watch_item, entries, previous_entry)
            if alert is not None:
                alerts.append(alert)

        if alerts:
            self.notifier.send(alerts)

    def watchlist_snapshot(self, watch_items: Iterable[WatchItem]) -> list[dict[str, object]]:
        """Summarise repository data for the provided watch list."""

        snapshot: list[dict[str, object]] = []
        for watch_item in watch_items:
            latest_entry = self.repository.latest_entry(watch_item)
            entry_count = self.repository.entry_count(watch_item)
            snapshot.append(
                {
                    "item": watch_item,
                    "latest_entry": latest_entry,
                    "latest_price": latest_entry.price_eur if latest_entry else None,
                    "last_updated": latest_entry.fetched_at if latest_entry else None,
                    "has_history": entry_count > 0,
                    "entry_count": entry_count,
                }
            )
        return snapshot

    def history_for(self, watch_item: WatchItem) -> list[PriceEntry]:
        """Return stored price history for ``watch_item``."""

        return self.repository.load_history(watch_item)

    def export_snapshot(self) -> list[dict[str, object]]:
        """Metadata describing available CSV exports."""

        exports: list[dict[str, object]] = []
        for export_path in self.repository.list_exports():
            try:
                stats = export_path.stat()
            except FileNotFoundError:
                continue
            exports.append(
                {
                    "id": export_path.stem,
                    "path": export_path,
                    "filename": export_path.name,
                    "modified": datetime.fromtimestamp(stats.st_mtime, tz=UTC),
                    "size_kb": round(stats.st_size / 1024, 1),
                }
            )
        exports.sort(key=lambda export: export["modified"], reverse=True)
        return exports

    def export_watch_item(self, watch_item: WatchItem, destination: Path | None = None) -> Path:
        """Export CSV data for ``watch_item`` to ``destination``."""

        return self.repository.export(watch_item, destination)

    def _detect_price_movement(
        self,
        watch_item: WatchItem,
        entries: list[PriceEntry],
        previous_entry: PriceEntry | None = None,
    ) -> PriceAlert | None:
        """Generate a ``PriceAlert`` when the latest snapshot is noteworthy."""

        if not entries:
            return None

        latest = entries[-1]

        if previous_entry is None:
            message = (
                f"Started tracking {watch_item.product_name}: {latest.price_eur:.2f}€ "
                f"with {latest.available_quantity} available copies."
            )
            return PriceAlert(watch_item=watch_item, message=message)

        price_change = latest.price_eur - previous_entry.price_eur
        baseline = previous_entry.price_eur
        percent_change = 0.0
        if baseline > 0:
            percent_change = (price_change / baseline) * 100

        if abs(price_change) < 0.01 and abs(percent_change) < 0.5:
            return None

        direction = "decreased" if price_change < 0 else "increased"
        message = (
            f"{watch_item.product_name} price {direction} to {latest.price_eur:.2f}€ "
            f"({percent_change:+.1f}%) with {latest.available_quantity} copies available."
        )
        return PriceAlert(watch_item=watch_item, message=message)

    def seed_demo_data(self, watch_item: WatchItem) -> None:
        """Populate demo CSV data for UI development."""

        now = datetime.now(UTC)
        entries = [
            PriceEntry(fetched_at=now, price_eur=29.99, available_quantity=3, seller="DemoShop"),
        ]
        self.repository.append_entries(watch_item, entries)
