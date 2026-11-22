"""Every operation's method, path, query, headers and body."""

from __future__ import annotations

import io
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from agilis_ads import Agilis

from .conftest import FakeApi, file_parts, form_fields, json_body

SAMPLE_PNG = Path(__file__).resolve().parent.parent / "examples" / "sample-offer.png"


Call = Callable[[Agilis], Any]

# (name, call, method, path, query)
SIMPLE_OPERATIONS: list[tuple[str, Call, str, str, dict[str, str]]] = [
    ("categories.list", lambda c: c.categories.list(), "GET", "/categories", {}),
    ("interests.list", lambda c: c.interests.list(), "GET", "/interests", {}),
    (
        "offers.list",
        lambda c: c.offers.list({"limit": 50, "offer_status": "active"}),
        "GET",
        "/offers",
        {"environment": "TEST", "limit": "50", "offer_status": "active"},
    ),
    ("offers.pause", lambda c: c.offers.pause(45), "POST", "/offers/45/pause", {}),
    ("offers.resume", lambda c: c.offers.resume(45), "POST", "/offers/45/resume", {}),
    (
        "offers.analytics",
        lambda c: c.offers.analytics(45, {"interval": "7d"}),
        "GET",
        "/offers/45/analytics",
        {"interval": "7d"},
    ),
    ("offers.delete", lambda c: c.offers.delete(45), "DELETE", "/offers/45", {}),
    (
        "offers.delete dry_run",
        lambda c: c.offers.delete(45, dry_run=True),
        "DELETE",
        "/offers/45",
        {"dry_run": "true"},
    ),
    (
        "event_categories.list",
        lambda c: c.event_categories.list(),
        "GET",
        "/event-categories",
        {},
    ),
    (
        "event_currencies.list",
        lambda c: c.event_currencies.list(),
        "GET",
        "/event-currencies",
        {},
    ),
    ("event_config.get", lambda c: c.event_config.get(), "GET", "/event-config", {}),
    (
        "events.list",
        lambda c: c.events.list({"event_status": "upcoming", "owner_user_id": 41}),
        "GET",
        "/events",
        {"environment": "TEST", "event_status": "upcoming", "owner_user_id": "41"},
    ),
    ("events.get", lambda c: c.events.get(3104), "GET", "/events/3104", {}),
    ("events.delete", lambda c: c.events.delete(3104), "DELETE", "/events/3104", {}),
    (
        "events.delete dry_run",
        lambda c: c.events.delete(3104, dry_run=True),
        "DELETE",
        "/events/3104",
        {"dry_run": "true"},
    ),
    ("events.cancel", lambda c: c.events.cancel(3104), "POST", "/events/3104/cancel", {}),
    (
        "events.cancel dry_run",
        lambda c: c.events.cancel(3104, dry_run=True),
        "POST",
        "/events/3104/cancel",
        {"dry_run": "true"},
    ),
    (
        "events.analytics",
        lambda c: c.events.analytics(3104, {"interval": "all"}),
        "GET",
        "/events/3104/analytics",
        {"interval": "all"},
    ),
    (
        "webhook_endpoints.list",
        lambda c: c.webhook_endpoints.list(),
        "GET",
        "/webhook-endpoints",
        {},
    ),
    (
        "webhook_endpoints.get",
        lambda c: c.webhook_endpoints.get("we_123"),
        "GET",
        "/webhook-endpoints/we_123",
        {},
    ),
    (
        "webhook_endpoints.delete",
        lambda c: c.webhook_endpoints.delete("we_123"),
        "DELETE",
        "/webhook-endpoints/we_123",
        {},
    ),
    (
        "webhook_events.list",
        lambda c: c.webhook_events.list({"type": "offer.started", "delivery_success": False}),
        "GET",
        "/webhook-events",
        {"type": "offer.started", "delivery_success": "false"},
    ),
    (
        "webhook_events.get",
        lambda c: c.webhook_events.get("whevt_1"),
        "GET",
        "/webhook-events/whevt_1",
        {},
    ),
]


