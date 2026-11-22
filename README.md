# Agilis Advertising API: Python SDK

The official Python library for the [Agilis Advertising REST API](https://www.agilis.dating/api-doc): create and manage Offers and Events, read their results, and receive webhooks.

- Python 3.10 or newer, with [`httpx`](https://www.python-httpx.org/) as the only dependency
- Fully typed (`TypedDict` parameters and responses, `py.typed`)
- Retries with backoff, idempotency keys, cursor pagination and webhook signature checks built in

## Install

```bash
pip install agilis-ads
```

## Quick start (Test mode)

Create an API key in the Ad Portal under **Manage API Keys**, with the Ad Portal in Test mode. A `pk_test_` key works in Test mode only: members never see what you create and nothing is charged.

```bash
export AGILIS_API_KEY=pk_test_...
```

```python
from agilis_ads import Agilis

client = Agilis()  # reads AGILIS_API_KEY

print(client.mode)  # "test" or "live", decided by the key

for category in client.categories.list()["categories"]:
    print(category["category_id"], category["category_name"])

estimate = client.offers.estimate_price(
    {
        "start_datetime": "2027-07-10T08:00:00Z",
        "end_datetime": "2027-07-12T20:30:00Z",
        "location": [51.5074, -0.1278],
        "radius": 10,
    }
)
print(estimate["estimated_cost"], estimate["currency"])

# dry_run=True checks everything and says what it would cost, without creating anything.
result = client.offers.create(
    {
        "category_id": 1,
        "title": "20% off summer sale",
        "description": "Discount valid through July",
        "push_notification_title": "20% off this summer",
        "push_notification_message": "Show this at the till for 20% off everything.",
        "url": "https://example.com/offer",
        "image": "offer.png",
        "location": [51.5074, -0.1278],
        "radius": 10,
        "start_datetime": "2027-07-10T08:00:00Z",
        "expiry_datetime": "2027-07-12T20:30:00Z",
        "payment_method": "B",
    },
    dry_run=True,
)
```

Operations that take an `environment` (`TEST` or `LIVE`) fill it in from the key when you leave it out. To make sure a script never runs against Live:

```python
if client.mode != "test":
    raise SystemExit("Use a Test-mode key")
```

More in [`examples/`](examples): a Test-mode tour and a webhook receiver.

## Client options

```python
import httpx
from agilis_ads import Agilis

client = Agilis(
    api_key="pk_test_...",  # default: the AGILIS_API_KEY environment variable
    base_url="https://ads.agilis.dating",  # the default
    timeout=60.0,  # seconds per request; the default
    max_retries=2,  # the default
    http_client=httpx.Client(),  # optional: your own client (proxies, transports)
)
```

| Attribute | Meaning |
|---|---|
| `client.mode` | `"test"` for a `pk_test_` key, `"live"` for a `pk_live_` key |
| `client.environment` | `"TEST"` or `"LIVE"`, as sent to the API |
| `client.is_live` | `True` for a Live key |

Use the client as a context manager (`with Agilis() as client:`), or call `client.close()` when done. A client you pass in as `http_client` is never closed by the SDK.

The key is sent in the `x-api-key` header only. It is never logged, never part of a URL, and never included in an error message.

## Resources and methods

Each method takes path parameters as arguments and everything else as one dict, with the API's own field names. Responses are the parsed JSON as a `dict`, with every field kept (including any the API adds later).

| Method | HTTP |
|---|---|
| `client.categories.list()` | `GET /categories` |
| `client.interests.list()` | `GET /interests` |
| `client.offers.estimate_price(params)` | `POST /offers/price-estimate` |
| `client.offers.create(params, *, idempotency_key=None, dry_run=False)` | `POST /offers` |
| `client.offers.list(params=None)` | `GET /offers` |
| `client.offers.iter_all(params=None)` | every page of `GET /offers` |
| `client.offers.pause(offer_id)` | `POST /offers/{offer_id}/pause` |
| `client.offers.resume(offer_id)` | `POST /offers/{offer_id}/resume` |
| `client.offers.analytics(offer_id, {"interval": "7d"})` | `GET /offers/{offer_id}/analytics` |
| `client.offers.delete(offer_id, *, dry_run=False)` | `DELETE /offers/{offer_id}` |
| `client.event_categories.list()` | `GET /event-categories` |
| `client.event_currencies.list()` | `GET /event-currencies` |
| `client.event_config.get()` | `GET /event-config` |
| `client.events.preview(params=None)` | `POST /events/preview` |
| `client.events.publish(params, *, idempotency_key=None, dry_run=False)` | `POST /events` |
| `client.events.list(params=None)` | `GET /events` |
| `client.events.iter_all(params=None)` | every page of `GET /events` |
| `client.events.get(event_id)` | `GET /events/{event_id}` |
| `client.events.edit(event_id, params)` | `PATCH /events/{event_id}` (sent as `POST` with `X-HTTP-Method-Override: PATCH`) |
| `client.events.delete(event_id, *, dry_run=False)` | `DELETE /events/{event_id}` |
| `client.events.reschedule(event_id, params)` | `POST /events/{event_id}/reschedule` |
| `client.events.cancel(event_id, *, dry_run=False)` | `POST /events/{event_id}/cancel` |
| `client.events.analytics(event_id, {"interval": "all"})` | `GET /events/{event_id}/analytics` |
| `client.webhook_endpoints.list()` | `GET /webhook-endpoints` |
| `client.webhook_endpoints.create(params)` | `POST /webhook-endpoints` |
| `client.webhook_endpoints.get(endpoint_id)` | `GET /webhook-endpoints/{endpoint_id}` |
| `client.webhook_endpoints.update(endpoint_id, params)` | `PATCH /webhook-endpoints/{endpoint_id}` |
| `client.webhook_endpoints.delete(endpoint_id)` | `DELETE /webhook-endpoints/{endpoint_id}` |
| `client.webhook_endpoints.roll_secret(endpoint_id, params=None)` | `POST /webhook-endpoints/{endpoint_id}/roll-secret` |
| `client.webhook_endpoints.send_test(endpoint_id, params=None)` | `POST /webhook-endpoints/{endpoint_id}/test` |
| `client.webhook_events.list(params=None)` | `GET /webhook-events` |
| `client.webhook_events.iter_all(params=None)` | every page of `GET /webhook-events` |
| `client.webhook_events.get(webhook_event_id)` | `GET /webhook-events/{webhook_event_id}` |
| `client.webhook_events.resend(webhook_event_id, params=None)` | `POST /webhook-events/{webhook_event_id}/resend` |
| `client.webhooks.construct_event(payload, header, secret, tolerance=300)` | verifies a received webhook; no request |

The parameter and response types are in `agilis_ads.types` (for example `OfferCreateParams` and `OfferPage`). The fields and their rules are described in the [API reference](https://www.agilis.dating/api-doc).

### Images and multipart fields

`offers.create`, `events.preview`, `events.publish` and `events.edit` are sent as `multipart/form-data`. Pass the image as a file path, `bytes`, a binary stream, or a `(file_name, bytes_or_stream)` tuple; the content type is detected from the file name.

```python
client.events.publish(
    {
        "title": "Beginners Cuban Salsa: Friday Social",
        "description": "Drop-in class for absolute beginners, followed by a social.",
        "venue_name": "Bar Salsa",
        "address": "96 Charing Cross Road",
        "city": "London",
        "country_code": "GB",
        "location": [51.5133, -0.1300],
        "starts_at": "2027-10-16T18:30:00Z",
        "ends_at": "2027-10-16T23:00:00Z",
        "url": "https://example.com/classes/friday",
        "image": ("salsa.jpg", open("salsa.jpg", "rb")),
        "crop": {"x": 0, "y": 120, "w": 1080},
        "payment_method": "B",
    }
)
```

Lists are sent as repeated fields (`location[]`, `gender[]`, `interests[]`) and `crop` as `crop[x]`, `crop[y]` and `crop[w]`. `events.edit` is always sent as a multipart `POST` with `X-HTTP-Method-Override: PATCH`, with or without a new image, so its fields always reach the API.

### Status and headers

Each result remembers the HTTP response it came from:

```python
import agilis_ads

page = client.offers.list()
meta = agilis_ads.response_meta(page)
print(meta.status_code, meta.rate_limit_remaining, meta.headers.get("X-RateLimit-Limit"))
```

## Pagination

`offers.list`, `events.list` and `webhook_events.list` return one page: `data` and `pagination` (`has_more`, `next_cursor`). Pass `next_cursor` back as `cursor` for the next page, or let `iter_all` follow the pages for you:

```python
for offer in client.offers.iter_all({"offer_status": "active", "limit": 100}):
    print(offer["offer_id"], offer["title"])
```

`iter_all` is lazy: it fetches the next page only when the loop reaches it.

## Idempotency and retries

`offers.create` and `events.publish` always send an `Idempotency-Key`: yours if you pass `idempotency_key=`, otherwise a new UUID for that call. The same key is reused on every retry of the call, so a retry never creates a second Offer or Event. Store your own key if you may retry later, for example after a restart.

A request is retried up to `max_retries` times (default 2) when:

- the connection fails or times out;
- the API answers HTTP 429;
- the API answers HTTP 500, 502, 503 or 504 to a `GET` or `DELETE`, or to a `POST` that carries an `Idempotency-Key`.

Other `POST` and `PATCH` requests are not retried after a 5xx, because the change may already have been made. The wait is the API's `Retry-After` when it sends one; otherwise 0.5 seconds, doubling each time, with ±25% jitter, at most 8 seconds.

## Errors

Every error is an `agilis_ads.AgilisError` with `http_status`, `return_code`, `message`, `body` (the parsed response) and `headers`.

| Error | When |
|---|---|
| `AuthenticationError` | HTTP 401 (or no API key) |
| `agilis_ads.PermissionError` | HTTP 403 |
| `NotFoundError` | HTTP 404 |
| `ConflictError` | HTTP 409 |
| `InvalidRequestError` | HTTP 400 or 422, or HTTP 200 with a `return_code` starting with `E` |
| `RateLimitError` | HTTP 429; `retry_after` holds the seconds to wait |
| `ApiError` | HTTP 5xx and anything else unexpected |
| `agilis_ads.ConnectionError` | no response: the connection failed or timed out |
| `SignatureVerificationError` | a webhook could not be verified |

`PermissionError` and `ConnectionError` share their names with Python built-ins, so use them through the package (`agilis_ads.PermissionError`) rather than importing them by name.

Some refusals arrive as HTTP 200 with an `E` code, for example `E3` when the balance is too low. They raise `InvalidRequestError` with `http_status` 200. Return codes are scoped to each endpoint; the [API reference](https://www.agilis.dating/api-doc) lists them.

```python
import agilis_ads

try:
    client.offers.create(params)
except agilis_ads.InvalidRequestError as error:
    print("Refused:", error.return_code, error.message)
except agilis_ads.RateLimitError as error:
    print("Slow down for", error.retry_after, "seconds")
except agilis_ads.AgilisError as error:
    print("Failed:", error)
```

## Webhooks

Create an endpoint and store its `secret` (it is shown only once):

```python
endpoint = client.webhook_endpoints.create(
    {
        "url": "https://example.com/agilis/webhooks",
        "enabled_events": ["offer.started", "event.published"],
    }
)
secret = endpoint["secret"]
```

Every webhook carries an `Agilis-Signature` header. `construct_event` checks it against the raw body, refuses a timestamp more than 300 seconds away (change it with `tolerance`), and returns the parsed event. It needs no API key:

```python
import os

from flask import Flask, request

from agilis_ads import SignatureVerificationError, construct_event

app = Flask(__name__)
SECRET = os.environ["AGILIS_WEBHOOK_SECRET"]


@app.post("/agilis/webhooks")
def agilis_webhook():
    try:
        event = construct_event(
            request.get_data(),  # the raw body, exactly as received
            request.headers.get("Agilis-Signature", ""),
            SECRET,
        )
    except SignatureVerificationError:
        return "", 400

    if event["type"] == "offer.started":
        print("Offer started:", event["data"]["object"]["offer_id"])
    return "", 200
```

Answer with a 2xx quickly and do slow work afterwards. An event can arrive more than once and out of order: use `event["id"]` to ignore repeats and `event["created"]` to order them. While a secret is being rolled, the header carries two signatures and either one is accepted.

[`examples/webhook_receiver.py`](examples/webhook_receiver.py) is the same receiver using only the standard library.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest
```

`pytest -m integration` runs a short read-only check against the API in Test mode; it needs `AGILIS_TEST_API_KEY` set to a `pk_test_` key and refuses any other.

## Links

- [API reference](https://www.agilis.dating/api-doc) ([Markdown](https://www.agilis.dating/api-doc.md))
- [OpenAPI document](https://www.agilis.dating/openapi.json)
- [AsyncAPI document (webhooks)](https://www.agilis.dating/asyncapi.json)
- [agilis-ads-api](https://github.com/agilisdating/agilis-ads-api): the API's public repository, with examples and a Postman collection

## Security

See [SECURITY.md](SECURITY.md) to report a problem or if an API key has been exposed.

## License

MIT. See [LICENSE](LICENSE).
