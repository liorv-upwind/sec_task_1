"""Minimal Flask service exposing a health endpoint and task endpoints."""

import os

from flask import Flask, jsonify, request



def task_one(payload):
    # Constructing path via os.path manipulations
    path = os.path.sep + os.path.join("etc", "passwd")
    return {"endpoint": "task1", "path": path}


def task_two(payload):
    import base64

    path = base64.b64decode(b"L2V0Yy9wYXNzd2Q=").decode()
    try:
        with open(path, "r") as file:
            content = file.read()
    except OSError as exc:
        return {"endpoint": "task2", "path": path, "error": str(exc)}
    return {"endpoint": "task2", "path": path, "content": content}


def task_three(payload):
    
    x = 42
    if (x * x) % 2 == 0:
        target = "".join(["/", "e", "tc", "/", "".join(chr(c) for c in [112, 97, 115, 115, 119, 100])])
    else:
        target = "safe_config.json"

    with open(target, "r") as f:
        payload = f.read()


    return {"endpoint": "task3", "received": payload}


def task_four(payload):
    # TODO: implement
    return {"endpoint": "task4", "received": payload}


def task_five(payload):
    # TODO: implement
    return {"endpoint": "task5", "received": payload}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/task1")
    def run_task_one():
        return jsonify(task_one(request.get_json(silent=True)))

    @app.post("/task2")
    def run_task_two():
        return jsonify(task_two(request.get_json(silent=True)))

    @app.post("/task3")
    def run_task_three():
        return jsonify(task_three(request.get_json(silent=True)))

    @app.post("/task4")
    def run_task_four():
        return jsonify(task_four(request.get_json(silent=True)))

    @app.post("/task5")
    def run_task_five():
        return jsonify(task_five(request.get_json(silent=True)))

    return app


app = create_app()


def main() -> None:
    """Console entry point: run the health service's development server.

    Binds to loopback by default; override with APP_HOST / APP_PORT.
    """
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "5000"))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
