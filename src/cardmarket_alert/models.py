"""Domain models used throughout the Cardmarket price alert application."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class ProductFilter:
    """Represents criteria used to identify a product listing on Cardmarket."""

    product_url: str
    language: Optional[str] = None
    condition: Optional[str] = None
    min_quantity: int = 1


@dataclass(slots=True)
class PriceEntry:
    """Single price observation returned from the Cardmarket API."""

    fetched_at: datetime
    price_eur: float
    available_quantity: int
    seller: Optional[str] = None


@dataclass(slots=True)
class PriceHistory:
    """Historic price data captured for a product."""

    product_id: str
    entries: list[PriceEntry] = field(default_factory=list)


@dataclass(slots=True)
class WatchItem:
    """A product tracked by the application."""

    product_id: str
    product_name: str
    filters: ProductFilter
    history: PriceHistory = field(default_factory=lambda: PriceHistory(product_id=""))

    def __post_init__(self) -> None:
        if not self.history.product_id:
            self.history.product_id = self.product_id
