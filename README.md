# Cardmarket Price Alert

Cardmarket Price Alert is a Python-based web application that tracks prices for
Yu-Gi-Oh! singles and sealed products on Cardmarket. The project focuses on
capturing detailed listing information—language, condition, and available
quantity—while remaining efficient with API usage and storing all observations as
CSV files.

## Features

- Flask-powered web UI with a modern, responsive layout.
- Manage a watchlist directly in the browser with per-product filter criteria.
- View detailed price history for each tracked product.
- Export captured price data as CSV files.
- Background scheduler prepared for efficient polling of the latest Cardmarket
  API (v2.0 placeholder).
- Notification layer starting with popup alerts and ready for other channels
  (email, push, etc.).

## Project Structure

```
├── docs/architecture.md      # System design and extensibility notes
├── src/cardmarket_alert/
│   ├── api/                  # Cardmarket API client
│   ├── notifications/        # Alert abstractions and implementations
│   ├── scheduler/            # Lightweight polling scheduler
│   ├── services/             # Domain services (pricing, watchlist)
│   ├── storage/              # CSV repository for price history
│   ├── web/                  # Flask app, templates, and styling
│   └── app.py                # Runtime bootstrap helpers
└── data/                     # CSV storage (created at runtime)
```

## Getting Started

### Requirements

- Python 3.11+
- [pip](https://pip.pypa.io/)

### Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
pip install --upgrade pip
pip install -r requirements.txt
```

### Running the App

```bash
# Option 1: use Flask's CLI
export FLASK_APP=cardmarket_alert.web.app
flask run

# Option 2: run the module directly
python -m cardmarket_alert
```

The development bootstrap seeds the UI with a demo Yu-Gi-Oh! product and sample
price history. This allows the watchlist and detail views to render without live
API credentials.

### Configuration

Runtime settings live in `src/cardmarket_alert/config.py`. Key options include:

- `polling.interval_seconds`: how often to poll the Cardmarket API.
- `polling.max_concurrent_requests`: placeholder for rate-limit tuning.
- `data_directory`: where CSV files and exports are saved.

## Roadmap

- Implement authenticated requests against the latest Cardmarket API.
- Persist watchlist entries between restarts (e.g., JSON or database storage).
- Add richer analytics to the detail view (charts, trend analysis).
- Extend notifications to email, webhooks, or desktop integrations.
- Optimise polling to batch requests and respect rate limits.

## Contributing

1. Fork the repository and create a feature branch.
2. Install dependencies and ensure linting/tests pass.
3. Submit a pull request describing your changes.

Please see `docs/architecture.md` for guidance on how components interact.
