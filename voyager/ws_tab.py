from __future__ import annotations

import asyncio
import inspect
import logging
import ssl
from typing import Any
from urllib.parse import urlparse

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Static, TabPane, TextArea

from .models import WebSocketTabSpec
from .parsing import parse_headers
from .ui_components import SmallButton

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    websockets = None  # type: ignore


def _ssl_context(verify_tls: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _validate_ws_url(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or 'missing'}")
    if not parsed.netloc:
        raise ValueError("Missing host in URL.")


class WebSocketTab(TabPane):
    """WebSocket client tab."""

    busy: reactive[bool] = reactive(False)
    connected: reactive[bool] = reactive(False)
    logger = logging.getLogger(__name__)

    def __init__(self, spec: WebSocketTabSpec) -> None:
        super().__init__(title="WebSocket", id="ws")
        self.spec = spec
        self.connection = None
        self._recv_task: asyncio.Task[Any] | None = None
        self.ws_connect = None

    def _wid(self, name: str) -> str:
        return f"{self.id}-{name}"

    def compose(self):
        with Container(classes="layout"):
            with Horizontal(classes="columns"):
                with Vertical(classes="left-panel"):
                    yield Static("Endpoint (ws/wss)", classes="label")
                    yield Input(
                        value=self.spec.url,
                        placeholder="wss://echo.websocket.events",
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
                    yield Static("Message (text)", classes="label")
                    yield TextArea(
                        self.spec.message,
                        language="json",
                        id=self._wid("message"),
                        classes="box body-box",
                    )
                    with Horizontal(classes="actions"):
                        yield SmallButton("Connect", id=self._wid("connect"), variant="primary")
                        yield SmallButton("Disconnect", id=self._wid("disconnect"), variant="ghost")
                        yield SmallButton("Send", id=self._wid("send"), variant="ghost")
                        yield SmallButton("Clear", id=self._wid("clear"), variant="ghost")
                        yield SmallButton("Copy", id=self._wid("copy-log"), variant="ghost")
                    yield Static("", id=self._wid("status"), classes="status")
                with Vertical(classes="right-panel"):
                    yield TextArea(
                        "",
                        language="markdown",
                        id=self._wid("log"),
                        read_only=True,
                        classes="box response-box response-section",
                    )

    def watch_busy(self, busy: bool) -> None:
        for name in ("connect", "send", "disconnect"):
            try:
                self._button(name).disabled = busy
            except Exception:
                continue
        self._set_status("Working..." if busy else "")

    def watch_connected(self, connected: bool) -> None:
        try:
            self._button("connect").disabled = connected or self.busy
            self._button("disconnect").disabled = not connected or self.busy
            self._button("send").disabled = not connected or self.busy
        except Exception:
            return
        if connected:
            self._set_status("Connected.")
        else:
            self._set_status("Disconnected.")

    async def on_button_pressed(self, event: SmallButton.Pressed) -> None:
        if event.button.id == self._wid("connect"):
            asyncio.create_task(self.connect())
        elif event.button.id == self._wid("disconnect"):
            asyncio.create_task(self.disconnect())
        elif event.button.id == self._wid("send"):
            asyncio.create_task(self.send())
        elif event.button.id == self._wid("clear"):
            self._clear_log()
        elif event.button.id == self._wid("copy-log"):
            asyncio.create_task(self.copy_log())

    async def connect(self, ws_connect: Callable[..., Any] | None = None) -> None:
        if self.busy:
            return
        endpoint = self._input("endpoint").value.strip()
        raw_headers = self._textarea("headers").text
        verify_tls = self._checkbox("verify").value

        if not endpoint:
            self._set_status("Please provide an endpoint.")
            return

        try:
            _validate_ws_url(endpoint)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        try:
            headers = parse_headers(raw_headers)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        connect_callable = ws_connect or self.ws_connect or websockets
        if connect_callable is None:
            self._set_status("Install the 'websockets' package to use this tab.")
            return

        self.busy = True
        await self.disconnect()
        self._set_status(f"Connecting to {endpoint} ...")
        try:
            connector = getattr(connect_callable, "connect", None)
            if connector:
                self.connection = await connector(endpoint, **_connect_kwargs(headers, verify_tls))  # type: ignore[arg-type]
            else:
                self.connection = await connect_callable(  # type: ignore[operator,union-attr]
                    endpoint,
                    **_connect_kwargs(headers, verify_tls),
                )
        except Exception as exc:
            self.logger.debug("WebSocket connection failed: %s", exc)
            self._append_log(f"Connect failed: {exc}")
            self._set_status(f"Connect failed: {exc}")
            self.busy = False
            return

        self.connected = True
        self.busy = False
        self._append_log(f"Connected to {endpoint}")
        self._persist_state()
        self._recv_task = asyncio.create_task(self._recv_loop(self.connection))

    async def disconnect(self) -> None:
        self.connected = False
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self.logger.debug("Receiver task ended with error: %s", exc)
        self._recv_task = None

        if self.connection:
            try:
                await self.connection.close()  # type: ignore[union-attr]
                self._append_log("Disconnected.")
            except Exception as exc:  # pragma: no cover - network dependent
                self.logger.debug("WebSocket close failed: %s", exc)
            self.connection = None

    async def send(self) -> None:
        if self.busy:
            return
        message = self._textarea("message").text
        if not self.connection or not self.connected:
            await self.connect()
        if not self.connection or not self.connected:
            return

        try:
            await self.connection.send(message)  # type: ignore[union-attr]
        except Exception as exc:  # pragma: no cover - network dependent
            self._append_log(f"Send failed: {exc}")
            self.logger.debug("Send failed: %s", exc)
            self.connected = False
            self._set_status("Send failed.")
            return
        self._append_log(f"Sent: {message.strip() or '<empty>'}")
        self._set_status("Message sent.")
        self._persist_state()

    async def copy_log(self) -> None:
        text = self._textarea("log").text
        if not text.strip():
            self._set_status("Nothing to copy.")
            return
        try:
            await self.app.copy_to_clipboard(text)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.logger.debug("Copy to clipboard failed: %s", exc)
            self._set_status("Copy failed.")
            return
        self._set_status("Log copied.")

    def _append_log(self, message: str) -> None:
        current = self._textarea("log").text
        new_text = (current + "\n" if current else "") + message
        self._textarea("log").load_text(new_text)

    def _clear_log(self) -> None:
        self._textarea("log").load_text("")
        self._set_status("Cleared.")

    def focus_endpoint(self) -> None:
        self._input("endpoint").focus()

    async def copy_response(self) -> None:
        await self.copy_log()

    def _textarea(self, name: str) -> TextArea:
        return self.query_one(f"#{self._wid(name)}", TextArea)

    def _input(self, name: str) -> Input:
        return self.query_one(f"#{self._wid(name)}", Input)

    def _checkbox(self, name: str) -> Checkbox:
        return self.query_one(f"#{self._wid(name)}", Checkbox)

    def _button(self, name: str) -> SmallButton:
        return self.query_one(f"#{self._wid(name)}", SmallButton)

    def _set_status(self, message: str) -> None:
        self.query_one(f"#{self._wid('status')}", Static).update(message)

    async def _recv_loop(self, connection) -> None:
        try:
            while self.connected:
                try:
                    message = await connection.recv()
                except asyncio.CancelledError:
                    break
                except Exception as exc:  # pragma: no cover - network dependent
                    self._append_log(f"Receive failed: {exc}")
                    self.logger.debug("Receive failed: %s", exc)
                    self.connected = False
                    break
                else:
                    self._append_log(f"Received: {message}")
        finally:
            self.connected = False
            self.connection = None

    async def on_unmount(self) -> None:  # type: ignore[override]
        await self.disconnect()

    def current_spec(self) -> WebSocketTabSpec:
        return WebSocketTabSpec(
            id=self.spec.id,
            title=self.spec.title,
            url=self._input("endpoint").value.strip(),
            message=self._textarea("message").text,
            headers=self._textarea("headers").text,
            verify_tls=self._checkbox("verify").value,
        )

    def _persist_state(self) -> None:
        spec = self.current_spec()
        try:
            self.app.save_state(spec, "websocket")  # type: ignore[attr-defined]
        except Exception:
            self._set_status("Could not save state.")


def _connect_kwargs(headers: dict[str, str], verify_tls: bool) -> dict[str, Any]:
    """Build connect kwargs compatible with websockets version."""
    kwargs: dict[str, Any] = {"ssl": _ssl_context(verify_tls)}
    params = set()
    try:
        params = set(inspect.signature(websockets.connect).parameters)
    except Exception:
        params = set()
    if "ping_interval" in params:
        kwargs["ping_interval"] = 20
    if "additional_headers" in params:
        kwargs["additional_headers"] = headers
    elif "extra_headers" in params:
        kwargs["extra_headers"] = headers
    return kwargs
