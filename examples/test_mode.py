"""A short tour in Test mode: reads, a price estimate and a dry-run Offer.

    AGILIS_API_KEY=pk_test_... python examples/test_mode.py

Nothing is created or charged.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agilis_ads import Agilis, AgilisError


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    with Agilis() as client:
        if client.mode != "test":
            print("This example runs in Test mode only: use a pk_test_ key.")
            return 1

        categories = client.categories.list()["categories"]
        print(f"{len(categories)} Offer categories, for example {categories[0]['category_name']!r}")

        for offer in client.offers.iter_all({"limit": 20}):
            print(f"Offer {offer['offer_id']}: {offer['title']} ({offer['offer_status']})")

        start = datetime.now(timezone.utc) + timedelta(days=1)
        estimate = client.offers.estimate_price(
            {
                "start_datetime": iso(start),
                "end_datetime": iso(start + timedelta(days=2)),
                "location": [51.5074, -0.1278],
                "radius": 10,
            }
        )
        print(f"Estimated cost: {estimate['estimated_cost']} {estimate['currency']}")

        try:
            result = client.offers.create(
                {
                    "category_id": categories[0]["category_id"],
                    "title": "20% off this weekend",
                    "description": "Show this offer at the till.",
                    "push_notification_title": "20% off this weekend",
                    "push_notification_message": "Show this at the till for 20% off.",
                    "url": "https://example.com/offer",
                    "image": Path(__file__).with_name("sample-offer.png"),
                    "location": [51.5074, -0.1278],
                    "radius": 10,
                    "start_datetime": iso(start),
                    "expiry_datetime": iso(start + timedelta(days=2)),
                    "payment_method": "B",
                },
                dry_run=True,
            )
            print("Dry run:", dict(result))
        except AgilisError as error:
            print(f"Refused: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
