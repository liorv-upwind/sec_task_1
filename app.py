"""Minimal Flask service exposing a health endpoint."""

import os

from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "5000"))
    app.run(host=host, port=port)
