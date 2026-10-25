"""HTTP communication component for local request-delivery testing.

This module provides two independent, reusable pieces:

- :func:`publish` -- a small HTTP client that POSTs a JSON payload to a
  configurable receiver. The receiver defaults to a loopback address, so by
  default nothing leaves the host.
- :func:`create_receiver_app` -- a Flask application exposing ``POST /collect``,
  a local receiver used to exercise request delivery in tests.

The module is deliberately decoupled from the file-reading and extraction code
(:mod:`services.passwd_reader`, :mod:`services.local_extractor`): it knows
nothing about where a payload came from and imports neither. It validates
payload format and size, returns appropriate HTTP status codes for invalid
requests, and never writes payload contents to logs -- log records carry only
sizes, status codes and failure types.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

# Default receiver is loopback-only: by default the client talks to a receiver
# running on the same host (e.g. create_receiver_app), so no data leaves the VM.
DEFAULT_RECEIVER_URL = "http://127.0.0.1:8080/collect"

# Reject payloads larger than this before sending or on receipt. Keeps a single
# request bounded for a small test service.
MAX_PAYLOAD_BYTES = 64 * 1024  # 64 KiB


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish attempt.

    On success ``status`` is the receiver's HTTP status code. On failure only
    ``error`` is set.
    """

    ok: bool
    status: Optional[int] = None
    error: Optional[str] = None


def _encode_payload(payload: Any, max_bytes: int) -> bytes:
    """Serialize ``payload`` to compact JSON bytes, enforcing the size limit.

    Raises ``ValueError`` with a short, content-free reason on invalid or
    oversized input.
    """
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")
    try:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("invalid_payload")
    if len(body) > max_bytes:
        raise ValueError("payload_too_large")
    return body


def publish(
    payload: Any,
    url: str = DEFAULT_RECEIVER_URL,
    *,
    timeout: float = 5.0,
    max_bytes: int = MAX_PAYLOAD_BYTES,
) -> PublishResult:
    """POST ``payload`` as JSON to ``url`` and return the outcome.

    ``url`` defaults to :data:`DEFAULT_RECEIVER_URL` (loopback). The payload must
    be a JSON-serializable ``dict`` no larger than ``max_bytes`` once encoded;
    oversized or malformed payloads are rejected locally before any request is
    made.

    Failures are returned rather than raised:

    - ``"invalid_payload"``: payload is not a JSON-serializable dict
    - ``"payload_too_large"``: encoded payload exceeds ``max_bytes``
    - ``"invalid_url"``: ``url`` is not a valid http/https URL
    - ``"http_error"``: the receiver returned a non-2xx status
    - ``"connection_error"``: the receiver could not be reached
    """
    try:
        body = _encode_payload(payload, max_bytes)
    except ValueError as exc:
        logger.warning("refusing to publish: %s", exc)
        return PublishResult(ok=False, error=str(exc))

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        logger.warning("invalid receiver url")
        return PublishResult(ok=False, error="invalid_url")

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        logger.warning("receiver returned status %d", exc.code)
        return PublishResult(ok=False, status=exc.code, error="http_error")
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("could not reach receiver: %s", type(exc).__name__)
        return PublishResult(ok=False, error="connection_error")

    logger.info("published %d bytes, receiver status %d", len(body), status)
    return PublishResult(ok=True, status=status)


def create_receiver_app(max_bytes: int = MAX_PAYLOAD_BYTES) -> Flask:
    """Build a Flask app exposing ``POST /collect`` for local delivery tests.

    The endpoint validates the request and returns a content-free JSON body:

    - ``415`` if the ``Content-Type`` is not ``application/json``
    - ``413`` if the body exceeds ``max_bytes``
    - ``400`` if the body is not a JSON object
    - ``200`` otherwise

    The received payload is never logged; only its size and the resulting status
    are recorded.
    """
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = max_bytes

    @app.post("/collect")
    def collect():
        if request.content_type != "application/json":
            logger.warning("rejected delivery: unsupported media type")
            return jsonify(status="unsupported_media_type"), 415

        raw = request.get_data(cache=True)
        if len(raw) > max_bytes:
            logger.warning("rejected delivery: payload too large")
            return jsonify(status="payload_too_large"), 413

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            logger.warning("rejected delivery: invalid payload")
            return jsonify(status="invalid_payload"), 400

        logger.info("accepted delivery of %d bytes", len(raw))
        return jsonify(status="accepted"), 200

    # Flask aborts with 413 on its own when MAX_CONTENT_LENGTH is exceeded before
    # the view runs; normalize that to the same content-free JSON shape.
    @app.errorhandler(413)
    def _too_large(_exc):
        return jsonify(status="payload_too_large"), 413

    return app


def main() -> None:
    """Console entry point: run the local receiver on loopback for testing.

    Binds to 127.0.0.1:8080; override with RECEIVER_HOST / RECEIVER_PORT.
    """
    import os

    host = os.environ.get("RECEIVER_HOST", "127.0.0.1")
    port = int(os.environ.get("RECEIVER_PORT", "8080"))
    create_receiver_app().run(host=host, port=port)


if __name__ == "__main__":
    # Run the local receiver for manual testing: python -m services.local_publisher
    main()
