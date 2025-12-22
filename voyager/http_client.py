import asyncio
import json
import ssl
from typing import Dict, Tuple
from urllib import request

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - httpx is optional
    httpx = None  # type: ignore

from .models import GraphQLResponse


async def perform_request(
    endpoint: str, payload: Dict, headers: Dict[str, str], verify_tls: bool
) -> GraphQLResponse:
    start = asyncio.get_event_loop().time()
    if httpx is not None:
        status, text = await _httpx_post(endpoint, payload, headers, verify_tls)
    else:
        status, text = await asyncio.to_thread(_urllib_post, endpoint, payload, headers, verify_tls)
    elapsed = (asyncio.get_event_loop().time() - start) * 1000
    return GraphQLResponse(status=status, text=text, duration_ms=elapsed)


async def _httpx_post(
    endpoint: str, payload: Dict, headers: Dict[str, str], verify_tls: bool
) -> Tuple[int, str]:
    assert httpx is not None
    async with httpx.AsyncClient(timeout=20, verify=verify_tls) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        return resp.status_code, resp.text


def _urllib_post(
    endpoint: str, payload: Dict, headers: Dict[str, str], verify_tls: bool
) -> Tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint, data=data, headers=headers, method="POST")
    context = None if verify_tls else ssl._create_unverified_context()
    with request.urlopen(req, timeout=20, context=context) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        return resp.status, text
