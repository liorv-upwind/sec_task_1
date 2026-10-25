from fastapi.testclient import TestClient

from app.main import create_app


def test_health():
    with TestClient(create_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_info_reflects_settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    with TestClient(create_app()) as client:
        resp = client.get("/info")
    assert resp.json() == {"name": "heartbeat-service", "environment": "test"}