@pytest.mark.parametrize(
    ("call", "method", "path", "query"),
    [pytest.param(*op[1:], id=op[0]) for op in SIMPLE_OPERATIONS],
)
def test_simple_operation(
    client: Agilis, api: FakeApi, call: Call, method: str, path: str, query: dict[str, str]
) -> None:
    call(client)
    request = api.last
    assert request.method == method
    assert request.url.path == path
    assert dict(request.url.params) == query
    assert request.content == b""
    assert "idempotency-key" not in request.headers


# (name, call, method, path, body)
JSON_OPERATIONS: list[tuple[str, Call, str, str, dict[str, Any]]] = [
    (
        "offers.estimate_price",
        lambda c: c.offers.estimate_price(
            {
                "start_datetime": "2027-07-10T08:00:00Z",
                "end_datetime": "2027-07-12T20:30:00Z",
                "location": [51.5074, -0.1278],
                "radius": 10,
                "gender": ["Male", "Female"],
                "interests": [3, 7],
            }
        ),
        "POST",
        "/offers/price-estimate",
        {
            "start_datetime": "2027-07-10T08:00:00Z",
            "end_datetime": "2027-07-12T20:30:00Z",
            "location": [51.5074, -0.1278],
            "radius": 10,
            "gender": ["Male", "Female"],
            "interests": [3, 7],
            "environment": "TEST",
        },
    ),
    (
        "events.reschedule",
        lambda c: c.events.reschedule(
            3104, {"starts_at": "2027-10-17T18:30:00Z", "ends_at": "2027-10-17T23:00:00Z"}
        ),
        "POST",
        "/events/3104/reschedule",
        {"starts_at": "2027-10-17T18:30:00Z", "ends_at": "2027-10-17T23:00:00Z"},
    ),
    (
        "webhook_endpoints.create",
        lambda c: c.webhook_endpoints.create(
            {"url": "https://example.com/hooks", "enabled_events": ["offer.started"]}
        ),
        "POST",
        "/webhook-endpoints",
        {"url": "https://example.com/hooks", "enabled_events": ["offer.started"]},
    ),
    (
        "webhook_endpoints.update",
        lambda c: c.webhook_endpoints.update("we_123", {"status": "disabled"}),
        "PATCH",
        "/webhook-endpoints/we_123",
        {"status": "disabled"},
    ),
    (
        "webhook_endpoints.roll_secret",
        lambda c: c.webhook_endpoints.roll_secret("we_123", {"expires_in": "24h"}),
        "POST",
        "/webhook-endpoints/we_123/roll-secret",
        {"expires_in": "24h"},
    ),
    (
        "webhook_endpoints.roll_secret no params",
        lambda c: c.webhook_endpoints.roll_secret("we_123"),
        "POST",
        "/webhook-endpoints/we_123/roll-secret",
        {},
    ),
    (
        "webhook_endpoints.send_test",
        lambda c: c.webhook_endpoints.send_test("we_123", {"type": "event.published"}),
        "POST",
        "/webhook-endpoints/we_123/test",
        {"type": "event.published"},
    ),
    (
        "webhook_events.resend",
        lambda c: c.webhook_events.resend("whevt_1", {"endpoint_id": "we_123"}),
        "POST",
        "/webhook-events/whevt_1/resend",
        {"endpoint_id": "we_123"},
    ),
]


@pytest.mark.parametrize(
    ("call", "method", "path", "body"),
    [pytest.param(*op[1:], id=op[0]) for op in JSON_OPERATIONS],
)
def test_json_operation(
    client: Agilis, api: FakeApi, call: Call, method: str, path: str, body: dict[str, Any]
) -> None:
    call(client)
    request = api.last
    assert request.method == method
    assert request.url.path == path
    assert dict(request.url.params) == {}
    assert json_body(request) == body


def test_every_operation_is_covered() -> None:
    names = {op[0].split(" ")[0] for op in SIMPLE_OPERATIONS + JSON_OPERATIONS}
    names |= {"offers.create", "events.preview", "events.publish", "events.edit"}
    assert len(names) == 31  # every operation in the OpenAPI document


