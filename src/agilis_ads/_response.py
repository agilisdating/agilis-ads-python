from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

__all__ = ["AgilisObject", "ResponseMeta", "response_meta"]


@dataclass(frozen=True)
class ResponseMeta:
    """The HTTP status and headers of the response a result came from."""

    status_code: int
    headers: httpx.Headers

    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """``X-RateLimit-Remaining``, when the API sent it."""
        value = self.headers.get("x-ratelimit-remaining")
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None


class AgilisObject(Dict[str, Any]):
    """A parsed JSON response: a ``dict`` that also remembers its HTTP response.

    Every field the API sends is kept, including ones this SDK does not know yet.
    """

    __slots__ = ("_meta",)

    def __init__(self, data: Dict[str, Any], meta: ResponseMeta) -> None:
        super().__init__(data)
        self._meta = meta

    @property
    def http_status(self) -> int:
        return self._meta.status_code

    @property
    def headers(self) -> httpx.Headers:
        return self._meta.headers


def response_meta(result: Any) -> Optional[ResponseMeta]:
    """Return the HTTP status and headers of a result returned by the client.

    Example::

        page = client.offers.list()
        meta = agilis_ads.response_meta(page)
        print(meta.status_code, meta.headers.get("X-RateLimit-Remaining"))
    """
    if isinstance(result, AgilisObject):
        return result._meta
    return None
