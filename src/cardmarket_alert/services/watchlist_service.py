"""Service for managing the watch list."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..models import ProductFilter, WatchItem


@dataclass(slots=True)
class WatchlistService:
    """Manages the in-memory watch list of products."""

    items: dict[str, WatchItem] = field(default_factory=dict)

    def add_item(self, product_id: str, product_name: str, filters: ProductFilter) -> WatchItem:
        watch_item = WatchItem(product_id=product_id, product_name=product_name, filters=filters)
        self.items[product_id] = watch_item
        return watch_item

    def remove_item(self, product_id: str) -> None:
        self.items.pop(product_id, None)

    def all_items(self) -> list[WatchItem]:
        return list(self.items.values())

    def update_filters(self, product_id: str, filters: ProductFilter) -> None:
        if product_id not in self.items:
            raise KeyError(f"Unknown product: {product_id}")
        self.items[product_id].filters = filters

    def load(self, items: Iterable[WatchItem]) -> None:
        self.items = {item.product_id: item for item in items}
