"""A minimal webhook receiver using only the standard library.

    AGILIS_WEBHOOK_SECRET=whsec_... python examples/webhook_receiver.py

Point a Test-mode webhook endpoint at this server (served over HTTPS in
production), then send it a test event with ``client.webhook_endpoints.send_test``.
"""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from agilis_ads import SIGNATURE_HEADER, SignatureVerificationError, construct_event

SECRET = os.environ["AGILIS_WEBHOOK_SECRET"]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)  # the body exactly as received
        try:
            event = construct_event(raw_body, self.headers.get(SIGNATURE_HEADER, ""), SECRET)
        except SignatureVerificationError:
            self.send_response(400)
            self.end_headers()
            return

        # Answer quickly, then do the work. Use event["id"] to ignore repeats.
        self.send_response(200)
        self.end_headers()

        if event["type"] == "offer.started":
            print("Offer started:", event["data"]["object"].get("offer_id"))
        elif event["type"] == "event.published":
            print("Event published:", event["data"]["object"].get("event_id"))
        else:
            print("Received", event["type"])


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
