"""Fixture: collect-and-send pattern.

Reads the fake passwd file and POSTs it to a collector. The collector URL must
be on 127.0.0.1 (normally mock_receiver.py), anything else raises.
"""
import json
import socket
import urllib.request
from urllib.parse import urlparse

from security_fixtures.file_access_probe import parse_accounts, read_passwd

DEFAULT_COLLECTOR = "http://127.0.0.1:8765/collect"


def _require_loopback(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError(f"fixture only sends to http://127.0.0.1, got {url!r}")


def collect() -> dict:
    return {
        "host": socket.gethostname(),
        "accounts": parse_accounts(read_passwd()),
    }


def send(payload: dict, url: str = DEFAULT_COLLECTOR, timeout: float = 5.0) -> int:
    _require_loopback(url)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # loopback only, checked above
        return resp.status


if __name__ == "__main__":
    print(send(collect()))
