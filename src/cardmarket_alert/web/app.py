"""Flask web application serving the user interface."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from ..config import DEFAULT_CONFIG
from ..models import ProductFilter
from ..notifications.base import PopupNotifier
from ..services.pricing_service import PricingService
from ..services.watchlist_service import WatchlistService
from ..storage.repository import CsvPriceRepository
from ..api.client import CardmarketClient


def create_app(pricing_service: PricingService, watchlist_service: WatchlistService) -> Flask:
    app = Flask(__name__)
    app.secret_key = "development-secret-key"

    app.config["pricing_service"] = pricing_service
    app.config["watchlist_service"] = watchlist_service

    def _build_watchlist_snapshot() -> list[dict[str, Any]]:
        snapshot: list[dict[str, Any]] = []
        for watch_item in watchlist_service.all_items():
            csv_path = pricing_service.repository.file_path_for(watch_item)
            entry_count = 0
            if csv_path.exists():
                with csv_path.open("r", encoding="utf-8") as handle:
                    # subtract header if present
                    entry_count = max(sum(1 for _ in handle) - 1, 0)
            snapshot.append(
                {
                    "item": watch_item,
                    "last_updated": pricing_service.repository.last_updated(watch_item),
                    "has_history": csv_path.exists(),
                    "entry_count": entry_count,
                }
            )
        return snapshot

    def _build_export_snapshot() -> list[dict[str, Any]]:
        exports: list[dict[str, Any]] = []
        for export_path in pricing_service.repository.list_exports():
            try:
                stats = export_path.stat()
            except FileNotFoundError:
                continue
            exports.append(
                {
                    "id": export_path.stem,
                    "filename": export_path.name,
                    "modified": datetime.fromtimestamp(stats.st_mtime),
                    "size_kb": round(stats.st_size / 1024, 1),
                }
            )
        exports.sort(key=lambda export: export["modified"], reverse=True)
        return exports

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {"current_year": datetime.utcnow().year}

    @app.route("/")
    def index() -> str:
        watchlist_snapshot = _build_watchlist_snapshot()
        exports = _build_export_snapshot()
        latest_update = max(
            (entry["last_updated"] for entry in watchlist_snapshot if entry["last_updated"]),
            default=None,
        )
        summary = {
            "total_tracked": len(watchlist_snapshot),
            "exports_available": len(exports),
            "latest_update": latest_update,
        }
        return render_template(
            "index.html",
            summary=summary,
            watchlist_snapshot=watchlist_snapshot,
            exports=exports,
        )

    @app.route("/watchlist")
    def watchlist() -> str:
        watchlist_snapshot = _build_watchlist_snapshot()
        watchlist_snapshot.sort(key=lambda entry: entry["item"].product_name.lower())
        return render_template("watchlist.html", watchlist=watchlist_snapshot)

    @app.route("/watchlist/<product_id>")
    def watchlist_detail(product_id: str) -> str:
        item = watchlist_service.items.get(product_id)
        if item is None:
            flash("Unknown product", "error")
            return redirect(url_for("watchlist"))
        csv_path = pricing_service.repository.file_path_for(item)
        history: list[dict[str, object]] = []
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as handle:
                next(handle)  # skip header
                for line in handle:
                    fetched_at, price_eur, available_quantity, seller = line.strip().split(",")
                    history.append(
                        {
                            "fetched_at": datetime.fromisoformat(fetched_at),
                            "price_eur": float(price_eur),
                            "available_quantity": int(available_quantity),
                            "seller": seller,
                        }
                    )
        return render_template("detail.html", item=item, history=history)

    @app.route("/watchlist", methods=["POST"])
    def add_watch_item() -> str:
        data = request.form
        product_url = data.get("product_url")
        product_name = data.get("product_name")
        language = data.get("language") or None
        condition = data.get("condition") or None
        quantity = int(data.get("min_quantity") or 1)
        product_id = data.get("product_id") or product_url or ""
        if not product_url or not product_name:
            flash("Product URL and name are required", "error")
            return redirect(url_for("watchlist"))
        filters = ProductFilter(
            product_url=product_url,
            language=language,
            condition=condition,
            min_quantity=quantity,
        )
        watch_item = watchlist_service.add_item(product_id=product_id, product_name=product_name, filters=filters)
        flash(f"Added {watch_item.product_name} to watch list", "success")
        return redirect(url_for("watchlist"))

    @app.route("/watchlist/<product_id>/remove", methods=["POST"])
    def remove_watch_item(product_id: str) -> str:
        item = watchlist_service.items.get(product_id)
        if item is None:
            flash("Unknown product", "error")
        else:
            watchlist_service.remove_item(product_id)
            flash(f"Stopped tracking {item.product_name}", "success")
        return redirect(url_for("watchlist"))

    @app.route("/exports/<product_id>.csv")
    def export_csv(product_id: str):
        watch_item = watchlist_service.items.get(product_id)
        if watch_item is None:
            flash("Unknown product", "error")
            return redirect(url_for("watchlist"))
        export_path = DEFAULT_CONFIG.data_directory / "exports" / f"{product_id}.csv"
        pricing_service.repository.export(watch_item, export_path)
        return send_file(export_path, as_attachment=True)

    return app


def bootstrap_app() -> tuple[Flask, PricingService, WatchlistService]:
    """Factory used by the entrypoint for running the web UI."""

    config = DEFAULT_CONFIG
    config.ensure_data_directories()
    repository = CsvPriceRepository(config.data_directory)
    watchlist_service = WatchlistService()
    dummy_item = watchlist_service.add_item(
        product_id="demo-blue-eyes",
        product_name="Blue-Eyes White Dragon",
        filters=ProductFilter(
            product_url="https://www.cardmarket.com/en/YuGiOh/Products/Singles/SDK-001",
            language="EN",
            condition="Near Mint",
            min_quantity=1,
        ),
    )
    pricing_service = PricingService(
        client=CardmarketClient(api_base_url="https://api.cardmarket.com/ws/v2.0/output.json", app_token="", app_secret=""),
        repository=repository,
        notifier=PopupNotifier(),
    )
    pricing_service.seed_demo_data(dummy_item)

    app = create_app(pricing_service, watchlist_service)
    return app, pricing_service, watchlist_service
