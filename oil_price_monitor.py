import os
import sys
import json
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

OIL_PRICES_URL = "https://www.airline-club.com/oil-prices"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

OIL_PRICE_THRESHOLD = float(os.environ.get("OIL_PRICE_THRESHOLD", "60.0"))


def fetch_oil_prices(url: str = OIL_PRICES_URL) -> dict:
    """Fetch oil prices from the Airline Club API."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def extract_current_price(data: dict | list) -> float:
    """Extract the current oil price from API response data."""
    if isinstance(data, list):
        if not data:
            raise ValueError("Empty oil price list returned from API")
        entry = data[-1]
    elif isinstance(data, dict):
        entry = data
    else:
        raise ValueError(f"Unexpected API response type: {type(data)}")

    for key in ("price", "oilPrice", "oil_price", "value", "amount"):
        if key in entry:
            return float(entry[key])

    raise ValueError(f"Could not find price field in API response: {entry}")


def should_ping_for_price(data: dict | list) -> bool:
    """Return True when the latest price is new compared to the previous value."""
    if not isinstance(data, list):
        return True
    if len(data) < 2:
        return True

    latest = extract_current_price(data[-1])
    previous = extract_current_price(data[-2])
    return latest != previous


def build_discord_message(price: float, threshold: float, should_ping: bool = True) -> dict:
    """Build the Discord webhook payload."""
    below_threshold = price < threshold
    if below_threshold and should_ping:
        content = (
            f"@everyone 🚨 **Oil price alert!** The current oil price is "
            f"**${price:.2f}**, which is below the threshold of **${threshold:.2f}**."
        )
        color = 0xFF4444
    else:
        content = None
        color = 0x44BB44

    embed = {
        "title": "✈️ Airline Club — Oil Price Update",
        "description": f"Current oil price: **${price:.2f}**",
        "color": color,
        "fields": [
            {
                "name": "Threshold",
                "value": f"${threshold:.2f}",
                "inline": True,
            },
            {
                "name": "Status",
                "value": "🔴 Below threshold" if below_threshold else "🟢 Above threshold",
                "inline": True,
            },
        ],
        "footer": {"text": "airline-club.com/oil-prices"},
    }

    payload: dict = {"embeds": [embed]}
    if content:
        payload["content"] = content

    return payload


def send_discord_notification(payload: dict, webhook_url: str = DISCORD_WEBHOOK_URL) -> None:
    """Send a message to the configured Discord webhook."""
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    logger.info("Discord notification sent (HTTP %s)", response.status_code)


def run(
    oil_url: str = OIL_PRICES_URL,
    webhook_url: str = DISCORD_WEBHOOK_URL,
    threshold: float = OIL_PRICE_THRESHOLD,
) -> float:
    """Main entry point: fetch price, evaluate threshold, notify Discord."""
    if not webhook_url:
        raise ValueError(
            "DISCORD_WEBHOOK_URL environment variable is not set. "
            "Please configure it before running."
        )
    logger.info("Fetching oil prices from %s", oil_url)
    data = fetch_oil_prices(oil_url)

    price = extract_current_price(data)
    ping_for_price = should_ping_for_price(data)
    logger.info("Current oil price: $%.2f (threshold: $%.2f)", price, threshold)

    payload = build_discord_message(price, threshold, should_ping=ping_for_price)
    send_discord_notification(payload, webhook_url)

    if price < threshold:
        logger.warning("Oil price $%.2f is below threshold $%.2f", price, threshold)

    return price


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Error: %s", exc)
        sys.exit(1)
