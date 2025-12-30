"""Voyager: a Textual-based GraphQL playground for the terminal."""

from .app import GraphQLVoyager
from .config import (
    DEFAULT_ENDPOINT,
    DEFAULT_HTTP_TAB,
    DEFAULT_QUERY,
    DEFAULT_TABS,
    DEFAULT_VARIABLES,
    DEFAULT_WS_TAB,
)
from .docs_tab import DocumentationTab
from .models import GraphQLResponse, GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec
from .tabs import GraphQLTab, HttpTab
from .ws_tab import WebSocketTab
from .ui_components import SmallButton

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

__version__ = "0.1.0"
