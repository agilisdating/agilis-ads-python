"""A read-only run against the API in Test mode.

Runs only with ``pytest -m integration`` and the ``AGILIS_TEST_API_KEY``
environment variable set to a Test-mode key. It reads, and makes two
``dry_run`` calls that create and charge nothing.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path

import pytest

from agilis_ads import Agilis, InvalidRequestError, response_meta

pytestmark = pytest.mark.integration

SAMPLE_PNG = Path(__file__).resolve().parent.parent / "examples" / "sample-offer.png"

# Refusals that depend only on the Test organisation's own state, not on the SDK.
ACCOUNT_STATE_CODES = {"E3", "E4", "E5", "E6", "E9"}


@pytest.fixture(scope="module")
def client() -> Iterator[Agilis]:
    key = os.environ.get("AGILIS_TEST_API_KEY", "").strip()
    if not key:
        pytest.skip("AGILIS_TEST_API_KEY is not set")
    if not key.startswith("pk_test_"):
        pytest.exit("AGILIS_TEST_API_KEY must be a Test-mode key (pk_test_); refusing to run.", 2)
    with Agilis(key) as c:
        assert c.mode == "test"
        yield c


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_reads(client: Agilis) -> None:
    categories = client.categories.list()
    assert categories["categories"]
    meta = response_meta(categories)
    assert meta is not None
    assert meta.status_code == 200

    assert "interests" in client.interests.list()
    assert "categories" in client.event_categories.list()
    assert "currencies" in client.event_currencies.list()
    assert "listing_fee" in client.event_config.get()

    assert "pagination" in client.offers.list({"limit": 5})
    assert "pagination" in client.events.list({"limit": 5})
    first_three = list(islice(client.offers.iter_all({"limit": 1}), 3))
    assert len(first_three) <= 3

    assert "data" in client.webhook_endpoints.list()
    assert "data" in client.webhook_events.list({"limit": 5})


def test_price_estimate(client: Agilis) -> None:
    start = datetime.now(timezone.utc) + timedelta(days=1)
    estimate = client.offers.estimate_price(
        {
            "start_datetime": iso(start),
            "end_datetime": iso(start + timedelta(days=2)),
            "location": [51.5074, -0.1278],
            "radius": 10,
        }
    )
    assert estimate["return_code"] == "S1"


def _skip_if_account_state(error: InvalidRequestError) -> None:
    if error.return_code in ACCOUNT_STATE_CODES:
        pytest.skip(f"refused by the Test organisation's state ({error.return_code})")
    raise error


def test_offer_create_dry_run(client: Agilis) -> None:
    category_id = client.categories.list()["categories"][0]["category_id"]
    start = datetime.now(timezone.utc) + timedelta(days=1)
    try:
        result = client.offers.create(
            {
                "category_id": category_id,
                "title": "SDK dry run",
                "description": "A dry run from the Python SDK tests. Nothing is created.",
                "push_notification_title": "SDK dry run",
                "push_notification_message": "A dry run from the Python SDK tests.",
                "url": "https://www.agilis.dating",
                "image": SAMPLE_PNG,
                "location": [51.5074, -0.1278],
                "radius": 10,
                "start_datetime": iso(start),
                "expiry_datetime": iso(start + timedelta(days=1)),
                "payment_method": "B",
            },
            dry_run=True,
        )
    except InvalidRequestError as error:
        _skip_if_account_state(error)
        return
    assert result.get("dry_run") is True
    assert not result.get("offer_id")


def test_event_publish_dry_run(client: Agilis) -> None:
    start = (datetime.now(timezone.utc) + timedelta(days=14)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    try:
        result = client.events.publish(
            {
                "title": "SDK dry run: evening social",
                "description": "A dry run from the Python SDK tests. Nothing is published.",
                "venue_name": "Test Venue",
                "address": "1 Test Street",
                "city": "London",
                "country_code": "GB",
                "location": [51.5133, -0.13],
                "starts_at": iso(start),
                "ends_at": iso(start + timedelta(hours=3)),
                "url": "https://www.agilis.dating",
                "image": SAMPLE_PNG,
                "payment_method": "B",
            },
            dry_run=True,
        )
    except InvalidRequestError as error:
        _skip_if_account_state(error)
        return
    assert result.get("dry_run") is True
    assert not result.get("event_id")
