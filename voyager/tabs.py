import asyncio
import json
import logging
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Select, Static, TabPane, TabbedContent, TextArea, Tree

from .http_client import perform_http_request, perform_request
from .models import GraphQLTabSpec, HttpTabSpec
from .parsing import format_response, parse_headers, parse_json_object
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


async def _copy_text_with_fallback(
    app: Any, text: str, logger: logging.Logger, set_status: Callable[[str], None]
) -> None:
    if not text.strip():
        set_status("Nothing to copy.")
        return
    try:
        await app.copy_to_clipboard(text)
    except Exception as exc:  # pragma: no cover - runtime-only clipboard failure
        logger.debug("Textual clipboard copy failed: %s", exc)
    else:
        set_status("Response copied to clipboard.")
        return

    pbcopy_path = shutil.which("pbcopy")
    if not pbcopy_path:
        set_status("Copy failed: no clipboard available.")
        return
    try:
        subprocess.run(  # noqa: S603 - uses local clipboard binary with trusted input
            [pbcopy_path],
            input=text,
            text=True,
            check=True,
            timeout=2,
        )
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover - runtime-only clipboard failure
        logger.debug("pbcopy execution failed: %s", exc)
        set_status("Copy failed: no clipboard available.")
        return

    set_status("Response copied via pbcopy.")


class GraphQLTab(TabPane):
    """Single GraphQL playground view."""

    busy: reactive[bool] = reactive(False)
    logger = logging.getLogger(__name__)

    def __init__(self, spec: GraphQLTabSpec) -> None:
        super().__init__(title="Query", id="query")
        self.spec = spec

    def _wid(self, name: str) -> str:
        return f"{self.id}-{name}"

    def compose(self):
        with Container(classes="layout"):
            with Horizontal(classes="columns"):
                with Vertical(classes="left-panel"):
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
                    yield Static("Variables (JSON)", classes="label")
                    yield TextArea(
                        self.spec.variables,
                        language="json",
                        id=self._wid("variables"),
                        classes="box vars-box",
                    )
                    yield Static("Query", classes="label")
                    yield TextArea(
                        self.spec.query,
                        language="graphql",
                        id=self._wid("query"),
                        show_line_numbers=True,
                        classes="box query-box",
                    )
                    with Horizontal(classes="actions"):
                        yield SmallButton("Send (Ctrl+S / F5)", id=self._wid("send"), variant="primary")
                        yield SmallButton("Load Docs", id=self._wid("load-docs"), variant="ghost")
                        yield SmallButton("Clear", id=self._wid("clear"), variant="ghost")
                        yield SmallButton("Copy", id=self._wid("copy-response"), variant="ghost")
                    yield Static("", id=self._wid("status"), classes="status")
                with TabbedContent(classes="right-tabs"):
                    with TabPane("Response", id=self._wid("response-tab")):
                        yield TextArea(
                            "",
                            language="json",
                            id=self._wid("response"),
                            read_only=True,
                            classes="box response-box",
                        )
                    with TabPane("Docs", id=self._wid("docs-tab")):
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
        self._button("send").disabled = busy
        status = "Sending request..." if busy else ""
        self._set_status(status)

    def focus_endpoint(self) -> None:
        self._input("endpoint").focus()

    def focus_query(self) -> None:
        self._textarea("query").focus()

    def clear_response(self) -> None:
        self._textarea("response").load_text("")

    async def send(self) -> None:
        if self.busy:
            return

        endpoint = self._input("endpoint").value.strip()
        query = self._textarea("query").text.strip()
        raw_variables = self._textarea("variables").text
        raw_headers = self._textarea("headers").text
        verify_tls = self._checkbox("verify").value

        if not endpoint:
            self._set_response("Please provide an endpoint URL.")
            return
        if not query:
            self._set_response("Query is empty. Add a GraphQL query or mutation.")
            return

        try:
            variables = parse_json_object(raw_variables) if raw_variables.strip() else {}
        except ValueError as exc:
            self._set_response(f"Variables are not valid JSON:\n{exc}")
            return

        try:
            headers = parse_headers(raw_headers)
        except ValueError as exc:
            self._set_response(str(exc))
            return

        headers.setdefault("Content-Type", "application/json")
        payload = {"query": query, "variables": variables}

        self.busy = True
        self._set_response("Sending request...")
        try:
            response = await perform_request(endpoint, payload, headers, verify_tls)
        except Exception as exc:  # pragma: no cover - network errors are runtime-only
            self._set_response(f"Request failed: {exc!r}")
        else:
            display = format_response(response)
            self._set_response(display)
            if not verify_tls:
                self._set_status("Warning: TLS verification disabled for this request.")
        finally:
            self.busy = False
            self._persist_state()

    async def copy_response(self) -> None:
        await _copy_text_with_fallback(self.app, self._textarea("response").text, self.logger, self._set_status)

    def on_button_pressed(self, event: SmallButton.Pressed) -> None:
        if event.button.id == self._wid("send"):
            asyncio.create_task(self.send())
        elif event.button.id == self._wid("load-docs"):
            asyncio.create_task(self.load_docs())
        elif event.button.id == self._wid("clear"):
            self.clear_response()
        elif event.button.id == self._wid("copy-response"):
            asyncio.create_task(self.copy_response())

    def _textarea(self, name: str) -> TextArea:
        return self.query_one(f"#{self._wid(name)}", TextArea)

    def _input(self, name: str) -> Input:
        return self.query_one(f"#{self._wid(name)}", Input)

    def _checkbox(self, name: str) -> Checkbox:
        return self.query_one(f"#{self._wid(name)}", Checkbox)

    def _button(self, name: str) -> SmallButton:
        return self.query_one(f"#{self._wid(name)}", SmallButton)

    def _set_response(self, message: str) -> None:
        self._textarea("response").load_text(message)

    def _set_status(self, message: str) -> None:
        self.query_one(f"#{self._wid('status')}", Static).update(message)

    def set_status(self, message: str) -> None:
        self._set_status(message)

    def current_spec(self) -> GraphQLTabSpec:
        return GraphQLTabSpec(
            id=self.spec.id,
            title=self.spec.title,
            endpoint=self._input("endpoint").value.strip(),
            query=self._textarea("query").text,
            variables=self._textarea("variables").text,
            headers=self._textarea("headers").text,
            verify_tls=self._checkbox("verify").value,
        )

    def _persist_state(self) -> None:
        spec = GraphQLTabSpec(
            id=self.spec.id,
            title=self.spec.title,
            endpoint=self._input("endpoint").value.strip(),
            query=self._textarea("query").text,
            variables=self._textarea("variables").text,
            headers=self._textarea("headers").text,
            verify_tls=self._checkbox("verify").value,
        )
        try:
            self.app.save_state(spec, "graphql")  # type: ignore[attr-defined]
        except Exception:
            self._set_status("Could not save state.")

    def _tree(self) -> Tree:
        return self.query_one(f"#{self._wid('tree')}", Tree)


