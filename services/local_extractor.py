"""Local file-processing utility: extract one line of text to a local file.

The core function :func:`extract_first_line` takes text (such as the output of
:func:`services.passwd_reader.read_passwd`), selects the first non-empty line,
and writes just that line to a configurable local output file created with
owner-only permissions. :func:`extract_from_reader` is a thin convenience that
reuses the existing reader and feeds its output to the core function.

This module never logs file contents (log records carry only paths and the
failure type), makes no network requests, and is not exposed through any HTTP
endpoint.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

from services.passwd_reader import DEFAULT_PASSWD_PATH, read_passwd

logger = logging.getLogger(__name__)

# Default output lives under /tmp so a stray run never writes into the repo or a
# user's home directory. The caller can override it.
DEFAULT_OUTPUT_PATH = "/tmp/ec2-file-test-output.txt"

# Owner read/write only (0o600). No group or other access.
_OWNER_ONLY = 0o600


@dataclass(frozen=True)
class ExtractResult:
    """Outcome of an extraction attempt.

    On success ``output_path`` is the file written and ``line`` is the line that
    was extracted. On failure only ``error`` is set.
    """

    ok: bool
    output_path: Optional[str] = None
    line: Optional[str] = None
    error: Optional[str] = None


def _write_owner_only(path: str, text: str) -> None:
    """Write ``text`` to ``path`` with owner-only (0o600) permissions.

    ``os.open`` applies the mode on creation; the explicit ``chmod`` also
    tightens an existing file that may have looser permissions.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, _OWNER_ONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(path, _OWNER_ONLY)


def extract_first_line(
    text: Optional[str],
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> ExtractResult:
    """Write the first non-empty line of ``text`` to ``output_path``.

    ``output_path`` defaults to :data:`DEFAULT_OUTPUT_PATH` and is created with
    owner-only (0o600) permissions. The extracted line is written with a single
    trailing newline.

    Failures are returned rather than raised:

    - ``"empty"``: ``text`` is ``None`` or has no non-blank line
    - ``"invalid_output_path"``: the output path's directory is missing or is not
      a directory
    - ``"permission_denied"``: the process may not write the output file
    - ``"write_error"``: any other OS-level error while writing the output
    """
    line = _first_non_empty_line(text)
    if line is None:
        logger.warning("no non-blank line in input; nothing to extract")
        return ExtractResult(ok=False, error="empty")

    try:
        _write_owner_only(output_path, line + "\n")
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError):
        logger.warning("invalid output path: %s", output_path)
        return ExtractResult(ok=False, error="invalid_output_path")
    except PermissionError:
        logger.warning("permission denied writing output: %s", output_path)
        return ExtractResult(ok=False, error="permission_denied")
    except OSError as exc:
        logger.warning(
            "failed to write output %s: %s", output_path, type(exc).__name__
        )
        return ExtractResult(ok=False, error="write_error")

    # Log the path and byte count only, never the extracted content.
    logger.info("wrote extracted line to %s (%d bytes)", output_path, len(line) + 1)
    return ExtractResult(ok=True, output_path=output_path, line=line)


def extract_from_reader(
    output_path: str = DEFAULT_OUTPUT_PATH,
    *,
    source_path: str = DEFAULT_PASSWD_PATH,
) -> ExtractResult:
    """Read ``source_path`` via :func:`read_passwd` and extract its first line.

    Convenience wrapper that reuses the existing reader without changing its
    behavior. If the read fails, the reader's own error code (e.g.
    ``"not_found"``, ``"permission_denied"``, ``"empty"``) is returned.
    """
    read_result = read_passwd(source_path)
    if not read_result.ok:
        logger.warning("source read failed (%s): %s", read_result.error, source_path)
        return ExtractResult(ok=False, error=read_result.error)
    return extract_first_line(read_result.content, output_path)


def _first_non_empty_line(text: Optional[str]) -> Optional[str]:
    """Return the first line with non-whitespace content, or ``None``."""
    if not text:
        return None
    for line in text.splitlines():
        if line.strip():
            return line
    return None
