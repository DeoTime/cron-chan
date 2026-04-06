# cron-chan

Automated cron jobs for [Airline Club](https://www.airline-club.com).

## Oil Price Monitor

Fetches the latest oil price from the [Airline Club oil-prices API](https://www.airline-club.com/oil-prices), posts an update to a Discord channel via webhook, and pings `@everyone` when the price dips below a configurable threshold.

### How it works

- Runs on a configurable schedule (default: every hour via GitHub Actions).
- Posts an embedded Discord message with the current oil price on every run.
- Sends an `@everyone` ping when the price falls below `OIL_PRICE_THRESHOLD`.

### Configuration

| Variable | Description | Default |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Discord incoming webhook URL | *(see `.env.example`)* |
| `OIL_PRICE_THRESHOLD` | Price (USD) below which a ping is sent | `60.0` |

Copy `.env.example` to `.env` and fill in your values for local runs, or add them as **Secrets / Variables** in your GitHub repository settings.

### Running locally

```bash
pip install -r requirements.txt
cp .env.example .env   # edit .env with your values
python oil_price_monitor.py
```

### Running tests

```bash
pip install -r requirements.txt responses pytest
pytest test_oil_price_monitor.py -v
```

### GitHub Actions

The workflow `.github/workflows/oil-price-cron.yml` runs automatically every hour.  
You can also trigger it manually from the **Actions** tab using *Run workflow*.

Add the following to your repository:

- **Secret** `DISCORD_WEBHOOK_URL` — your Discord webhook URL.
- **Variable** `OIL_PRICE_THRESHOLD` — price threshold (optional, defaults to `60.0`).
