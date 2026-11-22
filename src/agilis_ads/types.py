"""Typed shapes of the API's parameters and responses.

Every response is a plain ``dict`` at run time, so fields the API adds later
are kept and never break a client. The ``TypedDict`` classes below describe the
fields known today; all response fields are optional (``total=False``).
"""

from __future__ import annotations

import os
from typing import IO, Any, Dict, List, Literal, Optional, Tuple, TypedDict, Union

__all__ = [
    "AnalyticsInterval",
    "AnalyticsParams",
    "ButtonPreset",
    "Category",
    "CategoryList",
    "Crop",
    "Environment",
    "Event",
    "EventAnalytics",
    "EventAnalyticsMetrics",
    "EventCancelResult",
    "EventCategory",
    "EventCategoryList",
    "EventConfig",
    "EventCurrencyList",
    "EventDetail",
    "EventEditParams",
    "EventEditResult",
    "EventListParams",
    "EventPage",
    "EventPreview",
    "EventPreviewParams",
    "EventPublishParams",
    "EventPublishResult",
    "EventRescheduleParams",
    "EventRescheduleResult",
    "EventStatusFilter",
    "Gender",
    "ImageInput",
    "Interest",
    "InterestList",
    "Mode",
    "Offer",
    "OfferAnalytics",
    "OfferCreateParams",
    "OfferCreateResult",
    "OfferListParams",
    "OfferPage",
    "OfferPriceEstimate",
    "OfferPriceEstimateParams",
    "OfferStatusFilter",
    "Pagination",
    "ReturnCodeResult",
    "WebhookDelivery",
    "WebhookEndpoint",
    "WebhookEndpointCreateParams",
    "WebhookEndpointDeleted",
    "WebhookEndpointList",
    "WebhookEndpointUpdateParams",
    "WebhookEndpointWithSecret",
    "WebhookEvent",
    "WebhookEventListParams",
    "WebhookEventPage",
    "WebhookEventRecord",
    "WebhookEventType",
    "WebhookResendParams",
    "WebhookResendResult",
    "WebhookRollSecretParams",
    "WebhookTestParams",
    "WebhookTestResult",
    "BalanceWebhookEvent",
    "EventWebhookEvent",
    "InvoiceWebhookEvent",
    "OfferWebhookEvent",
    "TermsWebhookEvent",
]

# --------------------------------------------------------------------------
# Shared literals
# --------------------------------------------------------------------------

Mode = Literal["test", "live"]
Environment = Literal["TEST", "LIVE", "test", "live"]
Gender = Literal["Male", "Female", "Non-binary", "All"]
ButtonPreset = Literal[
    "claim_offer", "visit_website", "install_app", "book_now", "get_directions", "custom"
]
AnalyticsInterval = Literal["24h", "7d", "30d", "60d", "90d", "all"]
OfferStatusFilter = Literal["awaiting_payment", "active", "paused", "ended"]
EventStatusFilter = Literal["upcoming", "scheduled", "rescheduled", "cancelled", "ended"]

OfferEventType = Literal[
    "offer.created",
    "offer.payment_succeeded",
    "offer.payment_failed",
    "offer.started",
    "offer.paused",
    "offer.resumed",
    "offer.ended",
    "offer.deleted",
    "offer.disabled",
    "offer.enabled",
]
EventEventType = Literal[
    "event.published",
    "event.updated",
    "event.rescheduled",
    "event.cancelled",
    "event.deleted",
    "event.ended",
]
BalanceEventType = Literal["balance.topped_up", "balance.low"]
InvoiceEventType = Literal["invoice.created"]
TermsEventType = Literal["terms.version_issued"]
WebhookEventType = Union[
    OfferEventType, EventEventType, BalanceEventType, InvoiceEventType, TermsEventType
]

ImageInput = Union[
    str,
    os.PathLike[str],
    bytes,
    IO[bytes],
    Tuple[str, Union[bytes, IO[bytes]]],
]
"""An image to upload: a file path, bytes, a binary stream, or ``(file_name, bytes_or_stream)``.

The content type is detected from the file name (or from the bytes when there is no name).
"""


class Crop(TypedDict):
    """The area of the image to use, sent as ``crop[x]``, ``crop[y]`` and ``crop[w]``."""

    x: int
    y: int
    w: int


