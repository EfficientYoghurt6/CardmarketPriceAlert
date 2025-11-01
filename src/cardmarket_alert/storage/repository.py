"""CSV-based storage for captured price data."""
from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..models import PriceEntry, WatchItem


class CsvPriceRepository:
    """Persists price snapshots to CSV files."""

    def __init__(self, base_path: Path, export_path: Path | None = None) -> None:
        self._base_path = base_path
        self._export_path = export_path or (base_path / "exports")
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._export_path.mkdir(parents=True, exist_ok=True)

    def _file_for(self, watch_item: WatchItem) -> Path:
        safe_id = watch_item.product_id.replace("/", "_")
        return self._base_path / f"{safe_id}.csv"

    def file_path_for(self, watch_item: WatchItem) -> Path:
        """Public accessor for the CSV path associated with a watch item."""

        return self._file_for(watch_item)

    def append_entries(self, watch_item: WatchItem, entries: Iterable[PriceEntry]) -> None:
        """Append price entries to the CSV file for the watch item."""

        file_path = self._file_for(watch_item)
        is_new_file = not file_path.exists()
        with file_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if is_new_file:
                writer.writerow(["fetched_at", "price_eur", "available_quantity", "seller"])
            for entry in entries:
                row = asdict(entry)
                writer.writerow(
                    [
                        entry.fetched_at.isoformat(),
                        row.get("price_eur", ""),
                        row.get("available_quantity", ""),
                        row.get("seller", ""),
                    ]
                )

    def latest_entry(self, watch_item: WatchItem) -> PriceEntry | None:
        """Return the most recent ``PriceEntry`` for ``watch_item``."""

        history = self.load_history(watch_item, limit=1)
        return history[0] if history else None

    def load_history(self, watch_item: WatchItem, limit: int | None = None) -> list[PriceEntry]:
        """Load stored ``PriceEntry`` objects for ``watch_item``.

        Entries are returned in chronological order. When ``limit`` is provided the
        newest ``limit`` entries are returned.
        """

        file_path = self._file_for(watch_item)
        if not file_path.exists():
            return []

        entries: list[PriceEntry] = []
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    fetched_at = datetime.fromisoformat(row["fetched_at"])
                    price = float(row["price_eur"])
                    quantity = int(row["available_quantity"])
                    seller = row.get("seller") or None
                except (KeyError, TypeError, ValueError):
                    continue
                entries.append(
                    PriceEntry(
                        fetched_at=fetched_at,
                        price_eur=price,
                        available_quantity=quantity,
                        seller=seller,
                    )
                )

        if limit is None or limit >= len(entries):
            return entries

        return entries[-limit:]

    def entry_count(self, watch_item: WatchItem) -> int:
        """Return the number of stored entries for ``watch_item``."""

        file_path = self._file_for(watch_item)
        if not file_path.exists():
            return 0

        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # skip header
            return sum(1 for _ in reader)

    def export(self, watch_item: WatchItem, destination: Path | None = None) -> Path:
        """Copy the CSV for a watch item to a new location.

        When ``destination`` is omitted the CSV is copied into the repository's
        export directory.
        """

        source = self._file_for(watch_item)
        if not source.exists():
            raise FileNotFoundError(f"No history stored for {watch_item.product_id}")

        target = destination or (self._export_path / source.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        return target

    def list_exports(self) -> list[Path]:
        """List all stored CSV files."""

        return sorted(self._export_path.glob("*.csv"))

    def last_updated(self, watch_item: WatchItem) -> datetime | None:
        """Return the timestamp of the last appended entry."""

        latest = self.latest_entry(watch_item)
        return latest.fetched_at if latest else None
