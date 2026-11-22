"""Error mapping, errors in 200 responses, and keeping the key out of error text."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

import agilis_ads
from agilis_ads import (
    Agilis,
    AgilisError,
    ApiError,
    AuthenticationError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)

from .conftest import TEST_KEY, FakeApi, json_response


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (400, InvalidRequestError),
        (401, AuthenticationError),
        (403, agilis_ads.PermissionError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, InvalidRequestError),
        (429, RateLimitError),
        (500, ApiError),
        (503, ApiError),
        (418, ApiError),
        (302, ApiError),
    ],
)
def test_status_mapping(
    make_client: Callable[..., Agilis], api: FakeApi, status: int, error_type: type[AgilisError]
) -> None:
    client = make_client(max_retries=0)
    api.add(
        json_response(
            {"return_code": "E1", "message": "Nope"}, status, {"X-RateLimit-Remaining": "12"}
        )
    )
    with pytest.raises(error_type) as info:
        client.offers.pause(45)
    err = info.value
    assert isinstance(err, AgilisError)
    assert err.http_status == status
    assert err.return_code == "E1"
    assert err.message == "Nope"
    assert err.body == {"return_code": "E1", "message": "Nope"}
    assert err.headers["x-ratelimit-remaining"] == "12"
    assert str(err) == f"HTTP {status} E1: Nope"


def test_error_code_in_200_response(client: Agilis, api: FakeApi) -> None:
    api.add(
        json_response(
            {
                "return_code": "E3",
                "message": "Your balance is insufficient. Please top up and try again.",
            }
        )
    )
    with pytest.raises(InvalidRequestError) as info:
        client.events.publish(
            {
                "title": "x",
                "description": "y",
                "venue_name": "v",
                "address": "a",
                "city": "c",
                "country_code": "GB",
                "location": [1.0, 2.0],
                "starts_at": "s",
                "ends_at": "e",
                "url": "https://example.com",
                "payment_method": "B",
            }
        )
    assert info.value.http_status == 200
    assert info.value.return_code == "E3"
    assert "balance" in info.value.message
    assert len(api.requests) == 1  # a refusal is never retried


@pytest.mark.parametrize("code", ["S1", "S2"])
def test_success_codes(client: Agilis, api: FakeApi, code: str) -> None:
    api.add(json_response({"return_code": code, "message": "Done"}))
    assert client.offers.resume(45)["return_code"] == code


def test_200_without_return_code_is_success(client: Agilis, api: FakeApi) -> None:
    api.add(json_response({"categories": []}))
    assert client.categories.list() == {"categories": []}


def test_rate_limit_retry_after(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client(max_retries=0)
    api.add(json_response({"message": "Too Many Attempts."}, 429, {"Retry-After": "42"}))
    with pytest.raises(RateLimitError) as info:
        client.categories.list()
    assert info.value.retry_after == 42.0


def test_non_json_error_body(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client(max_retries=0)
    api.add(httpx.Response(502, text="<html>Bad gateway</html>"))
    with pytest.raises(ApiError) as info:
        client.categories.list()
    assert info.value.body == "<html>Bad gateway</html>"
    assert info.value.message == "The API returned HTTP 502."


def test_unauthorised_message(client: Agilis, api: FakeApi) -> None:
    api.add(json_response({"message": "Unauthorised"}, 401))
    with pytest.raises(AuthenticationError, match="Unauthorised"):
        client.categories.list()


def test_key_never_in_error_text(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client(max_retries=0)
    api.add(json_response({"message": f"Key {TEST_KEY} is not valid"}, 401))
    with pytest.raises(AuthenticationError) as info:
        client.categories.list()
    for text in (str(info.value), repr(info.value), info.value.message):
        assert TEST_KEY not in text
        assert "[redacted]" in text

    api.add(httpx.ConnectError(f"failed for {TEST_KEY}"))
    with pytest.raises(agilis_ads.ConnectionError) as conn:
        client.categories.list()
    assert TEST_KEY not in str(conn.value)
    assert TEST_KEY not in repr(conn.value)


def test_key_not_in_client_repr(client: Agilis) -> None:
    assert TEST_KEY not in repr(client)
    assert TEST_KEY not in str(client)


def test_error_hierarchy() -> None:
    for error_type in (
        AuthenticationError,
        agilis_ads.PermissionError,
        NotFoundError,
        ConflictError,
        InvalidRequestError,
        RateLimitError,
        ApiError,
        agilis_ads.ConnectionError,
        agilis_ads.SignatureVerificationError,
    ):
        assert issubclass(error_type, AgilisError)
    assert agilis_ads.PermissionError.__module__ == "agilis_ads._errors"
    assert "PermissionError" not in agilis_ads.__all__
