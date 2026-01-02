import os
from collections.abc import Sequence
from importlib.resources import files

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, TabbedContent

from .config import DEFAULT_HTTP_TAB, DEFAULT_TABS, DEFAULT_WS_TAB
from .models import GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec
from .storage import load_last_state, save_state
from .tabs import GraphQLTab, HttpTab
from .ws_tab import WebSocketTab


class GraphQLVoyager(App[None]):
    """A tabbed console GraphQL client built with Textual."""

    CSS = files("voyager.ui_components").joinpath("styles/main.tcss").read_text()

    BINDINGS = [
        Binding("ctrl+s", "send", "Send request"),
        Binding("f5", "send", "Send request"),
        Binding("ctrl+enter", "send", "Send request"),
        Binding("ctrl+l", "focus_endpoint", "Focus endpoint/URL"),
        Binding("ctrl+shift+c", "copy_response", "Copy response"),
        Binding("meta+c", "copy_response", "Copy response"),  # macOS Command+C
        Binding("meta+shift+c", "copy_response", "Copy response"),  # macOS Command+Shift+C
        Binding("f12", "quit", "Quit"),
    ]

    def __init__(
        self,
        tab_specs: Sequence[GraphQLTabSpec] | GraphQLTabSpec | None = None,
        *,
        config_dir: str | None = None,
    ) -> None:
        super().__init__()
        if config_dir:
            os.environ["HTTP_VOYAGER_CONFIG_DIR"] = config_dir
        base_spec = self._normalize_spec(tab_specs)
        self.tab_spec = load_last_state(base_spec, section="graphql")
        self.http_spec = load_last_state(DEFAULT_HTTP_TAB, section="http")
        self.ws_spec = load_last_state(DEFAULT_WS_TAB, section="websocket")
        self.view: GraphQLTab | None = None
        self.http_view: HttpTab | None = None
        self.ws_view: WebSocketTab | None = None

    def compose(self) -> ComposeResult:
        yield Header(id="app-header", show_clock=True)
        with Container(id="main"):
            with TabbedContent(id="tabs"):
                self.view = GraphQLTab(self.tab_spec)
                self.http_view = HttpTab(self.http_spec)
                self.ws_view = WebSocketTab(self.ws_spec)
                yield self.view
                yield self.http_view
                yield self.ws_view
        yield Footer()

    def on_mount(self) -> None:
        if self.view:
            self.view.focus_query()

    async def action_send(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, (GraphQLTab, HttpTab, WebSocketTab)):
            await tab.send()

    def action_focus_endpoint(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, (GraphQLTab, HttpTab, WebSocketTab)):
            tab.focus_endpoint()

    async def action_copy_response(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, (GraphQLTab, HttpTab, WebSocketTab)):
            await tab.copy_response()

    def save_state(self, spec: GraphQLTabSpec | HttpTabSpec | WebSocketTabSpec, section: str) -> None:
        try:
            save_state(spec, section)
        except Exception:
            # Silently ignore persistence failures; UI status is handled in view.
            return

    @staticmethod
    def _normalize_spec(tab_specs: Sequence[GraphQLTabSpec] | GraphQLTabSpec | None) -> GraphQLTabSpec:
        if tab_specs is None:
            return DEFAULT_TABS[0]
        if isinstance(tab_specs, GraphQLTabSpec):
            return tab_specs
        if not tab_specs:
            return DEFAULT_TABS[0]
        return tab_specs[0]

    def _active_tab(self):
        tabs = self.query_one("#tabs", TabbedContent)
        active_id = getattr(tabs, "active", None)
        if active_id == "http":
            return self.http_view
        if active_id == "ws":
            return self.ws_view
        return self.view
