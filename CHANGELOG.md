# Changelog

All notable changes to this package are listed here. It follows [Semantic Versioning](https://semver.org/).

## 0.1.0 (unreleased)

- First release: the `Agilis` client with every operation of the Agilis Advertising REST API (categories, interests, Offers, Events, webhook endpoints and webhook events).
- Typed parameters and responses (`agilis_ads.types`).
- Automatic `Idempotency-Key` on Offer creation and Event publishing, kept across retries.
- Retries with `Retry-After` and exponential backoff.
- Cursor pagination helpers (`iter_all`).
- Webhook signature verification (`construct_event`).
