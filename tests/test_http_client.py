# ruff: noqa: S101
import pytest

from voyager.http_client import (
    _validate_url,
    perform_http_request,
    perform_request,
)


@pytest.mark.asyncio
async def test_perform_request_uses_requester():
    async def requester(endpoint, payload, headers, verify_tls):
        return 200, "ok"

    resp = await perform_request("https://example.com", {}, {}, True, requester=requester)
    assert resp.status == 200
    assert resp.text == "ok"


@pytest.mark.asyncio
async def test_perform_http_request_with_client_factory(fake_client_factory, fake_httpx_client):
    fake_httpx_client.response.status_code = 201
    fake_httpx_client.response.text = "created"

    resp = await perform_http_request(
        "https://api.example.com",
        "post",
        headers={"A": "b"},
        body='{"x":1}',
        verify_tls=True,
        client_factory=fake_client_factory,
    )

    assert resp.status == 201
    assert resp.text == "created"
    assert fake_httpx_client.requests[0][0] == "POST"


@pytest.mark.asyncio
async def test_perform_http_request_with_requester_override():
    async def requester(endpoint, method, headers, body, verify_tls):
        return 418, "teapot"

    resp = await perform_http_request(
        "https://example.com",
        "get",
        headers={},
        body=None,
        verify_tls=False,
        requester=requester,
    )
    assert resp.status == 418
    assert resp.text == "teapot"


def test_validate_url_rejects_invalid_scheme():
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _validate_url("ftp://example.com")
