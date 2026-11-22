"""Verifying webhooks sent by Agilis.

Each webhook request carries an ``Agilis-Signature`` header of the form
``t=<timestamp>,v1=<signature>``. The signature is the hex HMAC-SHA256 of
``<timestamp>.<raw body>`` with the endpoint's secret. While a secret is being
rolled the header carries two ``v1`` values, and either one may match.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import List, Optional, Union, cast

from ._errors import SignatureVerificationError
from .types import WebhookEvent

__all__ = ["DEFAULT_TOLERANCE", "SIGNATURE_HEADER", "Webhooks", "construct_event", "verify_header"]

SIGNATURE_HEADER = "Agilis-Signature"
"""The name of the HTTP header that carries the signature."""

DEFAULT_TOLERANCE = 300
"""How old (or how far in the future) a timestamp may be, in seconds."""


def _parse_header(header: str) -> tuple[int, List[str]]:
    timestamp: Optional[int] = None
    signatures: List[str] = []
    for item in (header or "").split(","):
        key, sep, value = item.strip().partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if key == "t" and timestamp is None:
            if not value.isascii() or not value.isdigit():
                raise SignatureVerificationError(
                    "The signature header's timestamp is not a number.", reason="header"
                )
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value.lower())
    if timestamp is None:
        raise SignatureVerificationError(
            "The signature header has no timestamp (t=).", reason="header"
        )
    if not signatures:
        raise SignatureVerificationError(
            "The signature header has no v1 signature.", reason="header"
        )
    return timestamp, signatures


def verify_header(
    payload: Union[str, bytes],
    header: str,
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE,
    *,
    now: Optional[float] = None,
) -> None:
    """Check a webhook's signature header, raising :class:`SignatureVerificationError` if it fails.

    ``payload`` must be the raw request body exactly as received. ``tolerance``
    is in seconds; ``0`` or less turns the timestamp check off.
    """
    if not secret:
        raise ValueError("secret is required")
    body = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
    timestamp, signatures = _parse_header(header)

    expected = hmac.new(
        secret.encode("utf-8"), str(timestamp).encode("ascii") + b"." + body, hashlib.sha256
    ).hexdigest()
    matched = False
    for candidate in signatures:
        # Check every value so the time taken does not depend on which one matches.
        if hmac.compare_digest(expected.encode("ascii"), candidate.encode("ascii", "replace")):
            matched = True
    if not matched:
        raise SignatureVerificationError(
            "No signature matches the payload. Check the endpoint secret and that the body "
            "is passed exactly as received.",
            reason="signature",
        )

    if tolerance > 0:
        current = time.time() if now is None else now
        if abs(current - timestamp) > tolerance:
            raise SignatureVerificationError(
                "The signature timestamp is outside the tolerance.", reason="timestamp"
            )


def construct_event(
    payload: Union[str, bytes],
    header: str,
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE,
    *,
    now: Optional[float] = None,
) -> WebhookEvent:
    """Verify a received webhook and return its parsed event.

    Args:
        payload: The raw request body, exactly as received (``bytes`` or ``str``).
        header: The value of the ``Agilis-Signature`` header.
        secret: The endpoint's signing secret (``whsec_...``).
        tolerance: The largest allowed age of the timestamp, in seconds (default 300).
        now: The current Unix time; for tests only.

    Raises:
        SignatureVerificationError: the header is malformed, no signature matches,
            the timestamp is outside the tolerance, or the body is not JSON.
    """
    verify_header(payload, header, secret, tolerance, now=now)
    try:
        event = json.loads(payload)
    except ValueError:
        raise SignatureVerificationError(
            "The payload is not valid JSON.", reason="payload"
        ) from None
    if not isinstance(event, dict):
        raise SignatureVerificationError("The payload is not a JSON object.", reason="payload")
    return cast(WebhookEvent, event)


class Webhooks:
    """``client.webhooks``: verifies webhooks. It makes no request."""

    signature_header = SIGNATURE_HEADER

    def construct_event(
        self,
        payload: Union[str, bytes],
        header: str,
        secret: str,
        tolerance: int = DEFAULT_TOLERANCE,
        *,
        now: Optional[float] = None,
    ) -> WebhookEvent:
        """Verify a received webhook and return its parsed event. See :func:`construct_event`."""
        return construct_event(payload, header, secret, tolerance, now=now)

    def verify_header(
        self,
        payload: Union[str, bytes],
        header: str,
        secret: str,
        tolerance: int = DEFAULT_TOLERANCE,
        *,
        now: Optional[float] = None,
    ) -> None:
        """Check a signature header without parsing the body. See :func:`verify_header`."""
        verify_header(payload, header, secret, tolerance, now=now)
