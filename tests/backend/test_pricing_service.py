from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

import pytest

from cardmarket_alert.models import PriceEntry, ProductFilter, WatchItem
from cardmarket_alert.notifications.base import Notifier, PriceAlert
from cardmarket_alert.services.pricing_service import PricingService
from cardmarket_alert.storage.repository import CsvPriceRepository


class RecordingNotifier(Notifier):
    def __init__(self) -> None:
        self.alerts: list[PriceAlert] = []

    def send(self, alerts: Iterable[PriceAlert]) -> None:
        self.alerts.extend(list(alerts))


class DummyClient:
    def __init__(self, snapshots: dict[str, list[PriceEntry]]) -> None:
        self._snapshots = snapshots

    def fetch_bulk_snapshots(self, watch_items):  # pragma: no cover - delegation helper
        return self._snapshots


@pytest.fixture
def watch_item() -> WatchItem:
    filters = ProductFilter(product_url="https://example.com/card")
    return WatchItem(product_id="demo", product_name="Demo", filters=filters)


def test_poll_watch_items_persists_data_and_notifies(tmp_path, watch_item: WatchItem) -> None:
    entries = [
        PriceEntry(fetched_at=datetime.now(UTC), price_eur=12.5, available_quantity=4, seller="Seller"),
    ]
    client = DummyClient({"demo": entries})
    repository = CsvPriceRepository(tmp_path)
    notifier = RecordingNotifier()
    service = PricingService(client=client, repository=repository, notifier=notifier)

    service.poll_watch_items([watch_item])

    csv_path = repository.file_path_for(watch_item)
    assert csv_path.exists()
    contents = csv_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == "fetched_at,price_eur,available_quantity,seller"
    assert len(contents) == 2
    assert notifier.alerts, "Notifier should receive a price alert"
    assert watch_item.product_name in notifier.alerts[0].message


def test_poll_watch_items_skips_empty_snapshots(tmp_path, watch_item: WatchItem) -> None:
    client = DummyClient({"demo": []})
    repository = CsvPriceRepository(tmp_path)
    notifier = RecordingNotifier()
    service = PricingService(client=client, repository=repository, notifier=notifier)

    service.poll_watch_items([watch_item])

    assert not notifier.alerts
    assert not repository.file_path_for(watch_item).exists()


def test_detect_price_movement_handles_empty_entries(tmp_path, watch_item: WatchItem) -> None:
    client = DummyClient({})
    repository = CsvPriceRepository(tmp_path)
    notifier = RecordingNotifier()
    service = PricingService(client=client, repository=repository, notifier=notifier)

    alert = service._detect_price_movement(watch_item, [])

    assert alert is None
