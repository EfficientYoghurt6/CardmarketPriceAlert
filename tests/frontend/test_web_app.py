from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

import pytest

from cardmarket_alert.api.client import CardmarketClient
from cardmarket_alert.models import PriceEntry, ProductFilter
from cardmarket_alert.notifications.base import Notifier, PriceAlert
from cardmarket_alert.services.pricing_service import PricingService
from cardmarket_alert.services.watchlist_service import WatchlistService
from cardmarket_alert.storage.repository import CsvPriceRepository
from cardmarket_alert.web.app import create_app


class SilentNotifier(Notifier):
    def __init__(self) -> None:
        self.sent_alerts: list[PriceAlert] = []

    def send(self, alerts: Iterable[PriceAlert]) -> None:
        self.sent_alerts.extend(list(alerts))


@pytest.fixture
def web_app(tmp_path):
    repository = CsvPriceRepository(tmp_path)
    notifier = SilentNotifier()
    client = CardmarketClient(api_base_url="https://example.com", app_token="token", app_secret="secret")
    pricing_service = PricingService(client=client, repository=repository, notifier=notifier)
    watchlist_service = WatchlistService()

    filters = ProductFilter(product_url="https://example.com/card")
    watch_item = watchlist_service.add_item("demo", "Demo Product", filters)
    repository.append_entries(
        watch_item,
        [PriceEntry(fetched_at=datetime.now(UTC), price_eur=19.99, available_quantity=3, seller="Seller")],
    )

    app = create_app(pricing_service, watchlist_service)
    app.config.update(TESTING=True)

    return app, pricing_service, watchlist_service


def test_index_renders_watchlist_snapshot(web_app) -> None:
    app, _, _ = web_app
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Demo Product" in response.data
    assert b"Tracked products" in response.data


def test_add_watch_item_updates_service_state(web_app) -> None:
    app, _, watchlist_service = web_app
    client = app.test_client()

    response = client.post(
        "/watchlist",
        data={
            "product_url": "https://example.com/new-card",
            "product_name": "New Card",
            "language": "EN",
            "condition": "Near Mint",
            "min_quantity": "2",
            "product_id": "new-card",
        },
    )

    assert response.status_code == 302
    assert "new-card" in watchlist_service.items
    new_item = watchlist_service.items["new-card"]
    assert new_item.filters.language == "EN"
    assert new_item.filters.min_quantity == 2
