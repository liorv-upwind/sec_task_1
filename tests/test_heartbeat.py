import asyncio
import re

from fastapi.testclient import TestClient

from app.config import get_settings
from app.heartbeat import run_heartbeat, write_heartbeat
from app.main import create_app

LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00 heartbeat$")


def test_default_interval_is_five_minutes(monkeypatch):
    monkeypatch.delenv("HEARTBEAT_INTERVAL_SECONDS", raising=False)
    assert get_settings().heartbeat_interval_seconds == 300


def test_write_heartbeat_appends_timestamped_line(tmp_path):
    log = tmp_path / "nested" / "heartbeat.log"
    write_heartbeat(log, "heartbeat")
    write_heartbeat(log, "heartbeat")
    lines = log.read_text().splitlines()
    assert len(lines) == 2
    assert all(LINE_RE.match(line) for line in lines)


def test_run_heartbeat_repeats_until_cancelled(tmp_path):
    log = tmp_path / "heartbeat.log"

    async def scenario():
        task = asyncio.create_task(run_heartbeat(log, 0.01, "heartbeat"))
        await asyncio.sleep(0.1)
        task.cancel()

    asyncio.run(scenario())
    assert len(log.read_text().splitlines()) >= 3


def test_app_lifespan_starts_heartbeat(tmp_path):
    with TestClient(create_app()):
        pass
    log = tmp_path / "heartbeat.log"
    assert LINE_RE.match(log.read_text().splitlines()[0])


def test_heartbeat_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTBEAT_ENABLED", "false")
    with TestClient(create_app()):
        pass
    assert not (tmp_path / "heartbeat.log").exists()