class AnalyticsParams(TypedDict):
    interval: AnalyticsInterval


class Pagination(TypedDict, total=False):
    limit: int
    count: int
    has_more: bool
    next_cursor: Optional[str]


class ReturnCodeResult(TypedDict, total=False):
    return_code: str
    message: str


# --------------------------------------------------------------------------
# Categories and interests
# --------------------------------------------------------------------------


class Category(TypedDict, total=False):
    category_id: int
    category_name: str


class CategoryList(TypedDict, total=False):
    categories: List[Category]


class Interest(TypedDict, total=False):
    interest_id: int
    interest_name: str


class InterestList(TypedDict, total=False):
    interests: List[Interest]


# --------------------------------------------------------------------------
# Offers
# --------------------------------------------------------------------------


class _OfferPriceEstimateRequired(TypedDict):
    start_datetime: str
    end_datetime: str
    location: List[float]
    radius: int


class OfferPriceEstimateParams(_OfferPriceEstimateRequired, total=False):
    gender: List[Gender]
    interests: List[int]
    environment: Environment


class OfferPriceEstimate(TypedDict, total=False):
    return_code: str
    price_estimate: float
    matching_users: int
    ad_units: int
    ad_unit_price: float
    estimated_cost: float
    currency: str
    exchange_rate_per_gbp: float
    exchange_rate_date: Optional[str]


class _OfferCreateRequired(TypedDict):
    category_id: int
    title: str
    description: str
    push_notification_title: str
    push_notification_message: str
    url: str
    image: ImageInput
    location: List[float]
    radius: int
    start_datetime: str
    expiry_datetime: str
    payment_method: Literal["E", "B"]


class OfferCreateParams(_OfferCreateRequired, total=False):
    terms_and_conditions: str
    advertised_name: str
    button_preset: ButtonPreset
    button_text: str
    gender: List[Gender]
    interests: List[int]
    environment: Literal["TEST", "LIVE"]


class OfferCreateResult(TypedDict, total=False):
    return_code: str
    offer_id: int
    status: str
    payment_url: Optional[str]
    currency: str
    dry_run: bool


class OfferListParams(TypedDict, total=False):
    environment: Environment
    limit: int
    cursor: str
    offer_status: OfferStatusFilter
    created_after: str
    created_before: str


class Offer(TypedDict, total=False):
    offer_id: int
    title: str
    category: str
    description: str
    terms_and_conditions: str
    advertised_name: Optional[str]
    push_notification_title: Optional[str]
    push_notification_message: Optional[str]
    button_preset: ButtonPreset
    button_text: Optional[str]
    url: str
    image: str
    latitude: float
    longitude: float
    radius: int
    gender: List[str]
    interests: List[Interest]
    start_datetime: str
    expiry_datetime: str
    creation_datetime: str
    offer_status: str
    status: str


class OfferPage(TypedDict, total=False):
    data: List[Offer]
    pagination: Pagination


class OfferAnalyticsMetrics(TypedDict, total=False):
    views: int
    clicks: int


class OfferAnalytics(TypedDict, total=False):
    offer_id: int
    interval: str
    start_datetime: str
    end_datetime: str
    status: str
    metrics: OfferAnalyticsMetrics


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------


class EventCategory(TypedDict, total=False):
    category_id: int
    code: str
    category_name: str


class EventCategoryList(TypedDict, total=False):
    categories: List[EventCategory]


class EventCurrencyList(TypedDict, total=False):
    currencies: List[str]


class EventImageRules(TypedDict, total=False):
    max_mb: int
    min_width: int
    min_height: int


class EventConfig(TypedDict, total=False):
    listing_fee: float
    currency: str
    exchange_rate_per_gbp: float
    exchange_rate_date: Optional[str]
    environment: str
    balance: float
    organisation_balance: float
    live_publishing_open: bool
    currencies: List[str]
    image: EventImageRules
    max_years_ahead: int


class EventPreviewParams(TypedDict, total=False):
    title: str
    description: str
    venue_name: str
    image: ImageInput
    crop: Crop
    environment: Literal["TEST", "LIVE"]


class ImageCrop(TypedDict, total=False):
    x: int
    y: int
    w: int
    h: int


