from __future__ import annotations

import logging
from pathlib import Path

DEFAULT_LOG_FILENAME = "http_voyager.log"


def _resolve_log_path(log_path: Path | None = None) -> Path:
    """Return absolute path for the log file."""
    if log_path is None:
        return Path.cwd() / DEFAULT_LOG_FILENAME
    return Path(log_path).expanduser().resolve()


def _handler_uses_path(handler: logging.Handler, path: Path) -> bool:
    """Check whether a handler already writes to the given path."""
    file_name = getattr(handler, "baseFilename", None)
    if not file_name:
        return False
    try:
        return Path(file_name).resolve() == path
    except OSError:
        return False


def configure_logging(debug_enabled: bool, log_path: Path | None = None) -> Path | None:
    """Enable debug logging to a file in the current working directory."""
    if not debug_enabled:
        return None

    path = _resolve_log_path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        return None
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not any(_handler_uses_path(existing, path) for existing in root.handlers):
        root.addHandler(handler)

    logging.getLogger(__name__).debug("Debug logging enabled. Writing to %s", path)
    return path
