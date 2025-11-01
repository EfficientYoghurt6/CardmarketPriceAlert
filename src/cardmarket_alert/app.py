"""Application bootstrapper for the Cardmarket price alert service."""
from __future__ import annotations

import logging
from typing import Iterable

from .config import DEFAULT_CONFIG
from .models import WatchItem
from .scheduler.poller import PollingScheduler
from .services.pricing_service import PricingService
from .services.watchlist_service import WatchlistService
from .web.app import bootstrap_app

logger = logging.getLogger(__name__)


def create_pricing_runtime(pricing_service: PricingService, watchlist_service: WatchlistService) -> PollingScheduler:
    """Create the background scheduler used for polling."""

    def _task(items: Iterable[WatchItem]) -> None:
        items_list = list(items)
        logger.info("Polling %s items", len(items_list))
        pricing_service.poll_watch_items(items_list)

    scheduler = PollingScheduler(DEFAULT_CONFIG.polling.interval_seconds, _task)
    scheduler.start(watchlist_service.all_items())
    return scheduler


def run() -> None:
    """Entrypoint used by the CLI to launch the web UI and scheduler."""

    logging.basicConfig(level=logging.INFO)
    app, pricing_service, watchlist_service = bootstrap_app()
    scheduler = create_pricing_runtime(pricing_service, watchlist_service)
    app.config["scheduler"] = scheduler
    app.config["pricing_service"] = pricing_service
    app.config["watchlist_service"] = watchlist_service

    config = DEFAULT_CONFIG
    app.run(debug=config.environment == "development")


if __name__ == "__main__":  # pragma: no cover - manual execution only
    run()
