"""Error types raised by the SDK.

``PermissionError`` and ``ConnectionError`` share their names with Python
built-ins. Refer to them through the package (``agilis_ads.PermissionError``)
or import them under another name.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

import httpx

__all__ = [
    "AgilisError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "ConflictError",
    "InvalidRequestError",
    "RateLimitError",
    "ApiError",
    "ConnectionError",
    "SignatureVerificationError",
]


class AgilisError(Exception):
    """Base class of every error the SDK raises.

    Attributes:
        message: A readable description (the API's own ``message`` when it sent one).
        http_status: The HTTP status, or ``None`` when there was no response.
        return_code: The API's ``return_code`` (for example ``"E3"``), when present.
        body: The parsed response body (a ``dict`` for JSON, otherwise the text).
        headers: The response headers (empty when there was no response).
    """

    message: str
    http_status: Optional[int]
    return_code: Optional[str]
    body: Any
    headers: httpx.Headers

    def __init__(
        self,
        message: str,
        *,
        http_status: Optional[int] = None,
        return_code: Optional[str] = None,
        body: Any = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.return_code = return_code
        self.body = body
        self.headers = httpx.Headers(headers or {})

    def __str__(self) -> str:
        parts = []
        if self.http_status is not None:
            parts.append(f"HTTP {self.http_status}")
        if self.return_code:
            parts.append(self.return_code)
        prefix = " ".join(parts)
        return f"{prefix}: {self.message}" if prefix else self.message

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(message={self.message!r}, "
            f"http_status={self.http_status!r}, return_code={self.return_code!r})"
        )


class AuthenticationError(AgilisError):
    """HTTP 401: the API key is missing, unknown, disabled or expired (or the item is not found)."""


class PermissionError(AgilisError):  # noqa: A001 - name set by the shared SDK contract
    """HTTP 403: the key may not do this (for example, the other mode's ``environment``)."""


class NotFoundError(AgilisError):
    """HTTP 404."""


class ConflictError(AgilisError):
    """HTTP 409."""


class InvalidRequestError(AgilisError):
    """HTTP 400 or 422, or HTTP 200 with a ``return_code`` starting with ``E``."""


class RateLimitError(AgilisError):
    """HTTP 429. ``retry_after`` is the wait the API asked for, in seconds."""

    retry_after: Optional[float]

    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ApiError(AgilisError):
    """HTTP 5xx, or any other unexpected status."""


class ConnectionError(AgilisError):  # noqa: A001 - name set by the shared SDK contract
    """No response was received: the connection failed or timed out."""


class SignatureVerificationError(AgilisError):
    """A received webhook could not be verified.

    ``reason`` is ``"header"`` (the signature header is missing or malformed),
    ``"signature"`` (no signature matches), ``"timestamp"`` (outside the tolerance)
    or ``"payload"`` (the verified body is not a JSON object).
    """

    reason: str

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason
