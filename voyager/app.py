from typing import Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, TabbedContent

from .config import DEFAULT_TABS
from .docs_tab import DocumentationTab
from .models import GraphQLTabSpec
from .storage import load_last_state, save_state
from .tabs import GraphQLTab


class GraphQLVoyager(App[None]):
    """A tabbed console GraphQL client built with Textual."""

    CSS = """
    Screen {
        background: #0b1221;
    }

    #app-header {
        background: #1f2f6b;
        color: white;
    }

    #main {
        height: 1fr;
        padding: 0 1;
    }

    TabbedContent, TabPane {
        height: 1fr;
    }

    .columns {
        height: 1fr;
        border: round #1f2d4a;
    }

    .left-panel, .right-panel {
        padding: 0 1;
        background: #0f182b;
    }

    .left-panel {
        width: 60%;
        border-right: tall #1f2d4a;
    }

    .right-panel {
        width: 40%;
        height: 1fr;
        layout: vertical;
    }

    .box {
        border: round #22345b;
        background: #0b1529;
    }

    .query-box {
        height: 15;
    }

    .vars-box, .headers-box {
        height: 5;
    }

    .response-actions {
        margin-bottom: 1;
    }

    .response-box {
        height: 100%;
        min-height: 100%;
        max-height: 100%;
        scrollbar-size-vertical: 1;
        scrollbar-color: #4f8dff;
        scrollbar-background: #0b1221;
    }

    .query-scroll {
        scrollbar-size-vertical: 1;
        scrollbar-color: #4f8dff;
        scrollbar-background: #0b1221;
    }

    .status {
        color: #87d7ff;
        padding: 0 1;
    }

    .label {
        color: #8fb2ff;
        text-style: bold;
    }

    .actions SmallButton, .response-actions SmallButton {
        margin-right: 1;
    }

    .endpoint-input {
        width: 100%;
        min-width: 100%;
        max-width: 100%;
        background: #0b1529;
        color: #e5edff;
        border: tall #22345b;
    }

    .endpoint-input:focus {
        border: tall #4f8dff;
    }

    Checkbox {
        padding: 0;
        background: transparent;
        border: none;
    }

    Checkbox .toggle--button {
        width: 2;
        height: 2;
        min-width: 2;
        min-height: 2;
        border: tall #7fa6ff;
        background: #162540;
    }

    Checkbox.-checked .toggle--button {
        background: #4a7dff;
        color: #0b1221;
        border: tall #4a7dff;
    }

    Checkbox:hover .toggle--button {
        border: tall #a6c3ff;
    }

    Checkbox .toggle--label {
        padding-left: 1;
    }

    .docs-columns {
        height: 1fr;
    }

    .docs-display {
        padding: 0 1;
        layout: vertical;
        height: 1fr;
    }

    .docs-tree {
        height: 1fr;
        min-height: 0;
        scrollbar-size-vertical: 1;
    }

    .docs-display .response-box {
        height: 1fr;
        min-height: 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "send", "Send query"),
        Binding("f5", "send", "Send query"),
        Binding("ctrl+enter", "send", "Send query"),
        Binding("ctrl+l", "focus_endpoint", "Focus endpoint"),
        Binding("ctrl+shift+c", "copy_response", "Copy response"),
        Binding("meta+c", "copy_response", "Copy response"),  # macOS Command+C
        Binding("meta+shift+c", "copy_response", "Copy response"),  # macOS Command+Shift+C
        Binding("f12", "quit", "Quit"),
    ]

    def __init__(self, tab_specs: Sequence[GraphQLTabSpec] | GraphQLTabSpec | None = None) -> None:
        super().__init__()
        base_spec = self._normalize_spec(tab_specs)
        self.tab_spec = load_last_state(base_spec)
        self.view: GraphQLTab | None = None
        self.docs_view: DocumentationTab | None = None

    def compose(self) -> ComposeResult:
        yield Header(id="app-header", show_clock=True)
        with Container(id="main"):
            with TabbedContent(id="tabs"):
                self.view = GraphQLTab(self.tab_spec)
                self.docs_view = DocumentationTab(self.tab_spec)
                yield self.view
                yield self.docs_view
        yield Footer()

    def on_mount(self) -> None:
        if self.view:
            self.view.focus_query()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:  # type: ignore[override]
        if event.tab.id == "docs" and self.view and self.docs_view:
            self.docs_view.set_from_spec(self.view.current_spec())

    async def action_send(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, GraphQLTab):
            await tab.send()

    def action_focus_endpoint(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, GraphQLTab):
            tab.focus_endpoint()

    async def action_copy_response(self) -> None:
        tab = self._active_tab()
        if isinstance(tab, GraphQLTab):
            await tab.copy_response()

    def save_state(self, spec: GraphQLTabSpec) -> None:
        try:
            save_state(spec)
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
        if active_id == "docs":
            return self.docs_view
        return self.view
