import asyncio
import json
import ssl
from collections.abc import Awaitable, Callable
from urllib import request
from urllib.parse import urlparse

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - httpx is optional
    httpx = None  # type: ignore

from .models import GraphQLResponse


async def perform_request(
    endpoint: str,
    payload: dict,
    headers: dict[str, str],
    verify_tls: bool,
    requester: Callable[[str, dict, dict[str, str], bool], Awaitable[tuple[int, str]]] | None = None,
    client_factory: Callable[[], Awaitable[object] | object] | None = None,
) -> GraphQLResponse:
    _validate_url(endpoint)
    start = asyncio.get_event_loop().time()
    if requester is not None:
        status, text = await requester(endpoint, payload, headers, verify_tls)
    elif httpx is not None:
        status, text = await _httpx_post(endpoint, payload, headers, verify_tls, client_factory)
    else:
        status, text = await asyncio.to_thread(_urllib_post, endpoint, payload, headers, verify_tls)
    elapsed = (asyncio.get_event_loop().time() - start) * 1000
    return GraphQLResponse(status=status, text=text, duration_ms=elapsed)


async def _httpx_post(
    endpoint: str,
    payload: dict,
    headers: dict[str, str],
    verify_tls: bool,
    client_factory: Callable[[], Awaitable[object]] | None = None,
) -> tuple[int, str]:
    if httpx is None:  # pragma: no cover - guarded by perform_request
        raise RuntimeError("httpx is not installed.")
    if client_factory:
        client = client_factory()
        if asyncio.iscoroutine(client):
            client = await client
        resp = await client.post(endpoint, json=payload, headers=headers)
        return resp.status_code, resp.text
    async with httpx.AsyncClient(timeout=20, verify=verify_tls) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        return resp.status_code, resp.text


def _urllib_post(endpoint: str, payload: dict, headers: dict[str, str], verify_tls: bool) -> tuple[int, str]:
    _validate_url(endpoint)
    body = json.dumps(payload)
    return _urllib_request("POST", endpoint, headers, body, verify_tls)


async def perform_http_request(
    endpoint: str,
    method: str,
    headers: dict[str, str],
    body: str | None,
    verify_tls: bool,
    requester: Callable[[str, str, dict[str, str], str | None, bool], Awaitable[tuple[int, str]]] | None = None,
    client_factory: Callable[[], Awaitable[object] | object] | None = None,
) -> GraphQLResponse:
    normalized_method = method.strip().upper() or "GET"
    _validate_url(endpoint)
    start = asyncio.get_event_loop().time()
    if requester is not None:
        status, text = await requester(endpoint, normalized_method, headers, body, verify_tls)
    elif httpx is not None:
        status, text = await _httpx_request(endpoint, normalized_method, headers, body, verify_tls, client_factory)
    else:
        status, text = await asyncio.to_thread(_urllib_request, normalized_method, endpoint, headers, body, verify_tls)
    elapsed = (asyncio.get_event_loop().time() - start) * 1000
    return GraphQLResponse(status=status, text=text, duration_ms=elapsed)


async def _httpx_request(
    endpoint: str,
    method: str,
    headers: dict[str, str],
    body: str | None,
    verify_tls: bool,
    client_factory: Callable[[], Awaitable[object] | object] | None = None,
) -> tuple[int, str]:
    if httpx is None:  # pragma: no cover - guarded by perform_http_request
        raise RuntimeError("httpx is not installed.")
    if client_factory:
        client = client_factory()
        if asyncio.iscoroutine(client):
            client = await client
        resp = await client.request(
            method=method,
            url=endpoint,
            content=body.encode("utf-8") if body else None,
            headers=headers,
        )
        return resp.status_code, resp.text
    async with httpx.AsyncClient(timeout=20, verify=verify_tls) as client:
        resp = await client.request(
            method=method,
            url=endpoint,
            content=body.encode("utf-8") if body else None,
            headers=headers,
        )
        return resp.status_code, resp.text


def _urllib_request(
    method: str, endpoint: str, headers: dict[str, str], body: str | None, verify_tls: bool
) -> tuple[int, str]:
    _validate_url(endpoint)
    data = body.encode("utf-8") if body else None
    req = request.Request(endpoint, data=data, headers=headers, method=method)  # noqa: S310 - scheme validated above
    context = _ssl_context(verify_tls)
    with request.urlopen(req, timeout=20, context=context) as resp:  # noqa: S310 - scheme validated above
        text = resp.read().decode("utf-8", errors="replace")
        return resp.status, text


def _ssl_context(verify_tls: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _validate_url(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or 'missing'}")
