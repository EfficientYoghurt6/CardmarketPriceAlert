"""CSV-based storage for captured price data."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..models import PriceEntry, WatchItem


class CsvPriceRepository:
    """Persists price snapshots to CSV files."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)

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
            if is_new_file:
                handle.write("fetched_at,price_eur,available_quantity,seller\n")
            for entry in entries:
                row = asdict(entry)
                row["fetched_at"] = entry.fetched_at.isoformat()
                handle.write(
                    f"{row['fetched_at']},{row['price_eur']},{row['available_quantity']},{row.get('seller','')}\n"
                )

    def export(self, watch_item: WatchItem, destination: Path) -> Path:
        """Copy the CSV for a watch item to a new location."""

        source = self._file_for(watch_item)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination

    def list_exports(self) -> list[Path]:
        """List all stored CSV files."""

        return sorted(self._base_path.glob("*.csv"))

    def last_updated(self, watch_item: WatchItem) -> datetime | None:
        """Return the timestamp of the last appended entry."""

        file_path = self._file_for(watch_item)
        if not file_path.exists():
            return None
        with file_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        if len(lines) <= 1:
            return None
        last_row = lines[-1].strip().split(",")
        return datetime.fromisoformat(last_row[0])
