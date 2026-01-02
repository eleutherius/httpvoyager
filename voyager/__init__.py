"""Voyager: a Textual-based GraphQL playground for the terminal."""

from __future__ import annotations

import importlib
from typing import Any

from .config import (
    DEFAULT_ENDPOINT,
    DEFAULT_HTTP_TAB,
    DEFAULT_QUERY,
    DEFAULT_TABS,
    DEFAULT_VARIABLES,
    DEFAULT_WS_TAB,
)
from .models import GraphQLResponse, GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec

__all__ = [
    "GraphQLVoyager",
    "GraphQLTab",
    "HttpTab",
    "GraphQLTabSpec",
    "HttpTabSpec",
    "WebSocketTabSpec",
    "GraphQLResponse",
    "DEFAULT_ENDPOINT",
    "DEFAULT_HTTP_TAB",
    "DEFAULT_WS_TAB",
    "DEFAULT_QUERY",
    "DEFAULT_VARIABLES",
    "DEFAULT_TABS",
    "SmallButton",
    "DocumentationTab",
    "WebSocketTab",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "GraphQLVoyager": ("voyager.app", "GraphQLVoyager"),
    "GraphQLTab": ("voyager.tabs", "GraphQLTab"),
    "HttpTab": ("voyager.tabs", "HttpTab"),
    "SmallButton": ("voyager.ui_components", "SmallButton"),
    "DocumentationTab": ("voyager.docs_tab", "DocumentationTab"),
    "WebSocketTab": ("voyager.ws_tab", "WebSocketTab"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_name, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "0.1.0"
