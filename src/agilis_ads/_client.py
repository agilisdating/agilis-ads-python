from __future__ import annotations

import email.utils
import json as _json
import os
import platform
import random
import time
from datetime import timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Union
from urllib.parse import quote

import httpx

from ._errors import (
    AgilisError,
    ApiError,
    AuthenticationError,
    ConflictError,
    ConnectionError,
    InvalidRequestError,
    NotFoundError,
    PermissionError,
    RateLimitError,
)
from ._multipart import Part, encode_multipart
from ._resources import (
    Categories,
    EventCategories,
    EventConfigResource,
    EventCurrencies,
    Events,
    Interests,
    Offers,
    WebhookEndpoints,
    WebhookEvents,
)
from ._response import AgilisObject, ResponseMeta
from ._version import __version__
from .types import Mode
from .webhooks import Webhooks

__all__ = ["Agilis", "DEFAULT_BASE_URL", "DEFAULT_MAX_RETRIES", "DEFAULT_TIMEOUT"]

DEFAULT_BASE_URL = "https://ads.agilis.dating"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2

_RETRYABLE_5XX = frozenset({500, 502, 503, 504})
_REDACTED = "[redacted]"


def retry_wait(attempt: int, retry_after: Optional[float], rand: Callable[[], float]) -> float:
    """Seconds to wait before retry number ``attempt + 1``.

    ``Retry-After`` wins when present. Otherwise ``0.5 * 2**attempt`` with
    +/-25% jitter, at most 8 seconds. ``rand`` returns a float in ``[0, 1)``.
    """
    if retry_after is not None:
        return max(0.0, retry_after)
    base = 0.5 * (2**attempt)
    jittered = base * (0.75 + 0.5 * rand())
    return float(min(8.0, jittered))


def parse_retry_after(value: Optional[str], now: Optional[float] = None) -> Optional[float]:
    """Parse ``Retry-After`` as seconds (or an HTTP date). ``None`` if absent or invalid."""
    if value is None:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        current = time.time() if now is None else now
        return max(0.0, when.timestamp() - current)
    if seconds != seconds or seconds < 0:  # NaN or negative
        return None
    return seconds


