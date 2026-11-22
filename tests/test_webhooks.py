"""The shared signature vectors, run against construct_event."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest

import agilis_ads
from agilis_ads import Agilis, SignatureVerificationError, construct_event

VECTORS: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "webhook-signature-vectors.json").read_text("utf-8")
)
CASES = VECTORS["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
@pytest.mark.parametrize("as_bytes", [False, True], ids=["str", "bytes"])
def test_vector(case: dict[str, Any], as_bytes: bool) -> None:
    body: str = VECTORS["body"]
    payload: str | bytes = body.encode("utf-8") if as_bytes else body
    kwargs = {"now": VECTORS["now_unix"]}
    if case["valid"]:
        event = construct_event(
            payload, case["header"], VECTORS["secret"], VECTORS["tolerance_seconds"], **kwargs
        )
        assert event["id"] == "whevt_01JD0S6Q4M8K1Z0X7C2V9B3N5R"
        assert event["type"] == "event.published"
        if event["type"] == "event.published":
            assert event["data"]["object"]["event_id"] == 3104
    else:
        with pytest.raises(SignatureVerificationError) as info:
            construct_event(
                payload, case["header"], VECTORS["secret"], VECTORS["tolerance_seconds"], **kwargs
            )
        assert info.value.reason == case["error"]
        assert VECTORS["secret"] not in str(info.value)


def test_vectors_file_has_every_case() -> None:
    assert len(CASES) == 12
    assert sum(1 for c in CASES if c["valid"]) == 3


def test_client_webhooks_construct_event() -> None:
    case = CASES[0]
    with Agilis("pk_test_x") as client:
        event = client.webhooks.construct_event(
            VECTORS["body"], case["header"], VECTORS["secret"], now=VECTORS["now_unix"]
        )
    assert event["livemode"] is True


def test_default_tolerance_uses_current_time() -> None:
    # The vectors are from a fixed time, so with the real clock the timestamp is too old.
    with pytest.raises(SignatureVerificationError) as info:
        construct_event(VECTORS["body"], CASES[0]["header"], VECTORS["secret"])
    assert info.value.reason == "timestamp"


def test_tolerance_zero_skips_the_time_check() -> None:
    event = construct_event(VECTORS["body"], CASES[0]["header"], VECTORS["secret"], tolerance=0)
    assert event["type"] == "event.published"


def test_custom_tolerance() -> None:
    too_old = next(c for c in CASES if c["name"] == "too_old")
    # 430 seconds old: refused at 300, accepted at 500.
    event = construct_event(
        VECTORS["body"], too_old["header"], VECTORS["secret"], 500, now=VECTORS["now_unix"]
    )
    assert event["id"].startswith("whevt_")


def sign(secret: str, timestamp: int, body: str) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_signed_body_that_is_not_json() -> None:
    header = sign("whsec_x", 100, "not json")
    with pytest.raises(SignatureVerificationError) as info:
        construct_event("not json", header, "whsec_x", now=100)
    assert info.value.reason == "payload"


def test_uppercase_signature_accepted() -> None:
    header = sign("whsec_x", 100, "{}")
    t, v1 = header.split(",")
    assert (
        construct_event("{}", f"{t},{v1.upper().replace('V1=', 'v1=')}", "whsec_x", now=100) == {}
    )


def test_empty_secret_refused() -> None:
    with pytest.raises(ValueError):
        construct_event("{}", sign("a", 1, "{}"), "", now=1)


def test_verify_header_and_constant() -> None:
    assert agilis_ads.SIGNATURE_HEADER == "Agilis-Signature"
    agilis_ads.verify_header(
        VECTORS["body"], CASES[0]["header"], VECTORS["secret"], now=VECTORS["now_unix"]
    )
