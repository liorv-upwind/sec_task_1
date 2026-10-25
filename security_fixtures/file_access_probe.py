"""Fixture: sensitive-file read pattern.

Reads a passwd-format file. Locked to the fabricated fixture file next to this
module; any other path is rejected.
"""
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FAKE_PASSWD = FIXTURE_DIR / "fake_passwd.txt"


def read_passwd(path: Path = FAKE_PASSWD) -> str:
    resolved = Path(path).resolve()
    if resolved != FAKE_PASSWD:
        raise PermissionError(f"fixture may only read {FAKE_PASSWD}")
    return resolved.read_text(encoding="utf-8")


def parse_accounts(text: str) -> list[dict[str, str]]:
    accounts = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, uid, gid, gecos, home, shell = line.split(":")
        accounts.append({"user": name, "uid": uid, "gid": gid, "home": home, "shell": shell})
    return accounts