def _mode_for(api_key: str) -> Optional[Mode]:
    if api_key.startswith("pk_test_"):
        return "test"
    if api_key.startswith("pk_live_"):
        return "live"
    return None


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class Agilis:
    """Client for the Agilis Advertising REST API.

    Args:
        api_key: Your API key. Defaults to the ``AGILIS_API_KEY`` environment variable.
            A ``pk_test_`` key works in Test mode and a ``pk_live_`` key in Live mode.
        base_url: The API's base URL (default ``https://ads.agilis.dating``).
        timeout: Seconds to wait for each request (default 60).
        max_retries: How many times to retry a failed request (default 2).
        http_client: An ``httpx.Client`` to send requests with. The SDK does not close it.

    Example::

        from agilis_ads import Agilis

        with Agilis() as client:
            for offer in client.offers.iter_all():
                print(offer["offer_id"], offer["title"])
    """

    categories: Categories
    interests: Interests
    offers: Offers
    event_categories: EventCategories
    event_currencies: EventCurrencies
    event_config: EventConfigResource
    events: Events
    webhook_endpoints: WebhookEndpoints
    webhook_events: WebhookEvents
    webhooks: Webhooks

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("AGILIS_API_KEY")
        key = (key or "").strip()
        if not key:
            raise AuthenticationError(
                "No API key: pass api_key or set the AGILIS_API_KEY environment variable."
            )
        if max_retries < 0:
            raise ValueError("max_retries must be 0 or more")
        self.__api_key = key
        self.mode: Optional[Mode] = _mode_for(key)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._owns_http_client = http_client is None
        self._http = http_client if http_client is not None else httpx.Client()
        self._sleep: Callable[[float], None] = time.sleep
        self._random: Callable[[], float] = random.random
        self.user_agent = (
            f"agilis-ads-python/{__version__} "
            f"({platform.python_implementation()} {platform.python_version()})"
        )

        self.categories = Categories(self)
        self.interests = Interests(self)
        self.offers = Offers(self)
        self.event_categories = EventCategories(self)
        self.event_currencies = EventCurrencies(self)
        self.event_config = EventConfigResource(self)
        self.events = Events(self)
        self.webhook_endpoints = WebhookEndpoints(self)
        self.webhook_events = WebhookEvents(self)
        self.webhooks = Webhooks()

    # ------------------------------------------------------------------ basics

    @property
    def environment(self) -> Optional[str]:
        """``"TEST"`` or ``"LIVE"`` from the key, or ``None`` for a key of neither form."""
        return self.mode.upper() if self.mode else None

    @property
    def is_live(self) -> bool:
        """True when the key is a Live key: changes are real and may be charged."""
        return self.mode == "live"

    def __repr__(self) -> str:
        return f"Agilis(mode={self.mode!r}, base_url={self.base_url!r})"

    def close(self) -> None:
        """Close the HTTP connection pool (unless you supplied the ``http_client``)."""
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> Agilis:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------------------------------------------------------------- helpers

    def _redact(self, text: str) -> str:
        return text.replace(self.__api_key, _REDACTED) if self.__api_key else text

    def _with_environment(self, params: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        result = dict(params or {})
        if result.get("environment") is None and self.environment is not None:
            result["environment"] = self.environment
        return result

    @staticmethod
    def _path(template: str, *ids: Union[int, str]) -> str:
        return template.format(*(quote(str(i), safe="") for i in ids))

    def _headers(self, extra: Optional[Mapping[str, str]]) -> Dict[str, str]:
        headers = {
            "x-api-key": self.__api_key,
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if extra:
            headers.update(extra)
        return headers

    # ---------------------------------------------------------------- requests

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
        multipart: Optional[List[Part]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> AgilisObject:
        method = method.upper()
        request_headers = self._headers(headers)
        content: Optional[bytes] = None
        if multipart is not None:
            content, request_headers["Content-Type"] = encode_multipart(multipart)
        elif json is not None:
            content = _json.dumps(dict(json), separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        params = {k: _query_value(v) for k, v in query.items() if v is not None} if query else None
        has_idempotency_key = any(k.lower() == "idempotency-key" for k in request_headers)
        retry_5xx = method in ("GET", "DELETE") or (method == "POST" and has_idempotency_key)
        url = self.base_url + path

        attempt = 0
        while True:
            try:
                response = self._http.request(
                    method,
                    url,
                    params=params,
                    content=content,
                    headers=request_headers,
                    timeout=self.timeout,
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt < self.max_retries:
                    self._sleep(retry_wait(attempt, None, self._random))
                    attempt += 1
                    continue
                kind = "timed out" if isinstance(exc, httpx.TimeoutException) else "failed"
                raise ConnectionError(
                    self._redact(f"The request to {method} {path} {kind}: {type(exc).__name__}.")
                ) from exc
            except httpx.HTTPError as exc:
                raise ConnectionError(
                    self._redact(f"The request to {method} {path} failed: {type(exc).__name__}.")
                ) from exc

            status = response.status_code
            retryable = status == 429 or (retry_5xx and status in _RETRYABLE_5XX)
            if retryable and attempt < self.max_retries:
                wait = retry_wait(
                    attempt, parse_retry_after(response.headers.get("retry-after")), self._random
                )
                response.close()
                self._sleep(wait)
                attempt += 1
                continue
            return self._handle(response)

    def _handle(self, response: httpx.Response) -> AgilisObject:
        status = response.status_code
        body: Any
        raw = response.content
        if raw:
            try:
                body = response.json()
            except ValueError:
                body = response.text
        else:
            body = None
        meta = ResponseMeta(status_code=status, headers=response.headers)

        return_code = body.get("return_code") if isinstance(body, dict) else None
        if not isinstance(return_code, str):
            return_code = None

        if not 200 <= status < 300:
            raise self._error_for(status, body, return_code, response.headers)
        if return_code is not None and return_code.startswith("E"):
            raise InvalidRequestError(
                self._message(body, f"The API refused the request ({return_code})."),
                http_status=status,
                return_code=return_code,
                body=body,
                headers=response.headers,
            )
        if body is None:
            return AgilisObject({}, meta)
        if not isinstance(body, dict):
            raise ApiError(
                "The API returned a response that is not a JSON object.",
                http_status=status,
                body=body,
                headers=response.headers,
            )
        return AgilisObject(body, meta)

    def _message(self, body: Any, fallback: str) -> str:
        if isinstance(body, dict):
            for key in ("message", "error"):
                value = body.get(key)
                if isinstance(value, str) and value:
                    return self._redact(value)
        return self._redact(fallback)

    def _error_for(
        self, status: int, body: Any, return_code: Optional[str], headers: httpx.Headers
    ) -> AgilisError:
        message = self._message(body, f"The API returned HTTP {status}.")
        common: Dict[str, Any] = {
            "http_status": status,
            "return_code": return_code,
            "body": body,
            "headers": headers,
        }
        if status == 401:
            return AuthenticationError(message, **common)
        if status == 403:
            return PermissionError(message, **common)
        if status == 404:
            return NotFoundError(message, **common)
        if status == 409:
            return ConflictError(message, **common)
        if status in (400, 422):
            return InvalidRequestError(message, **common)
        if status == 429:
            return RateLimitError(
                message, retry_after=parse_retry_after(headers.get("retry-after")), **common
            )
        return ApiError(message, **common)
