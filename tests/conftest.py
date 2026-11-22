from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from email.message import Message
from email.parser import BytesParser
from email.policy import HTTP
from typing import Any

import httpx
import pytest

from agilis_ads import Agilis

TEST_KEY = "pk_test_0123456789abcdefSECRET"
LIVE_KEY = "pk_live_0123456789abcdefSECRET"

Responder = Callable[[httpx.Request], httpx.Response]


def json_response(
    body: Any = None, status: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    if body is None:
        body = {"return_code": "S1"}
    return httpx.Response(status, json=body, headers=headers)


class FakeApi:
    """Records requests and answers them from a queue (or a function)."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.queue: list[httpx.Response | Exception] = []
        self.default: Responder = lambda request: json_response()
        self.sleeps: list[float] = []

    def add(self, *responses: httpx.Response | Exception) -> None:
        self.queue.extend(responses)

    def handler(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        if self.queue:
            item = self.queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return self.default(request)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def api() -> FakeApi:
    return FakeApi()


@pytest.fixture
def make_client(api: FakeApi) -> Iterator[Callable[..., Agilis]]:
    clients: list[Agilis] = []

    def factory(api_key: str = TEST_KEY, **kwargs: Any) -> Agilis:
        http = httpx.Client(transport=httpx.MockTransport(api.handler))
        client = Agilis(api_key, http_client=http, **kwargs)
        client._sleep = api.sleeps.append
        client._random = lambda: 0.5  # no jitter, so waits are exact
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client._http.close()


@pytest.fixture
def client(make_client: Callable[..., Agilis]) -> Agilis:
    return make_client()


def json_body(request: httpx.Request) -> Any:
    assert request.headers["content-type"] == "application/json"
    return json.loads(request.content)


def multipart(request: httpx.Request) -> list[Message]:
    """The parts of a multipart request, in order."""
    content_type = request.headers["content-type"]
    assert content_type.startswith("multipart/form-data; boundary=")
    raw = b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + request.content
    message = BytesParser(policy=HTTP).parsebytes(raw)
    assert message.is_multipart()
    return list(message.iter_parts())


def form_fields(request: httpx.Request) -> list[tuple[str, str]]:
    """``(name, value)`` for each non-file part."""
    fields = []
    for part in multipart(request):
        if part.get_filename() is None:
            name = part.get_param("name", header="content-disposition")
            fields.append((str(name), part.get_payload(decode=True).decode()))  # type: ignore[union-attr]
    return fields


def file_parts(request: httpx.Request) -> list[tuple[str, str, str, bytes]]:
    """``(name, file name, content type, bytes)`` for each file part."""
    files = []
    for part in multipart(request):
        filename = part.get_filename()
        if filename is not None:
            name = part.get_param("name", header="content-disposition")
            payload = part.get_payload(decode=True)
            assert isinstance(payload, bytes)
            files.append((str(name), filename, part.get_content_type(), payload))
    return files
