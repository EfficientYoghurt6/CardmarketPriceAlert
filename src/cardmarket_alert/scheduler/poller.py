"""Background scheduler responsible for polling the Cardmarket API."""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Iterable

from ..models import WatchItem

logger = logging.getLogger(__name__)


class PollingScheduler:
    """A lightweight scheduler for periodic polling tasks."""

    def __init__(self, interval_seconds: int, task: Callable[[Iterable[WatchItem]], None]) -> None:
        self._interval = interval_seconds
        self._task = task
        self._timer: threading.Timer | None = None
        self._watch_items: list[WatchItem] = []
        self._lock = threading.Lock()
        self._running = False

    def start(self, watch_items: Iterable[WatchItem]) -> None:
        """Start scheduling polling runs."""

        with self._lock:
            self._watch_items = list(watch_items)
            self._running = True
            self._schedule_next()

    def stop(self) -> None:
        """Stop the scheduler."""

        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def update_watch_items(self, watch_items: Iterable[WatchItem]) -> None:
        """Update the watch items without interrupting the schedule."""

        with self._lock:
            self._watch_items = list(watch_items)

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._run_task)
        self._timer.daemon = True
        self._timer.start()

    def _run_task(self) -> None:
        try:
            logger.debug("Running scheduled polling task for %s items", len(self._watch_items))
            self._task(self._watch_items)
        finally:
            self._schedule_next()
