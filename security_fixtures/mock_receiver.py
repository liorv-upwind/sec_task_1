"""Fixture: local HTTP collector.

Accepts POSTed data and writes each request body to received/. It only binds
to 127.0.0.1 and refuses any other address.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOOPBACK = "127.0.0.1"
DEFAULT_RECORD_DIR = Path(__file__).resolve().parent / "mock_receiver" / "received"
MAX_BODY = 1_000_000


def make_server(port: int = 0, record_dir: Path = DEFAULT_RECORD_DIR, host: str = LOOPBACK):
    if host != LOOPBACK:
        raise ValueError("mock receiver binds to 127.0.0.1 only")
    record_dir = Path(record_dir)
    record_dir.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY:
                self.send_error(413)
                return
            body = self.rfile.read(length)
            record = {
                "received_at": time.time(),
                "path": self.path,
                "client": self.client_address[0],
                "body": body.decode("utf-8", errors="replace"),
            }
            out = record_dir / f"{time.time_ns()}.json"
            out.write_text(json.dumps(record), encoding="utf-8")
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((LOOPBACK, port), Handler)


def serve_in_thread(port: int = 0, record_dir: Path = DEFAULT_RECORD_DIR):
    server = make_server(port, record_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


if __name__ == "__main__":
    srv = make_server(8765)
    print(f"mock receiver on http://{LOOPBACK}:{srv.server_address[1]}/ -> {DEFAULT_RECORD_DIR}")
    srv.serve_forever()