def test_common_headers(client: Agilis, api: FakeApi) -> None:
    client.categories.list()
    headers = api.last.headers
    assert headers["x-api-key"] == "pk_test_0123456789abcdefSECRET"
    assert headers["accept"] == "application/json"
    assert re.fullmatch(
        r"agilis-ads-python/0\.1\.0 \(\w+ \d+\.\d+\.\d+\S*\)", headers["user-agent"]
    )
    assert "authorization" not in headers
    assert "pk_test_" not in str(api.last.url)


def test_path_ids_are_escaped(client: Agilis, api: FakeApi) -> None:
    client.webhook_endpoints.get("we/../x?y")
    assert api.last.url.raw_path == b"/webhook-endpoints/we%2F..%2Fx%3Fy"


def test_base_url_option(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client(base_url="https://api.example.test/")
    client.categories.list()
    assert str(api.last.url) == "https://api.example.test/categories"


def test_environment_from_live_key(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client("pk_live_abc")
    client.offers.list()
    assert api.last.url.params["environment"] == "LIVE"


def test_caller_environment_is_kept(client: Agilis, api: FakeApi) -> None:
    client.events.list({"environment": "test"})
    assert api.last.url.params["environment"] == "test"


def offer_params(**overrides: Any) -> Any:
    params: dict[str, Any] = {
        "category_id": 1,
        "title": "20% off summer sale",
        "description": "Discount valid through July",
        "push_notification_title": "20% off this summer",
        "push_notification_message": "Show this at the till for 20% off.",
        "url": "https://example.com/offer",
        "image": SAMPLE_PNG,
        "location": [51.5074, -0.1278],
        "radius": 10,
        "gender": ["Male", "Female"],
        "interests": [3, 7],
        "start_datetime": "2027-07-10T08:00:00Z",
        "expiry_datetime": "2027-07-12T20:30:00Z",
        "payment_method": "B",
    }
    params.update(overrides)
    return params


def test_offers_create_multipart(client: Agilis, api: FakeApi) -> None:
    client.offers.create(offer_params())
    request = api.last
    assert request.method == "POST"
    assert request.url.path == "/offers"
    assert dict(request.url.params) == {}
    uuid.UUID(request.headers["idempotency-key"], version=4)
    fields = form_fields(request)
    assert fields == [
        ("category_id", "1"),
        ("title", "20% off summer sale"),
        ("description", "Discount valid through July"),
        ("push_notification_title", "20% off this summer"),
        ("push_notification_message", "Show this at the till for 20% off."),
        ("url", "https://example.com/offer"),
        ("location[]", "51.5074"),
        ("location[]", "-0.1278"),
        ("radius", "10"),
        ("gender[]", "Male"),
        ("gender[]", "Female"),
        ("interests[]", "3"),
        ("interests[]", "7"),
        ("start_datetime", "2027-07-10T08:00:00Z"),
        ("expiry_datetime", "2027-07-12T20:30:00Z"),
        ("payment_method", "B"),
        ("environment", "TEST"),
    ]
    assert file_parts(request) == [
        ("image", "sample-offer.png", "image/png", SAMPLE_PNG.read_bytes())
    ]


def test_offers_create_own_idempotency_key_and_dry_run(client: Agilis, api: FakeApi) -> None:
    client.offers.create(offer_params(), idempotency_key="my-key-1", dry_run=True)
    assert api.last.headers["idempotency-key"] == "my-key-1"
    assert dict(api.last.url.params) == {"dry_run": "true"}


def test_offers_create_new_key_per_call(client: Agilis, api: FakeApi) -> None:
    client.offers.create(offer_params())
    client.offers.create(offer_params())
    keys = {r.headers["idempotency-key"] for r in api.requests}
    assert len(keys) == 2


def event_params(**overrides: Any) -> Any:
    params: dict[str, Any] = {
        "title": "Beginners Cuban Salsa",
        "description": "Drop-in class for absolute beginners.",
        "venue_name": "Bar Salsa",
        "address": "96 Charing Cross Road",
        "city": "London",
        "country_code": "GB",
        "location": [51.5133, -0.13],
        "starts_at": "2027-10-16T18:30:00Z",
        "ends_at": "2027-10-16T23:00:00Z",
        "url": "https://example.com/classes",
        "price_min": 12,
        "price_max": 12.5,
        "currency": "GBP",
        "image": ("salsa.JPG", b"\xff\xd8\xff\xe0fakejpeg"),
        "crop": {"x": 0, "y": 10, "w": 800},
        "payment_method": "B",
    }
    params.update(overrides)
    return params


def test_events_publish_multipart(client: Agilis, api: FakeApi) -> None:
    client.events.publish(event_params(), dry_run=True)
    request = api.last
    assert request.method == "POST"
    assert request.url.path == "/events"
    assert dict(request.url.params) == {"dry_run": "true"}
    uuid.UUID(request.headers["idempotency-key"], version=4)
    fields = dict(form_fields(request))
    assert [name for name, _ in form_fields(request)].count("location[]") == 2
    assert fields["price_min"] == "12"
    assert fields["price_max"] == "12.5"
    assert fields["crop[x]"] == "0"
    assert fields["crop[y]"] == "10"
    assert fields["crop[w]"] == "800"
    assert "crop" not in fields
    assert fields["environment"] == "TEST"
    assert file_parts(request) == [
        ("image", "salsa.JPG", "image/jpeg", b"\xff\xd8\xff\xe0fakejpeg")
    ]


def test_events_preview_multipart(client: Agilis, api: FakeApi) -> None:
    client.events.preview(
        {
            "title": "Salsa",
            "image": io.BytesIO(b"\x89PNG\r\n\x1a\nrest"),
            "crop": {"x": 1, "y": 2, "w": 3},
        }
    )
    request = api.last
    assert request.method == "POST"
    assert request.url.path == "/events/preview"
    assert "idempotency-key" not in request.headers
    assert form_fields(request) == [
        ("title", "Salsa"),
        ("crop[x]", "1"),
        ("crop[y]", "2"),
        ("crop[w]", "3"),
        ("environment", "TEST"),
    ]
    assert file_parts(request) == [("image", "image.png", "image/png", b"\x89PNG\r\n\x1a\nrest")]


def test_events_edit_without_file_is_post_with_override(client: Agilis, api: FakeApi) -> None:
    client.events.edit(3104, {"title": "Thursday Comedy Club", "location": [51.5, -0.1]})
    request = api.last
    assert request.method == "POST"
    assert request.url.path == "/events/3104"
    assert request.headers["x-http-method-override"] == "PATCH"
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert file_parts(request) == []
    assert form_fields(request) == [
        ("title", "Thursday Comedy Club"),
        ("location[]", "51.5"),
        ("location[]", "-0.1"),
    ]
    assert "environment" not in dict(form_fields(request))


def test_events_edit_with_file_is_post_with_override(client: Agilis, api: FakeApi) -> None:
    client.events.edit(3104, {"title": "New", "image": SAMPLE_PNG})
    request = api.last
    assert request.method == "POST"
    assert request.headers["x-http-method-override"] == "PATCH"
    assert request.url.path == "/events/3104"
    assert form_fields(request) == [("title", "New")]
    assert file_parts(request)[0][:3] == ("image", "sample-offer.png", "image/png")


def test_response_is_the_parsed_json_with_unknown_fields(client: Agilis, api: FakeApi) -> None:
    api.add(
        httpx.Response(
            200,
            json={"categories": [{"category_id": 1, "category_name": "Retail"}], "new_field": 7},
            headers={"X-RateLimit-Remaining": "59"},
        )
    )
    result = client.categories.list()
    assert result["categories"][0]["category_name"] == "Retail"
    assert result["new_field"] == 7  # type: ignore[typeddict-item]
