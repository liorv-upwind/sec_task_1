"""Read the local ``/etc/passwd`` file using the process's normal permissions.

The reader never logs file contents; log records only carry the path and the
kind of failure.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PASSWD_PATH = "/etc/passwd"


@dataclass(frozen=True)
class PasswdReadResult:
    """Outcome of a read attempt.

    ``content`` is set only on success; ``error`` is set only on failure.
    """

    ok: bool
    content: Optional[str] = None
    error: Optional[str] = None


def read_passwd(path: str = DEFAULT_PASSWD_PATH) -> PasswdReadResult:
    """Read ``path`` and return its text, or a result describing why it failed.

    Failures are returned rather than raised:

    - ``"not_found"``: the file does not exist
    - ``"permission_denied"``: the process may not read the file
    - ``"empty"``: the file exists but contains no non-whitespace data
    - ``"not_a_file"``: the path is a directory
    - ``"read_error"``: any other OS-level or decoding error
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except FileNotFoundError:
        logger.warning("passwd file not found: %s", path)
        return PasswdReadResult(ok=False, error="not_found")
    except PermissionError:
        logger.warning("permission denied reading passwd file: %s", path)
        return PasswdReadResult(ok=False, error="permission_denied")
    except IsADirectoryError:
        logger.warning("passwd path is a directory: %s", path)
        return PasswdReadResult(ok=False, error="not_a_file")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("failed to read passwd file %s: %s", path, type(exc).__name__)
        return PasswdReadResult(ok=False, error="read_error")

    if not content.strip():
        logger.warning("passwd file is empty: %s", path)
        return PasswdReadResult(ok=False, error="empty")

    logger.info("read passwd file %s (%d bytes)", path, len(content))
    return PasswdReadResult(ok=True, content=content)