class EventPreviewImage(TypedDict, total=False):
    preview_url: str
    width: int
    height: int
    master_width: int
    master_height: int
    crop: ImageCrop
    preview_token: str
    expires_at: str


class EventPreview(TypedDict, total=False):
    return_code: str
    category: Category
    listing_fee: float
    currency: str
    balance: float
    balance_after: float
    balance_sufficient: bool
    live_publishing_open: bool
    price_gbp: float
    image: EventPreviewImage


class _EventPublishRequired(TypedDict):
    title: str
    description: str
    venue_name: str
    address: str
    city: str
    country_code: str
    location: List[float]
    starts_at: str
    ends_at: str
    url: str
    payment_method: Literal["B"]


class EventPublishParams(_EventPublishRequired, total=False):
    advertised_name: str
    price_min: float
    price_max: float
    currency: str
    image: ImageInput
    preview_token: str
    source_event_id: int
    crop: Crop
    environment: Literal["TEST", "LIVE"]


class EventPublishResult(TypedDict, total=False):
    return_code: str
    event_id: int
    status: str
    payment_url: Optional[str]
    amount_charged: float
    currency: str
    category: Category
    dry_run: bool


class EventListParams(TypedDict, total=False):
    environment: Environment
    limit: int
    cursor: str
    event_status: EventStatusFilter
    owner_user_id: int
    created_after: str
    created_before: str


class EventOwner(TypedDict, total=False):
    user_id: int
    name: str


class Event(TypedDict, total=False):
    event_id: int
    title: str
    description: str
    category: Category
    venue_name: str
    address: str
    city: str
    country_code: str
    latitude: float
    longitude: float
    starts_at: str
    ends_at: str
    url: str
    advertised_name: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: Optional[str]
    image: str
    image_large: str
    image_thumb: str
    event_status: str
    attendees: str
    owner: EventOwner
    environment: str
    reschedule_count: int
    cloned_from_event_id: Optional[int]
    creation_datetime: str
    last_edited_at: Optional[str]


class EventDetail(Event, total=False):
    """One event with the extra fields ``events.get`` returns."""

    can_manage: bool
    can_delete: bool
    listing_price: float
    billing_currency: str
    invoice_id: Optional[str]
    app_synced_at: Optional[str]
    has_member_interaction: bool
    image_master: Dict[str, Any]
    history: List[Dict[str, Any]]


class EventPage(TypedDict, total=False):
    data: List[Event]
    pagination: Pagination


class EventEditParams(TypedDict, total=False):
    title: str
    description: str
    url: str
    advertised_name: str
    venue_name: str
    address: str
    city: str
    country_code: str
    location: List[float]
    price_min: Union[float, str]
    price_max: Union[float, str]
    currency: str
    image: ImageInput
    preview_token: str
    source_event_id: int
    crop: Crop


class EventEditResult(TypedDict, total=False):
    return_code: str
    message: str
    event_id: int
    status: str
    category: Category
    changed_fields: List[str]
    image: str
    image_large: str
    venue_changed: bool


class EventRescheduleParams(TypedDict):
    starts_at: str
    ends_at: str


class EventRescheduleResult(TypedDict, total=False):
    return_code: str
    message: str
    event_id: int
    status: str
    starts_at: str
    ends_at: str


class EventCancelResult(TypedDict, total=False):
    return_code: str
    message: str
    event_id: int
    status: str
    dry_run: bool


class EventAnalyticsMetrics(TypedDict, total=False):
    clicks: int
    attendees: str
    invites_sent: str
    invites_accepted: str


class EventAnalytics(TypedDict, total=False):
    event_id: int
    interval: str
    starts_at: str
    ends_at: str
    status: str
    metrics: EventAnalyticsMetrics
    as_of: str


# --------------------------------------------------------------------------
# Webhook endpoints and webhook events
# --------------------------------------------------------------------------


class WebhookEndpoint(TypedDict, total=False):
    return_code: str
    id: str
    url: str
    description: str
    enabled_events: List[str]
    status: Literal["enabled", "disabled"]
    livemode: bool
    created: str
    last_success_at: Optional[str]
    failing_since: Optional[str]
    disabled_by: Optional[str]
    disabled_reason: Optional[str]
    previous_secret_expires_at: Optional[str]


