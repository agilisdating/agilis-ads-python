"""Construction, mode from the key, options, pagination and response metadata."""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

import agilis_ads
from agilis_ads import Agilis, AuthenticationError, response_meta
from agilis_ads._multipart import content_type_for, read_image

from .conftest import FakeApi, json_response


@pytest.mark.parametrize(
    ("key", "mode", "environment"),
    [
        ("pk_test_abc", "test", "TEST"),
        ("pk_live_abc", "live", "LIVE"),
        ("something_else", None, None),
    ],
)
def test_mode_from_key(key: str, mode: str | None, environment: str | None) -> None:
    client = Agilis(key)
    assert client.mode == mode
    assert client.environment == environment
    assert client.is_live is (mode == "live")
    client.close()


def test_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGILIS_API_KEY", "pk_live_fromenv")
    with Agilis() as client:
        assert client.mode == "live"


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGILIS_API_KEY", raising=False)
    with pytest.raises(AuthenticationError, match="AGILIS_API_KEY"):
        Agilis()
    with pytest.raises(AuthenticationError):
        Agilis("  ")


def test_defaults() -> None:
    with Agilis("pk_test_x") as client:
        assert client.base_url == "https://ads.agilis.dating"
        assert client.timeout == 60.0
        assert client.max_retries == 2


def test_negative_retries_refused() -> None:
    with pytest.raises(ValueError):
        Agilis("pk_test_x", max_retries=-1)


def test_timeout_is_sent_per_request() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions.get("timeout"))
        return json_response({"categories": []})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = Agilis("pk_test_x", http_client=http, timeout=7.5)
    client.categories.list()
    assert seen == [{"connect": 7.5, "read": 7.5, "write": 7.5, "pool": 7.5}]
    client.close()
    assert not http.is_closed  # a supplied client is left open
    http.close()


def test_own_http_client_closed() -> None:
    client = Agilis("pk_test_x")
    client.close()
    assert client._http.is_closed


def test_response_meta(client: Agilis, api: FakeApi) -> None:
    api.add(
        httpx.Response(
            200,
            json={"categories": []},
            headers={"X-RateLimit-Remaining": "58", "X-RateLimit-Limit": "60"},
        )
    )
    result = client.categories.list()
    meta = response_meta(result)
    assert meta is not None
    assert meta.status_code == 200
    assert meta.headers["X-RateLimit-Limit"] == "60"
    assert meta.rate_limit_remaining == 58
    assert response_meta({"plain": "dict"}) is None


def page(items: list[int], cursor: str | None) -> httpx.Response:
    return json_response(
        {
            "data": [{"offer_id": i} for i in items],
            "pagination": {
                "limit": 2,
                "count": len(items),
                "has_more": cursor is not None,
                "next_cursor": cursor,
            },
        }
    )


def test_list_returns_one_page(client: Agilis, api: FakeApi) -> None:
    api.add(page([1, 2], "c2"))
    result = client.offers.list({"limit": 2})
    assert [o["offer_id"] for o in result["data"]] == [1, 2]
    assert result["pagination"]["next_cursor"] == "c2"
    assert len(api.requests) == 1


def test_iter_all_follows_cursors(client: Agilis, api: FakeApi) -> None:
    api.add(page([1, 2], "c2"), page([3, 4], "c3"), page([5], None))
    ids = [o["offer_id"] for o in client.offers.iter_all({"limit": 2, "offer_status": "active"})]
    assert ids == [1, 2, 3, 4, 5]
    params = [dict(r.url.params) for r in api.requests]
    assert params == [
        {"limit": "2", "offer_status": "active", "environment": "TEST"},
        {"limit": "2", "offer_status": "active", "environment": "TEST", "cursor": "c2"},
        {"limit": "2", "offer_status": "active", "environment": "TEST", "cursor": "c3"},
    ]


def test_iter_all_is_lazy(client: Agilis, api: FakeApi) -> None:
    api.add(page([1, 2], "c2"), page([3], None))
    iterator = client.events.iter_all()
    assert api.requests == []
    assert next(iterator) == {"offer_id": 1}
    assert len(api.requests) == 1


def test_iter_all_stops_when_has_more_without_cursor(client: Agilis, api: FakeApi) -> None:
    api.add(
        json_response(
            {"data": [{"id": "a"}], "pagination": {"has_more": True, "next_cursor": None}}
        )
    )
    assert [e["id"] for e in client.webhook_events.iter_all()] == ["a"]
    assert len(api.requests) == 1


def test_webhook_events_iter_all(client: Agilis, api: FakeApi) -> None:
    api.add(
        json_response(
            {"data": [{"id": "a"}], "pagination": {"has_more": True, "next_cursor": "n"}}
        ),
        json_response(
            {"data": [{"id": "b"}], "pagination": {"has_more": False, "next_cursor": None}}
        ),
    )
    assert [e["id"] for e in client.webhook_events.iter_all({"limit": 1})] == ["a", "b"]
    assert dict(api.requests[1].url.params) == {"limit": "1", "cursor": "n"}


def test_image_inputs(tmp_path: Path) -> None:
    path = tmp_path / "photo.jpeg"
    path.write_bytes(b"\xff\xd8\xffdata")
    assert read_image(path) == ("photo.jpeg", b"\xff\xd8\xffdata", "image/jpeg")
    assert read_image(str(path)) == ("photo.jpeg", b"\xff\xd8\xffdata", "image/jpeg")
    with path.open("rb") as handle:
        assert read_image(handle) == ("photo.jpeg", b"\xff\xd8\xffdata", "image/jpeg")
    assert read_image(b"GIF89a...") == ("image.gif", b"GIF89a...", "image/gif")
    assert read_image(b"unknown") == ("image", b"unknown", "application/octet-stream")
    assert read_image(("banner.webp", io.BytesIO(b"x"))) == ("banner.webp", b"x", "image/webp")
    assert read_image(("pic.png", b"y")) == ("pic.png", b"y", "image/png")
    with pytest.raises(TypeError):
        read_image(io.StringIO("text"))
    with pytest.raises(TypeError):
        read_image(123)


def test_content_type_from_name() -> None:
    assert content_type_for("A.PNG") == "image/png"
    assert content_type_for("a.jpg") == "image/jpeg"
    assert content_type_for("a.gif") == "image/gif"
    assert content_type_for("noext", b"\x89PNG\r\n\x1a\n") == "image/png"


def test_unsupported_form_value(client: Agilis) -> None:
    with pytest.raises(TypeError):
        client.events.edit(1, {"title": {"nested": "dict"}})  # type: ignore[typeddict-item]


def test_version() -> None:
    assert agilis_ads.__version__ == "0.1.0"


def test_requests_send_no_body_when_none(make_client: Callable[..., Agilis], api: FakeApi) -> None:
    client = make_client()
    client.offers.pause(1)
    assert "content-type" not in api.last.headers
