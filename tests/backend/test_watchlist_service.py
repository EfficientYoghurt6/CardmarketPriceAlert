from __future__ import annotations

import pytest

from cardmarket_alert.models import ProductFilter, WatchItem
from cardmarket_alert.services.watchlist_service import WatchlistService


def test_add_and_remove_items() -> None:
    service = WatchlistService()
    filters = ProductFilter(product_url="https://example.com/card")

    item = service.add_item(product_id="demo", product_name="Demo", filters=filters)

    assert service.items["demo"] is item
    assert service.all_items() == [item]

    service.remove_item("demo")
    assert service.items == {}


def test_update_filters_replaces_existing_definition() -> None:
    service = WatchlistService()
    original = ProductFilter(product_url="https://example.com/original", language="EN")
    updated = ProductFilter(product_url="https://example.com/original", language="DE", min_quantity=2)
    service.add_item(product_id="demo", product_name="Demo", filters=original)

    service.update_filters("demo", updated)

    assert service.items["demo"].filters.language == "DE"
    assert service.items["demo"].filters.min_quantity == 2


def test_update_filters_unknown_product_raises() -> None:
    service = WatchlistService()
    filters = ProductFilter(product_url="https://example.com/card")

    with pytest.raises(KeyError):
        service.update_filters("missing", filters)


def test_load_replaces_existing_items() -> None:
    service = WatchlistService()
    filters = ProductFilter(product_url="https://example.com/card")
    items = [WatchItem(product_id="abc", product_name="Alpha", filters=filters)]

    service.load(items)

    assert list(service.items) == ["abc"]
    assert service.items["abc"].product_name == "Alpha"