class WebhookEndpointWithSecret(WebhookEndpoint, total=False):
    secret: str
    """The signing secret. It is returned only once: store it safely."""


class WebhookEndpointList(TypedDict, total=False):
    return_code: str
    data: List[WebhookEndpoint]


class _WebhookEndpointCreateRequired(TypedDict):
    url: str
    enabled_events: List[Union[WebhookEventType, Literal["*"]]]


class WebhookEndpointCreateParams(_WebhookEndpointCreateRequired, total=False):
    description: str


class WebhookEndpointUpdateParams(TypedDict, total=False):
    url: str
    enabled_events: List[Union[WebhookEventType, Literal["*"]]]
    description: str
    status: Literal["enabled", "disabled"]


class WebhookEndpointDeleted(TypedDict, total=False):
    return_code: str
    id: str
    deleted: bool


class WebhookRollSecretParams(TypedDict, total=False):
    expires_in: Literal["now", "1h", "24h", "7d"]


class WebhookTestParams(TypedDict, total=False):
    type: WebhookEventType


class WebhookDelivery(TypedDict, total=False):
    endpoint_id: str
    status: str
    attempts: int
    last_http_status: Optional[int]
    last_error: Optional[str]
    next_attempt_at: Optional[str]
    delivered_at: Optional[str]


class WebhookTestResult(TypedDict, total=False):
    return_code: str
    webhook_event_id: str
    type: str
    test: bool
    delivery: WebhookDelivery


class WebhookRequestInfo(TypedDict, total=False):
    source: Literal["api", "mcp", "ad_portal", "agilis", "system"]
    idempotency_key: Optional[str]


class WebhookEventRecord(TypedDict, total=False):
    """A webhook event as ``webhook_events.list`` and ``.get`` return it."""

    return_code: str
    id: str
    type: str
    created: int
    livemode: bool
    test: bool
    data: Dict[str, Any]
    request: WebhookRequestInfo
    deliveries: List[WebhookDelivery]


class WebhookEventListParams(TypedDict, total=False):
    type: WebhookEventType
    delivery_success: bool
    limit: int
    cursor: str


class WebhookEventPage(TypedDict, total=False):
    return_code: str
    data: List[WebhookEventRecord]
    pagination: Pagination


class WebhookResendParams(TypedDict, total=False):
    endpoint_id: str


class WebhookResendResult(TypedDict, total=False):
    return_code: str
    webhook_event_id: str
    deliveries: List[WebhookDelivery]


# --------------------------------------------------------------------------
# Received webhook events (returned by construct_event), typed by ``type``
# --------------------------------------------------------------------------


class _OfferEventData(TypedDict, total=False):
    object: Offer


class _EventEventData(TypedDict, total=False):
    object: Event


class _ObjectData(TypedDict, total=False):
    object: Dict[str, Any]


class OfferWebhookEvent(TypedDict, total=False):
    id: str
    object: str
    type: OfferEventType
    created: int
    livemode: bool
    version: int
    data: _OfferEventData
    request: WebhookRequestInfo


class EventWebhookEvent(TypedDict, total=False):
    id: str
    object: str
    type: EventEventType
    created: int
    livemode: bool
    version: int
    data: _EventEventData
    request: WebhookRequestInfo


class BalanceWebhookEvent(TypedDict, total=False):
    id: str
    object: str
    type: BalanceEventType
    created: int
    livemode: bool
    version: int
    data: _ObjectData
    request: WebhookRequestInfo


class InvoiceWebhookEvent(TypedDict, total=False):
    id: str
    object: str
    type: InvoiceEventType
    created: int
    livemode: bool
    version: int
    data: _ObjectData
    request: WebhookRequestInfo


class TermsWebhookEvent(TypedDict, total=False):
    id: str
    object: str
    type: TermsEventType
    created: int
    livemode: bool
    version: int
    data: _ObjectData
    request: WebhookRequestInfo


WebhookEvent = Union[
    OfferWebhookEvent,
    EventWebhookEvent,
    BalanceWebhookEvent,
    InvoiceWebhookEvent,
    TermsWebhookEvent,
]
"""A received webhook event. Compare ``event["type"]`` to narrow it."""
