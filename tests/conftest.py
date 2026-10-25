import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Point the heartbeat at a temp file and reset cached settings per test."""
    monkeypatch.setenv("HEARTBEAT_LOG_PATH", str(tmp_path / "heartbeat.log"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
