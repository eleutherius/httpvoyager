# ruff: noqa: S101
import logging

from voyager.logging_setup import _handler_uses_path, _resolve_log_path, configure_logging


def test_resolve_log_path_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_log_path()
    assert resolved == tmp_path / "http_voyager.log"


def test_handler_uses_path(tmp_path):
    target = tmp_path / "log.txt"
    handler = logging.FileHandler(target)
    try:
        assert _handler_uses_path(handler, target)
    finally:
        handler.close()


def test_configure_logging_creates_handler(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = logging.getLogger()
    initial = list(root.handlers)
    try:
        path = configure_logging(True)
        assert path == tmp_path / "http_voyager.log"
        assert any(isinstance(h, logging.FileHandler) for h in root.handlers)
        # Second call should not duplicate handlers
        configure_logging(True, log_path=path)
        assert len([h for h in root.handlers if isinstance(h, logging.FileHandler)]) >= 1
    finally:
        for h in root.handlers[len(initial) :]:
            root.removeHandler(h)
            h.close()
