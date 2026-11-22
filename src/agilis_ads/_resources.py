"""The API's resources: ``client.offers``, ``client.events`` and the others."""

from __future__ import annotations

import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    Mapping,
    Optional,
    TypeVar,
    Union,
    cast,
)

from ._multipart import form_parts
from .types import (
    AnalyticsParams,
    CategoryList,
    Event,
    EventAnalytics,
    EventCancelResult,
    EventCategoryList,
    EventConfig,
    EventCurrencyList,
    EventDetail,
    EventEditParams,
    EventEditResult,
    EventListParams,
    EventPage,
    EventPreview,
    EventPreviewParams,
    EventPublishParams,
    EventPublishResult,
    EventRescheduleParams,
    EventRescheduleResult,
    InterestList,
    Offer,
    OfferAnalytics,
    OfferCreateParams,
    OfferCreateResult,
    OfferListParams,
    OfferPage,
    OfferPriceEstimate,
    OfferPriceEstimateParams,
    ReturnCodeResult,
    WebhookEndpoint,
    WebhookEndpointCreateParams,
    WebhookEndpointDeleted,
    WebhookEndpointList,
    WebhookEndpointUpdateParams,
    WebhookEndpointWithSecret,
    WebhookEventListParams,
    WebhookEventPage,
    WebhookEventRecord,
    WebhookResendParams,
    WebhookResendResult,
    WebhookRollSecretParams,
    WebhookTestParams,
    WebhookTestResult,
)

if TYPE_CHECKING:
    from ._client import Agilis

__all__ = [
    "Categories",
    "EventCategories",
    "EventConfigResource",
    "EventCurrencies",
    "Events",
    "Interests",
    "Offers",
    "WebhookEndpoints",
    "WebhookEvents",
]

T = TypeVar("T")
Id = Union[int, str]


def _dry_run(dry_run: bool) -> Optional[Dict[str, Any]]:
    return {"dry_run": True} if dry_run else None


def _idempotency(key: Optional[str]) -> Dict[str, str]:
    # Generated once per call, so every retry of the call sends the same key.
    return {"Idempotency-Key": key or str(uuid.uuid4())}


def _auto_page(
    fetch: Callable[[Dict[str, Any]], Mapping[str, Any]], params: Optional[Mapping[str, Any]]
) -> Iterator[Any]:
    query: Dict[str, Any] = dict(params or {})
    while True:
        page = fetch(query)
        yield from page.get("data") or []
        pagination = page.get("pagination") or {}
        next_cursor = pagination.get("next_cursor")
        if not pagination.get("has_more") or not next_cursor:
            return
        query = {**query, "cursor": next_cursor}


class _Resource:
    def __init__(self, client: Agilis) -> None:
        self._client = client


class Categories(_Resource):
    def list(self) -> CategoryList:
        """``GET /categories``: the Offer categories."""
        return cast(CategoryList, self._client._request("GET", "/categories"))


class Interests(_Resource):
    def list(self) -> InterestList:
        """``GET /interests``: the interests an Offer can target."""
        return cast(InterestList, self._client._request("GET", "/interests"))


class Offers(_Resource):
    def estimate_price(self, params: OfferPriceEstimateParams) -> OfferPriceEstimate:
        """``POST /offers/price-estimate``: what an Offer would cost.

        ``environment`` is filled in from the key when left out.
        """
        body = self._client._with_environment(params)
        return cast(
            OfferPriceEstimate,
            self._client._request("POST", "/offers/price-estimate", json=body),
        )

    def create(
        self,
        params: OfferCreateParams,
        *,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False,
    ) -> OfferCreateResult:
        """``POST /offers``: create an Offer (multipart, with its image).

        An ``Idempotency-Key`` is sent with every call (yours, or a new UUID) and
        reused on retries. ``dry_run=True`` checks the Offer without creating it.
        ``environment`` is filled in from the key when left out.
        """
        parts = form_parts(self._client._with_environment(params))
        return cast(
            OfferCreateResult,
            self._client._request(
                "POST",
                "/offers",
                query=_dry_run(dry_run),
                multipart=parts,
                headers=_idempotency(idempotency_key),
            ),
        )

    def list(self, params: Optional[OfferListParams] = None) -> OfferPage:
        """``GET /offers``: one page of your Offers, newest first."""
        query = self._client._with_environment(params)
        return cast(OfferPage, self._client._request("GET", "/offers", query=query))

    def iter_all(self, params: Optional[OfferListParams] = None) -> Iterator[Offer]:
        """Every Offer, following ``next_cursor`` from page to page."""
        return _auto_page(lambda q: self.list(cast(OfferListParams, q)), params)

    def pause(self, offer_id: Id) -> ReturnCodeResult:
        """``POST /offers/{offer_id}/pause``."""
        path = self._client._path("/offers/{}/pause", offer_id)
        return cast(ReturnCodeResult, self._client._request("POST", path))

    def resume(self, offer_id: Id) -> ReturnCodeResult:
        """``POST /offers/{offer_id}/resume``. Success is ``S2``."""
        path = self._client._path("/offers/{}/resume", offer_id)
        return cast(ReturnCodeResult, self._client._request("POST", path))

    def analytics(self, offer_id: Id, params: AnalyticsParams) -> OfferAnalytics:
        """``GET /offers/{offer_id}/analytics``: views and clicks over ``interval``."""
        path = self._client._path("/offers/{}/analytics", offer_id)
        return cast(OfferAnalytics, self._client._request("GET", path, query=params))

    def delete(self, offer_id: Id, *, dry_run: bool = False) -> ReturnCodeResult:
        """``DELETE /offers/{offer_id}``. ``dry_run=True`` shows what deleting would do."""
        path = self._client._path("/offers/{}", offer_id)
        return cast(
            ReturnCodeResult, self._client._request("DELETE", path, query=_dry_run(dry_run))
        )


