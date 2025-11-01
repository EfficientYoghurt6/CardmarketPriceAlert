"""Client for interacting with the Cardmarket API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import requests

from ..models import PriceEntry, WatchItem


@dataclass(slots=True)
class CardmarketClient:
    """Handles communication with the Cardmarket API.

    The implementation intentionally keeps a low dependency footprint while
    leaving room for more advanced features such as caching and concurrency.
    """

    api_base_url: str
    app_token: str
    app_secret: str

    def build_headers(self) -> dict[str, str]:
        """Return HTTP headers required for the Cardmarket API.

        The actual API uses OAuth 1.0a; this method is a placeholder to show
        where authentication logic will live. The skeleton returns an empty
        dictionary so the code base remains runnable without credentials.
        """

        return {}

    def fetch_product_snapshot(self, watch_item: WatchItem) -> list[PriceEntry]:
        """Fetch current price snapshot for a watch item.

        This method must be implemented with actual API calls. For now it
        returns an empty list to keep the development skeleton operational.
        """

        _ = watch_item
        # Example of how pagination or filtering could be implemented:
        # response = requests.get(...)
        return []

    def fetch_bulk_snapshots(self, watch_items: Iterable[WatchItem]) -> dict[str, list[PriceEntry]]:
        """Fetch price snapshots for multiple watch items efficiently."""

        snapshots: dict[str, list[PriceEntry]] = {}
        for item in watch_items:
            snapshots[item.product_id] = self.fetch_product_snapshot(item)
        return snapshots

    def health_check(self) -> dict[str, Any]:
        """Perform a lightweight request to ensure the API is reachable."""

        try:
            response = requests.get(self.api_base_url, timeout=5)
            response.raise_for_status()
            return {"ok": True, "checked_at": datetime.utcnow()}
        except requests.RequestException as exc:  # pragma: no cover - placeholder
            return {"ok": False, "error": str(exc), "checked_at": datetime.utcnow()}
