"""Tests for services.local_publisher.

The receiver is exercised with Flask's test client; the client's network layer
is mocked so no real socket is opened.
"""

import json
import logging
import unittest
from unittest import mock

from services.local_publisher import (
    DEFAULT_RECEIVER_URL,
    MAX_PAYLOAD_BYTES,
    PublishResult,
    create_receiver_app,
    publish,
)


class _FakeResponse:
    """Minimal context-manager stand-in for urlopen's return value."""

    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ReceiverAppTests(unittest.TestCase):
    def setUp(self):
        self.client = create_receiver_app().test_client()

    def test_accepts_valid_json_object(self):
        resp = self.client.post("/collect", json={"host": "demo", "value": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "accepted"})

    def test_rejects_non_json_content_type(self):
        resp = self.client.post(
            "/collect", data="hello", content_type="text/plain"
        )
        self.assertEqual(resp.status_code, 415)

    def test_rejects_non_object_json(self):
        resp = self.client.post(
            "/collect", data="[1, 2, 3]", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_malformed_json(self):
        resp = self.client.post(
            "/collect", data="{not json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_oversized_payload(self):
        app = create_receiver_app(max_bytes=128)
        client = app.test_client()
        big = {"blob": "x" * 500}
        resp = client.post("/collect", json=big)
        self.assertEqual(resp.status_code, 413)

    def test_payload_contents_never_logged(self):
        secret = "do-not-log-me-12345"
        with self.assertLogs("services.local_publisher", level="DEBUG") as cm:
            self.client.post("/collect", json={"secret": secret})
        joined = "\n".join(cm.output)
        self.assertNotIn(secret, joined)


class PublishClientTests(unittest.TestCase):
    def test_default_receiver_is_loopback(self):
        self.assertTrue(DEFAULT_RECEIVER_URL.startswith("http://127.0.0.1"))

    def test_rejects_non_dict_payload_without_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            result = publish(["not", "a", "dict"])
        self.assertEqual(result, PublishResult(ok=False, error="invalid_payload"))
        urlopen.assert_not_called()

    def test_rejects_oversized_payload_without_network(self):
        payload = {"blob": "x" * (MAX_PAYLOAD_BYTES + 1)}
        with mock.patch("urllib.request.urlopen") as urlopen:
            result = publish(payload)
        self.assertEqual(result.error, "payload_too_large")
        urlopen.assert_not_called()

    def test_rejects_invalid_url_without_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            result = publish({"a": 1}, url="ftp://example/collect")
        self.assertEqual(result.error, "invalid_url")
        urlopen.assert_not_called()

    def test_successful_publish(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
            result = publish({"host": "demo"})
        self.assertEqual(result, PublishResult(ok=True, status=200))

    def test_http_error_is_returned(self):
        import urllib.error

        err = urllib.error.HTTPError(
            DEFAULT_RECEIVER_URL, 400, "Bad Request", hdrs=None, fp=None
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            result = publish({"host": "demo"})
        self.assertEqual(result.ok, False)
        self.assertEqual(result.status, 400)
        self.assertEqual(result.error, "http_error")

    def test_connection_error_is_returned(self):
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("unreachable"),
        ):
            result = publish({"host": "demo"})
        self.assertEqual(result.error, "connection_error")

    def test_payload_contents_never_logged(self):
        secret = "client-secret-98765"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
            with self.assertLogs("services.local_publisher", level="DEBUG") as cm:
                publish({"token": secret})
        self.assertNotIn(secret, "\n".join(cm.output))


class EndToEndLoopbackTests(unittest.TestCase):
    """Drive the client against the receiver via the Werkzeug test client."""

    def test_client_payload_accepted_by_receiver(self):
        client = create_receiver_app().test_client()

        def fake_urlopen(req, timeout=None):
            # Route the client's request to the in-process receiver, using only
            # the URL path so the Werkzeug test client handles it.
            path = "/" + req.full_url.split("://", 1)[1].split("/", 1)[1]
            resp = client.post(
                path,
                data=req.data,
                content_type=req.headers.get("Content-type"),
            )
            return _FakeResponse(resp.status_code)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = publish({"host": "demo", "n": 3}, url=DEFAULT_RECEIVER_URL)
        self.assertEqual(result, PublishResult(ok=True, status=200))


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
