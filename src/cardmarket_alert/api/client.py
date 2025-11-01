"""Client for interacting with the Cardmarket API."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
        """Fetch a fresh price snapshot for ``watch_item``.

        The real Cardmarket API exposes a JSON endpoint that returns a list of
        articles (listings) for a product.  The exact schema is not guaranteed
        and varies slightly between documentation revisions, so this
        implementation focuses on the common fields required by the rest of the
        application: price, available quantity, seller and metadata necessary to
        apply language/condition filters.

        The method is intentionally defensive to cope with mocked responses in
        tests and with the API occasionally returning malformed payloads.  Any
        network error or unexpected data structure results in an empty snapshot
        rather than raising – keeping the polling loop resilient.
        """

        endpoint = f"{self.api_base_url.rstrip('/')}/products/{watch_item.product_id}/articles"
        params: dict[str, Any] = {"minQuantity": max(watch_item.filters.min_quantity, 1)}
        if watch_item.filters.language:
            params["language"] = watch_item.filters.language
        if watch_item.filters.condition:
            params["condition"] = watch_item.filters.condition

        try:
            response = requests.get(
                endpoint,
                headers=self.build_headers(),
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        articles = self._extract_articles(payload)
        if not articles:
            return []

        fetched_at = datetime.now(UTC)
        entries: list[PriceEntry] = []
        for article in articles:
            if not self._matches_filters(article, watch_item):
                continue

            price = self._extract_price(article)
            quantity = self._extract_quantity(article)
            if price is None or quantity <= 0:
                continue

            seller = self._extract_seller(article)
            entries.append(
                PriceEntry(
                    fetched_at=fetched_at,
                    price_eur=price,
                    available_quantity=quantity,
                    seller=seller,
                )
            )

        entries.sort(key=lambda entry: entry.price_eur)
        return entries

    def _extract_articles(self, payload: Any) -> list[Mapping[str, Any]]:
        """Normalise the variable article containers used by the API.

        Cardmarket historically exposed either ``{"article": [...]}`` or
        ``{"articles": {"article": [...]}}`` depending on the endpoint.  The
        helper accepts both forms (including the degenerate single-dict case)
        and filters out non-mapping entries so the caller can iterate safely.
        """

        if not isinstance(payload, Mapping):
            return []

        articles: list[Mapping[str, Any]] = []

        def _collect(candidate: Any) -> None:
            if isinstance(candidate, Mapping):
                articles.append(candidate)
            elif isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, Mapping):
                        articles.append(item)

        if "article" in payload:
            _collect(payload["article"])

        articles_container = payload.get("articles")
        if isinstance(articles_container, Mapping) and "article" in articles_container:
            _collect(articles_container["article"])
        elif isinstance(articles_container, list):
            for item in articles_container:
                _collect(item)

        return articles

    def _matches_filters(self, article: Mapping[str, Any], watch_item: WatchItem) -> bool:
        """Return ``True`` when ``article`` matches the watch list filters."""

        filters = watch_item.filters

        language = filters.language
        if language:
            language_info = article.get("language", {})
            if isinstance(language_info, Mapping):
                lang_candidates = {
                    str(language_info.get("abbreviation", "")).lower(),
                    str(language_info.get("languageName", "")).lower(),
                }
            else:
                lang_candidates = {str(language_info).lower()}

            if language.lower() not in lang_candidates:
                return False

        condition = filters.condition
        if condition:
            condition_value = article.get("condition")
            if condition_value is None:
                return False
            if str(condition_value).lower() != condition.lower():
                return False

        min_quantity = max(filters.min_quantity, 1)
        quantity = self._extract_quantity(article)
        if quantity < min_quantity:
            return False

        return True

    @staticmethod
    def _extract_price(article: Mapping[str, Any]) -> float | None:
        price_field = article.get("price")
        if isinstance(price_field, Mapping):
            value = price_field.get("value")
            if value is None:
                value = price_field.get("eur")
        else:
            value = price_field

        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_quantity(article: Mapping[str, Any]) -> int:
        for key in ("count", "quantity", "available", "stock"):
            value = article.get(key)
            if value is not None:
                try:
                    quantity = int(value)
                    return max(quantity, 0)
                except (TypeError, ValueError):
                    continue
        return 0

    @staticmethod
    def _extract_seller(article: Mapping[str, Any]) -> str | None:
        seller = article.get("seller")
        if isinstance(seller, Mapping):
            for key in ("username", "name", "user"):
                value = seller.get(key)
                if value:
                    return str(value)
        elif seller:
            return str(seller)
        return None

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
            return {"ok": True, "checked_at": datetime.now(UTC)}
        except requests.RequestException as exc:  # pragma: no cover - placeholder
            return {"ok": False, "error": str(exc), "checked_at": datetime.now(UTC)}
