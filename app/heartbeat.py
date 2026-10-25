import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def write_heartbeat(log_path: Path, message: str) -> str:
    """Append one timestamped heartbeat line to log_path and return it."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat()} {message}"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return line


async def run_heartbeat(log_path: Path, interval_seconds: float, message: str) -> None:
    """Write a heartbeat immediately, then every interval_seconds until cancelled."""
    while True:
        try:
            write_heartbeat(log_path, message)
        except OSError:
            logger.exception("failed to write heartbeat to %s", log_path)
        await asyncio.sleep(interval_seconds)
