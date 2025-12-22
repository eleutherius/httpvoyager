import asyncio
import subprocess

from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Static, TabPane, TextArea

from .http_client import perform_request
from .models import GraphQLTabSpec
from .parsing import format_response, parse_headers, parse_json_object
from .ui import SmallButton


class GraphQLTab(TabPane):
    """Single GraphQL playground view."""

    busy: reactive[bool] = reactive(False)

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
                    yield VerticalScroll(
                        TextArea(
                            self.spec.query,
                            language="graphql",
                            id=self._wid("query"),
                            show_line_numbers=True,
                            classes="box query-box",
                        ),
                        classes="query-scroll",
                    )
                    with Horizontal(classes="actions"):
                        yield SmallButton("Send (Ctrl+S / F5)", id=self._wid("send"), variant="primary")
                        yield SmallButton("Clear", id=self._wid("clear"), variant="ghost")
                    yield Static("", id=self._wid("status"), classes="status")
                with Vertical(classes="right-panel"):
                    with Horizontal(classes="response-actions"):
                        yield Static("Response", classes="label")
                        yield SmallButton("Copy", id=self._wid("copy-response"), variant="ghost")
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
        response_text = self._textarea("response").text
        if not response_text.strip():
            self._set_status("Nothing to copy.")
            return
        try:
            await self.app.copy_to_clipboard(response_text)
            self._set_status("Response copied to clipboard.")
            return
        except Exception:
            pass

        # Fallback for environments where Textual clipboard is unavailable.
        try:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(input=response_text.encode("utf-8"), timeout=2)
            if proc.returncode == 0:
                self._set_status("Response copied via pbcopy.")
                return
        except Exception:
            pass

        self._set_status("Copy failed: no clipboard available.")

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
            self.app.save_state(spec)  # type: ignore[attr-defined]
        except Exception:
            self._set_status("Could not save state.")
