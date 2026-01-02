# ruff: noqa: S101
import asyncio

import pytest

from voyager.models import WebSocketTabSpec
from voyager.ws_tab import WebSocketTab


class StubVal:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.text = value

    def load_text(self, text: str) -> None:
        self.text = text


class DummyTask:
    def __init__(self, coro):
        self.coro = coro
        try:
            coro.close()
        except Exception as exc:  # pragma: no cover - defensive cleanup
            # Log or swallow cleanup issues during test scaffolding.
            DummyTask._last_error = exc

    def cancel(self):
        return None

    def done(self):
        return True


class TestableWebSocketTab(WebSocketTab):
    __test__ = False  # prevent pytest from collecting this helper as a test class

    def __init__(self, spec: WebSocketTabSpec, endpoint: str, headers: str, verify: bool) -> None:
        super().__init__(spec)
        self._endpoint = StubVal(endpoint)
        self._headers = StubVal(headers)
        self._verify = StubVal()
        self._verify.value = verify
        self.logs: list[str] = []
        self.statuses: list[str] = []
        self.saved = False

    def _input(self, name: str):
        return self._endpoint

    def _textarea(self, name: str):
        if name == "headers":
            return self._headers
        if name == "message":
            return StubVal("")
        return StubVal("")

    def _checkbox(self, name: str):
        return self._verify

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _append_log(self, message: str) -> None:
        self.logs.append(message)

    def _persist_state(self) -> None:
        self.saved = True


@pytest.mark.asyncio
async def test_connect_uses_injected_ws_connect(monkeypatch, ws_connect_stub):
    spec = WebSocketTabSpec(id="ws", title="WS", url="wss://echo.example")
    tab = TestableWebSocketTab(spec, endpoint="wss://echo.example", headers='{"Auth": "x"}', verify=True)

    monkeypatch.setattr(asyncio, "create_task", lambda coro: DummyTask(coro))

    await tab.connect(ws_connect=ws_connect_stub)

    assert tab.connected is True
    assert tab.busy is False
    assert tab.saved is True
    assert any("Connected to" in log for log in tab.logs)
    assert ws_connect_stub.calls[0][0] == "wss://echo.example"
    kwargs = ws_connect_stub.calls[0][1]
    headers_payload = kwargs.get("additional_headers") or kwargs.get("extra_headers") or {}
    assert headers_payload.get("Auth") == "x"


@pytest.mark.asyncio
async def test_connect_invalid_endpoint_sets_status(monkeypatch, ws_connect_stub):
    spec = WebSocketTabSpec(id="ws", title="WS", url="ws://bad")
    tab = TestableWebSocketTab(spec, endpoint="invalid://example", headers="{}", verify=True)

    await tab.connect(ws_connect=ws_connect_stub)

    assert tab.connected is False
    assert any("Unsupported URL scheme" in status for status in tab.statuses)
