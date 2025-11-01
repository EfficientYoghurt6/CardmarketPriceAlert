# Architecture Overview

The Cardmarket Price Alert project is organised as a modular Python application
with a thin dependency footprint. The system is designed to track Yu-Gi-Oh!
product prices for both singles and sealed items while accounting for
marketplace nuances such as language, condition, and available quantity.

## High-Level Components

```
+---------------------------+     +---------------------------+
|  Web UI (Flask)           |<--->|  Watchlist Service        |
|  - Dashboard              |     |  - In-memory store        |
|  - Watchlist management   |     |  - Filter management      |
|  - Detail views           |     +---------------------------+
|  - CSV export             |
+-------------^-------------+
              |
              v
+---------------------------+     +---------------------------+
|  Pricing Service          |<--->|  Cardmarket API Client    |
|  - Polling orchestration  |     |  - Snapshot retrieval     |
|  - Alert detection        |     |  - Bulk fetch helper      |
|  - Persistence triggers   |     +---------------------------+
+-------------v-------------+
              |
              v
+---------------------------+     +---------------------------+
|  CSV Repository           |     |  Notification Layer       |
|  - Append-only history    |     |  - Popup notifier         |
|  - Export tooling         |     |  - Extensible interface   |
+---------------------------+     +---------------------------+

```

## Polling Flow

1. The background `PollingScheduler` invokes the `PricingService` at configured
   intervals. The scheduler uses the standard library `threading.Timer` to avoid
   heavy dependencies.
2. The `PricingService` requests price snapshots for each watch item via the
   `CardmarketClient`. The client exposes a `fetch_bulk_snapshots` method ready
   for optimisation, such as batching or caching API calls.
3. Received `PriceEntry` values are persisted through the `CsvPriceRepository`.
   The repository writes CSV files per product, ensuring exportability.
4. Significant movements detected by `_detect_price_movement` produce
   `PriceAlert` instances that are forwarded to the `Notifier` abstraction. The
   default notifier is a popup-style console print, but the interface supports
   future channels like email or push notifications.

## Web Application

The Flask UI provides three main experiences:

- **Dashboard:** quick access to recorded CSV exports.
- **Watchlist:** manage tracked products, including filter criteria (language,
  condition, minimum quantity).
- **Detail view:** inspect the stored price history for a product.

Templates and CSS are organised under `src/cardmarket_alert/web/` to keep the UI
self-contained. Styling aims for a modern, glassmorphism-inspired interface
without bringing additional CSS frameworks.

## Data Persistence

All price data is written to CSV files located in the `data/` directory (with an
`exports/` subdirectory for downloadable copies). This format keeps historical
records human-readable and easy to process with spreadsheets or data science
notebooks.

## Extensibility Considerations

- **Notifications:** Implement new `Notifier` subclasses (e.g., email, webhook)
  and inject them into `PricingService`.
- **Scheduling:** Swap the lightweight scheduler for a more robust solution
  (e.g., APScheduler or Celery) when scaling or distributed execution is needed.
- **API Efficiency:** The client is structured to allow request batching,
  caching, or asynchronous execution. Rate limiting can be centralised in the
  client layer.
- **Data Stores:** Replace the CSV repository with a database-backed
  implementation by implementing the same interface.

## Configuration

`AppConfig` in `config.py` holds runtime settings such as polling interval and
storage paths. The design keeps configuration centralised and ready for loading
from environment variables or configuration files.
