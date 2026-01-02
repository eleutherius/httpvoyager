import asyncio
import sys
from pathlib import Path

import pytest

# Ensure pytest-asyncio plugin is loaded so @pytest.mark.asyncio works with pytest>=9.
pytest_plugins = ["pytest_asyncio"]


# Ensure project root is on sys.path for local test runs without installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setenv("HTTP_VOYAGER_CONFIG_DIR", str(cfg))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return cfg


@pytest.fixture
def clipboard_spy():
    calls: list[str] = []

    async def copier(text: str) -> None:
        calls.append(text)

    return calls, copier


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "{}") -> None:
        self.status_code = status_code
        self.text = text


class FakeHttpxClient:
    def __init__(self, response: _FakeResponse | None = None) -> None:
        self.requests: list[tuple[str, str, bytes | None, dict[str, str]]] = []
        self.response = response or _FakeResponse()

    async def post(self, endpoint: str, json=None, headers=None):  # noqa: A002 - json matches httpx signature
        self.requests.append(("POST", endpoint, None, headers or {}))
        return self.response

    async def request(self, method: str, url: str, content=None, headers=None):
        body = content if isinstance(content, bytes) else (content.encode("utf-8") if content else None)
        self.requests.append((method, url, body, headers or {}))
        return self.response


@pytest.fixture
def fake_httpx_client():
    return FakeHttpxClient()


@pytest.fixture
def fake_client_factory(fake_httpx_client):
    async def factory():
        return fake_httpx_client

    return factory


class StubWebSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.recv_queue: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        return await self.recv_queue.get()

    async def close(self) -> None:
        return None


class WebSocketConnectStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.socket = StubWebSocket()

    async def __call__(self, endpoint: str, **kwargs):
        self.calls.append((endpoint, kwargs))
        return self.socket

    async def connect(self, endpoint: str, **kwargs):
        return await self.__call__(endpoint, **kwargs)


@pytest.fixture
def ws_connect_stub():
    return WebSocketConnectStub()
