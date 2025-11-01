from __future__ import annotations

from datetime import datetime
import pytest
import requests

from cardmarket_alert.api.client import CardmarketClient
from cardmarket_alert.models import PriceEntry, ProductFilter, WatchItem


@pytest.fixture
def client() -> CardmarketClient:
    return CardmarketClient(api_base_url="https://example.com", app_token="token", app_secret="secret")


def test_build_headers_returns_placeholder_dict(client: CardmarketClient) -> None:
    assert client.build_headers() == {}


def test_fetch_bulk_snapshots_reuses_single_fetch(monkeypatch: pytest.MonkeyPatch, client: CardmarketClient) -> None:
    recorded: list[str] = []

    def fake_fetch(self: CardmarketClient, item: WatchItem) -> list[PriceEntry]:  # pragma: no cover - helper
        recorded.append(item.product_id)
        return []

    monkeypatch.setattr(CardmarketClient, "fetch_product_snapshot", fake_fetch)

    filters = ProductFilter(product_url="https://example.com/card")
    items = [
        WatchItem(product_id="abc", product_name="Alpha", filters=filters),
        WatchItem(product_id="def", product_name="Delta", filters=filters),
    ]

    result = client.fetch_bulk_snapshots(items)

    assert result == {"abc": [], "def": []}
    assert recorded == ["abc", "def"]


def test_health_check_success(monkeypatch: pytest.MonkeyPatch, client: CardmarketClient) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:  # pragma: no cover - helper
            return None

    def fake_get(url: str, timeout: int) -> DummyResponse:
        assert url == "https://example.com"
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    result = client.health_check()

    assert result["ok"] is True
    assert isinstance(result["checked_at"], datetime)


def test_health_check_failure(monkeypatch: pytest.MonkeyPatch, client: CardmarketClient) -> None:
    def fake_get(url: str, timeout: int) -> None:  # pragma: no cover - helper
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests, "get", fake_get)

    result = client.health_check()

    assert result["ok"] is False
    assert "boom" in result["error"]
    assert isinstance(result["checked_at"], datetime)
