"""The official Python SDK for the Agilis Advertising REST API.

Example::

    from agilis_ads import Agilis

    client = Agilis()  # reads AGILIS_API_KEY
    print(client.mode)  # "test" or "live", from the key
    for category in client.categories.list()["categories"]:
        print(category["category_id"], category["category_name"])
"""

from . import types
from ._client import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, Agilis
from ._errors import (
    AgilisError,
    ApiError,
    AuthenticationError,
    ConflictError,
    ConnectionError as ConnectionError,
    InvalidRequestError,
    NotFoundError,
    PermissionError as PermissionError,
    RateLimitError,
    SignatureVerificationError,
)
from ._response import ResponseMeta, response_meta
from ._version import __version__
from .webhooks import SIGNATURE_HEADER, Webhooks, construct_event, verify_header

# ``PermissionError`` and ``ConnectionError`` are left out of ``__all__`` so that
# ``from agilis_ads import *`` never hides Python's built-ins of the same names.
__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "SIGNATURE_HEADER",
    "Agilis",
    "AgilisError",
    "ApiError",
    "AuthenticationError",
    "ConflictError",
    "InvalidRequestError",
    "NotFoundError",
    "RateLimitError",
    "ResponseMeta",
    "SignatureVerificationError",
    "Webhooks",
    "__version__",
    "construct_event",
    "response_meta",
    "types",
    "verify_header",
]
