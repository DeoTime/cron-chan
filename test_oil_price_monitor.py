"""
Tests for oil_price_monitor.py
"""
import json
import pytest
import responses
import requests

from oil_price_monitor import (
    OIL_PRICES_URL,
    extract_current_price,
    build_discord_message,
    fetch_oil_prices,
    send_discord_notification,
    run,
)


# ---------------------------------------------------------------------------
# extract_current_price
# ---------------------------------------------------------------------------

class TestExtractCurrentPrice:
    def test_dict_with_price_key(self):
        assert extract_current_price({"price": 72.5}) == 72.5

    def test_dict_with_oilPrice_key(self):
        assert extract_current_price({"oilPrice": 80.0}) == 80.0

    def test_dict_with_oil_price_key(self):
        assert extract_current_price({"oil_price": 55.0}) == 55.0

    def test_dict_with_value_key(self):
        assert extract_current_price({"value": 100.0}) == 100.0

    def test_dict_with_amount_key(self):
        assert extract_current_price({"amount": 45.0}) == 45.0

    def test_list_uses_last_entry(self):
        data = [{"price": 50.0}, {"price": 60.0}, {"price": 70.0}]
        assert extract_current_price(data) == 70.0

    def test_list_single_entry(self):
        assert extract_current_price([{"price": 42.0}]) == 42.0

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            extract_current_price([])

    def test_missing_price_key_raises(self):
        with pytest.raises(ValueError, match="Could not find price field"):
            extract_current_price({"unknown_key": 99.0})

    def test_unexpected_type_raises(self):
        with pytest.raises(ValueError, match="Unexpected API response type"):
            extract_current_price("bad_data")  # type: ignore

    def test_price_coerced_to_float(self):
        result = extract_current_price({"price": "65.25"})
        assert isinstance(result, float)
        assert result == 65.25


# ---------------------------------------------------------------------------
# build_discord_message
# ---------------------------------------------------------------------------

class TestBuildDiscordMessage:
    def test_above_threshold_no_content(self):
        payload = build_discord_message(price=75.0, threshold=60.0)
        assert "content" not in payload
        embed = payload["embeds"][0]
        assert "🟢" in embed["fields"][1]["value"]
        assert embed["color"] == 0x44BB44

    def test_below_threshold_has_content_with_ping(self):
        payload = build_discord_message(price=50.0, threshold=60.0)
        assert "@everyone" in payload["content"]
        embed = payload["embeds"][0]
        assert "🔴" in embed["fields"][1]["value"]
        assert embed["color"] == 0xFF4444

    def test_embed_shows_price(self):
        payload = build_discord_message(price=72.34, threshold=60.0)
        assert "$72.34" in payload["embeds"][0]["description"]

    def test_embed_shows_threshold(self):
        payload = build_discord_message(price=72.34, threshold=60.0)
        fields = payload["embeds"][0]["fields"]
        threshold_field = next(f for f in fields if f["name"] == "Threshold")
        assert "$60.00" in threshold_field["value"]

    def test_price_equal_to_threshold_not_below(self):
        payload = build_discord_message(price=60.0, threshold=60.0)
        assert "content" not in payload


# ---------------------------------------------------------------------------
# fetch_oil_prices
# ---------------------------------------------------------------------------

FAKE_WEBHOOK = "https://discord.com/api/webhooks/123/fake"


class TestFetchOilPrices:
    @responses.activate
    def test_returns_parsed_json(self):
        responses.add(
            responses.GET,
            OIL_PRICES_URL,
            json={"price": 68.0},
            status=200,
        )
        data = fetch_oil_prices()
        assert data == {"price": 68.0}

    @responses.activate
    def test_raises_on_http_error(self):
        responses.add(
            responses.GET,
            OIL_PRICES_URL,
            status=500,
        )
        with pytest.raises(requests.HTTPError):
            fetch_oil_prices()


# ---------------------------------------------------------------------------
# send_discord_notification
# ---------------------------------------------------------------------------


class TestSendDiscordNotification:
    @responses.activate
    def test_sends_post_with_json_payload(self):
        responses.add(responses.POST, FAKE_WEBHOOK, status=204)
        payload = {"content": "test", "embeds": []}
        send_discord_notification(payload, webhook_url=FAKE_WEBHOOK)
        assert len(responses.calls) == 1
        assert json.loads(responses.calls[0].request.body) == payload

    @responses.activate
    def test_raises_on_http_error(self):
        responses.add(responses.POST, FAKE_WEBHOOK, status=400, json={"message": "bad"})
        with pytest.raises(requests.HTTPError):
            send_discord_notification({}, webhook_url=FAKE_WEBHOOK)


# ---------------------------------------------------------------------------
# run (integration)
# ---------------------------------------------------------------------------


class TestRun:
    @responses.activate
    def test_run_above_threshold_returns_price(self):
        responses.add(
            responses.GET,
            OIL_PRICES_URL,
            json={"price": 75.0},
            status=200,
        )
        responses.add(responses.POST, FAKE_WEBHOOK, status=204)
        price = run(webhook_url=FAKE_WEBHOOK, threshold=60.0)
        assert price == 75.0

    @responses.activate
    def test_run_below_threshold_sends_ping(self):
        responses.add(
            responses.GET,
            OIL_PRICES_URL,
            json={"price": 45.0},
            status=200,
        )
        responses.add(responses.POST, FAKE_WEBHOOK, status=204)
        price = run(webhook_url=FAKE_WEBHOOK, threshold=60.0)
        assert price == 45.0
        sent_body = json.loads(responses.calls[1].request.body)
        assert "@everyone" in sent_body.get("content", "")

    @responses.activate
    def test_run_raises_on_api_failure(self):
        responses.add(
            responses.GET,
            OIL_PRICES_URL,
            status=503,
        )
        with pytest.raises(requests.HTTPError):
            run(webhook_url=FAKE_WEBHOOK, threshold=60.0)
