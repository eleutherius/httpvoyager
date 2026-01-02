import asyncio
import logging

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Static, TabPane, TextArea, Tree

from .http_client import perform_request
from .introspection import add_types_to_tree, build_introspection_result
from .models import GraphQLTabSpec
from .parsing import parse_headers
from .ui_components import SmallButton

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          type { kind name ofType { kind name ofType { kind name } } }
        }
        type { kind name ofType { kind name ofType { kind name } } }
      }
    }
  }
}
"""


class DocumentationTab(TabPane):
    """Documentation explorer built from GraphQL introspection."""

    busy: reactive[bool] = reactive(False)
    logger = logging.getLogger(__name__)

    def __init__(self, spec: GraphQLTabSpec) -> None:
        super().__init__(title="Docs", id="docs")
        self.spec = spec

    def _wid(self, name: str) -> str:
        return f"{self.id}-{name}"

    def set_from_spec(self, spec: GraphQLTabSpec) -> None:
        self._input("endpoint").value = spec.endpoint
        self._textarea("headers").load_text(spec.headers)
        self._checkbox("verify").value = spec.verify_tls

    def compose(self):
        with Container(classes="layout"):
            with Horizontal(classes="columns docs-columns"):
                with Vertical(classes="left-panel docs-panel"):
                    yield Static("Endpoint", classes="label")
                    yield Input(
                        value=self.spec.endpoint,
                        placeholder="GraphQL endpoint",
                        id=self._wid("endpoint"),
                        classes="endpoint-input",
                    )
                    yield Static("Headers (JSON object or Key: Value per line)", classes="label")
                    yield TextArea(
                        self.spec.headers,
                        language="json",
                        id=self._wid("headers"),
                        classes="box headers-box",
                    )
                    yield Checkbox(
                        "Verify TLS certificates (recommended)",
                        value=self.spec.verify_tls,
                        id=self._wid("verify"),
                    )
                    with Horizontal(classes="actions"):
                        yield SmallButton("Load Schema", id=self._wid("load-docs"), variant="primary")
                        yield SmallButton("Clear", id=self._wid("clear-docs"), variant="ghost")
                    yield Static("", id=self._wid("status"), classes="status")
                with Vertical(classes="right-panel docs-display"):
                    yield Static("Explorer", classes="label")
                    yield Tree("Schema", id=self._wid("tree"), classes="box docs-tree")
                    yield Static("Details", classes="label")
                    yield TextArea(
                        "",
                        language="markdown",
                        id=self._wid("details"),
                        read_only=True,
                        classes="box response-box",
                    )

    def watch_busy(self, busy: bool) -> None:
        self._button("load-docs").disabled = busy
        status = "Loading schema..." if busy else ""
        self._set_status(status)

    async def on_button_pressed(self, event: SmallButton.Pressed) -> None:
        if event.button.id == self._wid("load-docs"):
            asyncio.create_task(self.load_docs())
        elif event.button.id == self._wid("clear-docs"):
            self._clear_tree()
            self._textarea("details").load_text("")
            self._set_status("Cleared.")

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:  # type: ignore[override]
        node = event.node
        data = node.data if isinstance(node.data, dict) else {}
        desc = data.get("description") or ""
        type_repr = data.get("type") or ""
        args_str = data.get("args_str") or ""
        lines = []
        if type_repr:
            lines.append(f"**Type**: {type_repr}")
        if args_str:
            lines.append(f"**Args**: {args_str}")
        if desc:
            lines.append(desc)
        details = "\n\n".join(lines) or node.label.plain
        self._textarea("details").load_text(details)

    async def load_docs(self) -> None:
        if self.busy:
            return

        # Sync from Query tab first (so Docs uses current values by default).
        endpoint = self._input("endpoint").value.strip()
        raw_headers = self._textarea("headers").text
        verify_tls = self._checkbox("verify").value

        query_tab = getattr(self.app, "view", None)  # type: ignore[attr-defined]
        if query_tab:
            try:
                spec = query_tab.current_spec()
            except Exception as exc:  # pragma: no cover - runtime safety
                self.logger.debug("Could not sync from query tab: %s", exc)
                self._set_status("Could not sync from Query tab.")
            else:
                endpoint = spec.endpoint
                raw_headers = spec.headers
                verify_tls = spec.verify_tls
                self.set_from_spec(spec)

        if not endpoint:
            self._set_status("Please provide an endpoint.")
            return

        try:
            headers = parse_headers(raw_headers)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        headers.setdefault("Content-Type", "application/json")
        payload = {"query": INTROSPECTION_QUERY, "variables": {}}

        self.busy = True
        self._textarea("details").load_text(f"Loading schema from {endpoint} ...")
        self._set_status(f"Loading schema from {endpoint} ...")
        try:
            response = await perform_request(endpoint, payload, headers, verify_tls=verify_tls)
        except Exception as exc:
            self._set_status(f"Failed: {exc}")
        else:
            self._populate_tree(response)
        finally:
            self.busy = False

    def _populate_tree(self, response) -> None:
        tree = self._tree()
        self._clear_tree()
        result = build_introspection_result(response)
        if not result.success:
            self._show_tree_message(tree, result.status, result.details)
            return

        add_types_to_tree(tree, result.types)

        tree.root.expand_all()
        tree.refresh(layout=True)
        self._set_status(result.status)
        self._textarea("details").load_text(result.details)
        # Focus on first type to show info immediately.
        first_child = tree.root.children[0] if tree.root.children else None
        if first_child:
            tree.focus_node(first_child)
            tree.scroll_to_node(first_child)

    def _show_tree_message(self, tree: Tree, status: str, details: str) -> None:
        self._set_status(status)
        self._textarea("details").load_text(details)
        tree.refresh(layout=True)

    def _clear_tree(self) -> None:
        tree = self._tree()
        root = tree.root
        # Remove children explicitly; TreeNode has no clear().
        for child in list(root.children):
            child.remove()
        tree.refresh(layout=True)

    def _input(self, name: str) -> Input:
        return self.query_one(f"#{self._wid(name)}", Input)

    def _textarea(self, name: str) -> TextArea:
        return self.query_one(f"#{self._wid(name)}", TextArea)

    def _button(self, name: str) -> SmallButton:
        return self.query_one(f"#{self._wid(name)}", SmallButton)

    def _checkbox(self, name: str) -> Checkbox:
        return self.query_one(f"#{self._wid(name)}", Checkbox)

    def _tree(self) -> Tree:
        return self.query_one(f"#{self._wid('tree')}", Tree)

    def _set_status(self, message: str) -> None:
        self.query_one(f"#{self._wid('status')}", Static).update(message)