class EventCategories(_Resource):
    def list(self) -> EventCategoryList:
        """``GET /event-categories``."""
        return cast(EventCategoryList, self._client._request("GET", "/event-categories"))


class EventCurrencies(_Resource):
    def list(self) -> EventCurrencyList:
        """``GET /event-currencies``."""
        return cast(EventCurrencyList, self._client._request("GET", "/event-currencies"))


class EventConfigResource(_Resource):
    def get(self) -> EventConfig:
        """``GET /event-config``: the listing fee, your balance and the image rules."""
        return cast(EventConfig, self._client._request("GET", "/event-config"))


class Events(_Resource):
    def preview(self, params: Optional[EventPreviewParams] = None) -> EventPreview:
        """``POST /events/preview``: the category, fee and image an Event would get.

        ``environment`` is filled in from the key when left out.
        """
        parts = form_parts(self._client._with_environment(params))
        return cast(EventPreview, self._client._request("POST", "/events/preview", multipart=parts))

    def publish(
        self,
        params: EventPublishParams,
        *,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False,
    ) -> EventPublishResult:
        """``POST /events``: publish an Event (multipart).

        An ``Idempotency-Key`` is sent with every call (yours, or a new UUID) and
        reused on retries. ``dry_run=True`` checks the Event without publishing it.
        ``environment`` is filled in from the key when left out.
        """
        parts = form_parts(self._client._with_environment(params))
        return cast(
            EventPublishResult,
            self._client._request(
                "POST",
                "/events",
                query=_dry_run(dry_run),
                multipart=parts,
                headers=_idempotency(idempotency_key),
            ),
        )

    def list(self, params: Optional[EventListParams] = None) -> EventPage:
        """``GET /events``: one page of Events, newest first."""
        query = self._client._with_environment(params)
        return cast(EventPage, self._client._request("GET", "/events", query=query))

    def iter_all(self, params: Optional[EventListParams] = None) -> Iterator[Event]:
        """Every Event, following ``next_cursor`` from page to page."""
        return _auto_page(lambda q: self.list(cast(EventListParams, q)), params)

    def get(self, event_id: Id) -> EventDetail:
        """``GET /events/{event_id}``."""
        path = self._client._path("/events/{}", event_id)
        return cast(EventDetail, self._client._request("GET", path))

    def edit(self, event_id: Id, params: EventEditParams) -> EventEditResult:
        """``PATCH /events/{event_id}``: change a published Event (multipart).

        With a new ``image`` it is sent as ``POST`` with ``X-HTTP-Method-Override: PATCH``.
        """
        path = self._client._path("/events/{}", event_id)
        parts = form_parts(params)
        if params.get("image") is not None:
            result = self._client._request(
                "POST", path, multipart=parts, headers={"X-HTTP-Method-Override": "PATCH"}
            )
        else:
            result = self._client._request("PATCH", path, multipart=parts)
        return cast(EventEditResult, result)

    def delete(self, event_id: Id, *, dry_run: bool = False) -> ReturnCodeResult:
        """``DELETE /events/{event_id}``. ``dry_run=True`` shows what deleting would do."""
        path = self._client._path("/events/{}", event_id)
        return cast(
            ReturnCodeResult, self._client._request("DELETE", path, query=_dry_run(dry_run))
        )

    def reschedule(self, event_id: Id, params: EventRescheduleParams) -> EventRescheduleResult:
        """``POST /events/{event_id}/reschedule``: new start and end times."""
        path = self._client._path("/events/{}/reschedule", event_id)
        return cast(EventRescheduleResult, self._client._request("POST", path, json=params))

    def cancel(self, event_id: Id, *, dry_run: bool = False) -> EventCancelResult:
        """``POST /events/{event_id}/cancel``. ``dry_run=True`` shows what cancelling would do."""
        path = self._client._path("/events/{}/cancel", event_id)
        return cast(EventCancelResult, self._client._request("POST", path, query=_dry_run(dry_run)))

    def analytics(self, event_id: Id, params: AnalyticsParams) -> EventAnalytics:
        """``GET /events/{event_id}/analytics``."""
        path = self._client._path("/events/{}/analytics", event_id)
        return cast(EventAnalytics, self._client._request("GET", path, query=params))


