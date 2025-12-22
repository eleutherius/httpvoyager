import asyncio
import json
import ssl
from urllib import request
from urllib.parse import urlparse

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - httpx is optional
    httpx = None  # type: ignore

from .models import GraphQLResponse


async def perform_request(endpoint: str, payload: dict, headers: dict[str, str], verify_tls: bool) -> GraphQLResponse:
    start = asyncio.get_event_loop().time()
    if httpx is not None:
        status, text = await _httpx_post(endpoint, payload, headers, verify_tls)
    else:
        status, text = await asyncio.to_thread(_urllib_post, endpoint, payload, headers, verify_tls)
    elapsed = (asyncio.get_event_loop().time() - start) * 1000
    return GraphQLResponse(status=status, text=text, duration_ms=elapsed)


async def _httpx_post(endpoint: str, payload: dict, headers: dict[str, str], verify_tls: bool) -> tuple[int, str]:
    if httpx is None:  # pragma: no cover - guarded by perform_request
        raise RuntimeError("httpx is not installed.")
    async with httpx.AsyncClient(timeout=20, verify=verify_tls) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        return resp.status_code, resp.text


def _urllib_post(endpoint: str, payload: dict, headers: dict[str, str], verify_tls: bool) -> tuple[int, str]:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or 'missing'}")

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint, data=data, headers=headers, method="POST")  # noqa: S310 - scheme validated above
    context = ssl.create_default_context()
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with request.urlopen(req, timeout=20, context=context) as resp:  # noqa: S310 - scheme validated above
        text = resp.read().decode("utf-8", errors="replace")
        return resp.status, text
