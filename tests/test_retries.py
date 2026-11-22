"""Which requests are retried, how long the waits are, and the Idempotency-Key."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

import agilis_ads
from agilis_ads import Agilis, ApiError, RateLimitError
from agilis_ads._client import parse_retry_after, retry_wait

from .conftest import FakeApi, json_response
from .test_operations import offer_params


def error(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    return json_response({"message": "Server error"}, status, headers)


def test_idempotency_key_is_kept_across_retries(client: Agilis, api: FakeApi) -> None:
    api.add(error(500), error(503), json_response({"return_code": "S1", "offer_id": 46}))
    result = client.offers.create(offer_params())
    assert result["offer_id"] == 46
    assert len(api.requests) == 3
    keys = {r.headers["idempotency-key"] for r in api.requests}
    assert len(keys) == 1
    bodies = {r.content.split(b"\r\n", 1)[1] for r in api.requests}
    assert len(bodies) == 1  # the same body (and image) every time


def test_event_publish_retried_with_same_key(client: Agilis, api: FakeApi) -> None:
    from .test_operations import event_params

    api.add(httpx.ConnectError("boom"), error(502), json_response())
    client.events.publish(event_params(), idempotency_key="k-1")
    assert [r.headers["idempotency-key"] for r in api.requests] == ["k-1", "k-1", "k-1"]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_get_retried_on_5xx(client: Agilis, api: FakeApi, status: int) -> None:
    api.add(error(status), json_response({"categories": []}))
    assert client.categories.list() == {"categories": []}
    assert len(api.requests) == 2


def test_delete_retried_on_5xx(client: Agilis, api: FakeApi) -> None:
    api.add(error(503), json_response())
    client.offers.delete(45)
    assert len(api.requests) == 2


@pytest.mark.parametrize(
    ("name", "call"),
    [
        ("pause", lambda c: c.offers.pause(45)),
        ("cancel", lambda c: c.events.cancel(3104)),
        (
            "estimate",
            lambda c: c.offers.estimate_price(
                {"start_datetime": "a", "end_datetime": "b", "location": [1, 2], "radius": 5}
            ),
        ),
        ("edit", lambda c: c.events.edit(3104, {"title": "x"})),
        ("edit post", lambda c: c.events.edit(3104, {"image": b"\x89PNG\r\n\x1a\n"})),
        ("endpoint update", lambda c: c.webhook_endpoints.update("we_1", {"status": "enabled"})),
    ],
)
def test_post_and_patch_without_key_not_retried_on_5xx(
    client: Agilis, api: FakeApi, name: str, call: Callable[[Agilis], Any]
) -> None:
    api.add(error(500))
    with pytest.raises(ApiError) as info:
        call(client)
    assert info.value.http_status == 500
    assert len(api.requests) == 1
    assert api.sleeps == []


def test_429_retried_for_any_method(client: Agilis, api: FakeApi) -> None:
    api.add(error(429, {"Retry-After": "3"}), json_response({"return_code": "S1"}))
    client.offers.pause(45)
    assert len(api.requests) == 2
    assert api.sleeps == [3.0]


def test_retry_after_is_honoured(client: Agilis, api: FakeApi) -> None:
    api.add(error(503, {"Retry-After": "1.5"}), error(503, {"Retry-After": "12"}), json_response())
    client.categories.list()
    assert api.sleeps == [1.5, 12.0]


def test_backoff_without_retry_after(client: Agilis, api: FakeApi) -> None:
    api.add(error(500), error(500), json_response())
    client.categories.list()
    assert api.sleeps == [0.5, 1.0]


def test_gives_up_after_max_retries(client: Agilis, api: FakeApi) -> None:
    api.add(error(500), error(500), error(500), json_response())
    with pytest.raises(ApiError):
        client.categories.list()
    assert len(api.requests) == 3  # one try and the default 2 retries
    assert len(api.sleeps) == 2


def test_rate_limit_error_after_retries(client: Agilis, api: FakeApi) -> None:
    api.add(*(error(429, {"Retry-After": "2"}) for _ in range(3)))
    with pytest.raises(RateLimitError) as info:
        client.categories.list()
    assert info.value.retry_after == 2.0
    assert info.value.http_status == 429


def test_max_retries_option(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client(max_retries=0)
    api.add(error(500))
    with pytest.raises(ApiError):
        client.categories.list()
    assert len(api.requests) == 1

    client = make_client(max_retries=4)
    api.requests.clear()
    api.add(*(error(500) for _ in range(4)), json_response())
    client.categories.list()
    assert len(api.requests) == 5


def test_connection_errors_and_timeouts_retried(client: Agilis, api: FakeApi) -> None:
    api.add(httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), json_response())
    client.offers.pause(45)  # even a POST without a key: no response means nothing happened yet
    assert len(api.requests) == 3


def test_connection_error_raised_when_retries_run_out(client: Agilis, api: FakeApi) -> None:
    api.add(*(httpx.ConnectError("refused") for _ in range(3)))
    with pytest.raises(agilis_ads.ConnectionError) as info:
        client.categories.list()
    assert info.value.http_status is None
    assert "failed" in str(info.value)


def test_timeout_raised_as_connection_error(
    make_client: Callable[..., Agilis], api: FakeApi
) -> None:
    client = make_client(max_retries=0)
    api.add(httpx.ReadTimeout("slow"))
    with pytest.raises(agilis_ads.ConnectionError, match="timed out"):
        client.categories.list()


def test_non_retryable_status_not_retried(client: Agilis, api: FakeApi) -> None:
    api.add(error(400))
    with pytest.raises(agilis_ads.InvalidRequestError):
        client.categories.list()
    assert len(api.requests) == 1


def test_retry_wait_formula() -> None:
    assert retry_wait(0, None, lambda: 0.5) == 0.5
    assert retry_wait(1, None, lambda: 0.5) == 1.0
    assert retry_wait(2, None, lambda: 0.5) == 2.0
    assert retry_wait(0, None, lambda: 0.0) == 0.375  # -25%
    assert retry_wait(0, None, lambda: 0.999999) == pytest.approx(0.625)  # +25%
    assert retry_wait(10, None, lambda: 0.5) == 8.0  # capped
    assert retry_wait(4, None, lambda: 0.999) == 8.0
    assert retry_wait(3, 20.0, lambda: 0.5) == 20.0  # Retry-After wins


def test_parse_retry_after() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("5") == 5.0
    assert parse_retry_after(" 2.5 ") == 2.5
    assert parse_retry_after("-1") is None
    assert parse_retry_after("soon") is None
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:10 GMT", now=1445412480.0) == 10.0