class WebhookEndpoints(_Resource):
    def list(self) -> WebhookEndpointList:
        """``GET /webhook-endpoints``."""
        return cast(WebhookEndpointList, self._client._request("GET", "/webhook-endpoints"))

    def create(self, params: WebhookEndpointCreateParams) -> WebhookEndpointWithSecret:
        """``POST /webhook-endpoints``. The response holds the signing ``secret``, once."""
        return cast(
            WebhookEndpointWithSecret,
            self._client._request("POST", "/webhook-endpoints", json=params),
        )

    def get(self, endpoint_id: str) -> WebhookEndpoint:
        """``GET /webhook-endpoints/{endpoint_id}``."""
        path = self._client._path("/webhook-endpoints/{}", endpoint_id)
        return cast(WebhookEndpoint, self._client._request("GET", path))

    def update(self, endpoint_id: str, params: WebhookEndpointUpdateParams) -> WebhookEndpoint:
        """``PATCH /webhook-endpoints/{endpoint_id}``."""
        path = self._client._path("/webhook-endpoints/{}", endpoint_id)
        return cast(WebhookEndpoint, self._client._request("PATCH", path, json=params))

    def delete(self, endpoint_id: str) -> WebhookEndpointDeleted:
        """``DELETE /webhook-endpoints/{endpoint_id}``."""
        path = self._client._path("/webhook-endpoints/{}", endpoint_id)
        return cast(WebhookEndpointDeleted, self._client._request("DELETE", path))

    def roll_secret(
        self, endpoint_id: str, params: Optional[WebhookRollSecretParams] = None
    ) -> WebhookEndpointWithSecret:
        """``POST /webhook-endpoints/{endpoint_id}/roll-secret``. The new secret is shown once."""
        path = self._client._path("/webhook-endpoints/{}/roll-secret", endpoint_id)
        return cast(
            WebhookEndpointWithSecret,
            self._client._request("POST", path, json=dict(params or {})),
        )

    def send_test(
        self, endpoint_id: str, params: Optional[WebhookTestParams] = None
    ) -> WebhookTestResult:
        """``POST /webhook-endpoints/{endpoint_id}/test``: send a test event now."""
        path = self._client._path("/webhook-endpoints/{}/test", endpoint_id)
        return cast(WebhookTestResult, self._client._request("POST", path, json=dict(params or {})))


class WebhookEvents(_Resource):
    def list(self, params: Optional[WebhookEventListParams] = None) -> WebhookEventPage:
        """``GET /webhook-events``: one page of the last 30 days' events."""
        return cast(
            WebhookEventPage,
            self._client._request("GET", "/webhook-events", query=dict(params or {})),
        )

    def iter_all(
        self, params: Optional[WebhookEventListParams] = None
    ) -> Iterator[WebhookEventRecord]:
        """Every webhook event, following ``next_cursor`` from page to page."""
        return _auto_page(lambda q: self.list(cast(WebhookEventListParams, q)), params)

    def get(self, webhook_event_id: str) -> WebhookEventRecord:
        """``GET /webhook-events/{webhook_event_id}``."""
        path = self._client._path("/webhook-events/{}", webhook_event_id)
        return cast(WebhookEventRecord, self._client._request("GET", path))

    def resend(
        self, webhook_event_id: str, params: Optional[WebhookResendParams] = None
    ) -> WebhookResendResult:
        """``POST /webhook-events/{webhook_event_id}/resend``: to all endpoints, or one."""
        path = self._client._path("/webhook-events/{}/resend", webhook_event_id)
        return cast(
            WebhookResendResult, self._client._request("POST", path, json=dict(params or {}))
        )
