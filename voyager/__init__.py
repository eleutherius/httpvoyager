"""Voyager: a Textual-based GraphQL playground for the terminal."""

from .app import GraphQLVoyager
from .config import DEFAULT_ENDPOINT, DEFAULT_QUERY, DEFAULT_TABS, DEFAULT_VARIABLES
from .docs_tab import DocumentationTab
from .models import GraphQLResponse, GraphQLTabSpec
from .tabs import GraphQLTab
from .ui import SmallButton

__all__ = [
    "GraphQLVoyager",
    "GraphQLTab",
    "GraphQLTabSpec",
    "GraphQLResponse",
    "DEFAULT_ENDPOINT",
    "DEFAULT_QUERY",
    "DEFAULT_VARIABLES",
    "DEFAULT_TABS",
    "SmallButton",
    "DocumentationTab",
]

__version__ = "0.1.0"