class HttpTab(TabPane):
    """Generic HTTP request tab."""

    busy: reactive[bool] = reactive(False)
    logger = logging.getLogger(__name__)

    METHODS = [
        ("GET", "GET"),
        ("POST", "POST"),
        ("PUT", "PUT"),
        ("PATCH", "PATCH"),
        ("DELETE", "DELETE"),
        ("HEAD", "HEAD"),
        ("OPTIONS", "OPTIONS"),
    ]

    def __init__(self, spec: HttpTabSpec) -> None:
        super().__init__(title="HTTP", id="http")
        self.spec = spec

    def _wid(self, name: str) -> str:
        return f"{self.id}-{name}"

    def compose(self):
        with Container(classes="layout"):
            with Horizontal(classes="columns"):
                with Vertical(classes="left-panel"):
                    with Container(classes="top-section"):
                        with Container(classes="label-container"):
                            yield Static("Request", classes="label")
                        with Horizontal(classes="method-row"):
                            yield Select(
                                self.METHODS,
                                value=self.spec.method,
                                id=self._wid("method"),
                                classes="method-select",
                            )
                            with Container(classes="expand"):
                                yield Input(
                                    value = self.spec.url,
                                    placeholder = "https://api.example.com/resource",
                                    id = self._wid("endpoint"),
                                    classes="endpoint-input",
                            )
                    yield Checkbox(
                        "Verify TLS certificates (recommended)",
                        value=self.spec.verify_tls,
                        id=self._wid("verify"),
                    )
                    yield Static("Headers (JSON object or Key: Value per line)", classes="label")
                    yield TextArea(
                        self.spec.headers,
                        language="json",
                        id=self._wid("headers"),
                        classes="box headers-box",
                    )
                    yield Static("Body (optional)", classes="label")
                    yield TextArea(
                        self.spec.body,
                        language="json",
                        id=self._wid("body"),
                        classes="box body-box",
                    )
                    with Horizontal(classes="actions"):
                        yield SmallButton("Send (Ctrl+S / F5)", id=self._wid("send"), variant="primary")
                        yield SmallButton("Clear", id=self._wid("clear"), variant="ghost")
                        yield SmallButton("Copy", id=self._wid("copy-response"), variant="ghost")
                    yield Static("", id=self._wid("status"), classes="status")
                with Vertical(classes="right-panel"):
                    yield TextArea(
                        "",
                        language="json",
                        id=self._wid("response"),
                        read_only=True,
                        classes="box response-box",
                    )

    def watch_busy(self, busy: bool) -> None:
        self._button("send").disabled = busy
        status = "Sending request..." if busy else ""
        self._set_status(status)

    def focus_endpoint(self) -> None:
        self._input("endpoint").focus()

    def clear_response(self) -> None:
        self._textarea("response").load_text("")

    async def send(self) -> None:
        if self.busy:
            return

        endpoint = self._input("endpoint").value.strip()
        method = (self._select("method").value or "GET").upper()
        raw_headers = self._textarea("headers").text
        body = self._textarea("body").text
        verify_tls = self._checkbox("verify").value

        if not endpoint:
            self._set_response("Please provide a URL.")
            return

        try:
            headers = parse_headers(raw_headers)
        except ValueError as exc:
            self._set_response(str(exc))
            return

        self.busy = True
        self._set_response("Sending request...")
        try:
            response = await perform_http_request(endpoint, method, headers, body, verify_tls)
        except Exception as exc:  # pragma: no cover - network errors are runtime-only
            self._set_response(f"Request failed: {exc!r}")
        else:
            display = format_response(response)
            self._set_response(display)
            if not verify_tls:
                self._set_status("Warning: TLS verification disabled for this request.")
        finally:
            self.busy = False
            self._persist_state()

    async def copy_response(self) -> None:
        await _copy_text_with_fallback(self.app, self._textarea("response").text, self.logger, self._set_status)

    def on_button_pressed(self, event: SmallButton.Pressed) -> None:
        if event.button.id == self._wid("send"):
            asyncio.create_task(self.send())
        elif event.button.id == self._wid("clear"):
            self.clear_response()
        elif event.button.id == self._wid("copy-response"):
            asyncio.create_task(self.copy_response())

    def _textarea(self, name: str) -> TextArea:
        return self.query_one(f"#{self._wid(name)}", TextArea)

    def _input(self, name: str) -> Input:
        return self.query_one(f"#{self._wid(name)}", Input)

    def _select(self, name: str) -> Select:
        return self.query_one(f"#{self._wid(name)}", Select)

    def _checkbox(self, name: str) -> Checkbox:
        return self.query_one(f"#{self._wid(name)}", Checkbox)

    def _button(self, name: str) -> SmallButton:
        return self.query_one(f"#{self._wid(name)}", SmallButton)

    def _set_response(self, message: str) -> None:
        self._textarea("response").load_text(message)

    def _set_status(self, message: str) -> None:
        self.query_one(f"#{self._wid('status')}", Static).update(message)

    def current_spec(self) -> HttpTabSpec:
        return HttpTabSpec(
            id=self.spec.id,
            title=self.spec.title,
            url=self._input("endpoint").value.strip(),
            method=self._select("method").value or "GET",
            body=self._textarea("body").text,
            headers=self._textarea("headers").text,
            verify_tls=self._checkbox("verify").value,
        )

    def _persist_state(self) -> None:
        spec = self.current_spec()
        try:
            self.app.save_state(spec, "http")  # type: ignore[attr-defined]
        except Exception:
            self._set_status("Could not save state.")
