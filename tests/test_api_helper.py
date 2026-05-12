"""Tests for tools._api helpers (httpx wrapper + auth-header injection)."""
import pytest
import respx
import httpx

from tools._api import ApiClient


@pytest.mark.asyncio
@respx.mock
async def test_get_attaches_bearer_token():
    """ApiClient.get() must set Authorization: Bearer <jwt>."""
    route = respx.get("https://api.example/test").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = ApiClient(base_url="https://api.example", jwt="abc.def.ghi")
    async with client:
        resp = await client.get("/test")
    assert resp.status_code == 200
    assert route.calls[0].request.headers["authorization"] == "Bearer abc.def.ghi"


@pytest.mark.asyncio
@respx.mock
async def test_post_serializes_json_body():
    route = respx.post("https://api.example/codebases").mock(
        return_value=httpx.Response(201, json={"id": "cb-1"})
    )
    client = ApiClient(base_url="https://api.example", jwt="t")
    async with client:
        resp = await client.post("/codebases", json={"provider": "github"})
    body = route.calls[0].request.content.decode()
    assert '"provider":"github"' in body or '"provider": "github"' in body
    assert resp.json()["id"] == "cb-1"


@pytest.mark.asyncio
async def test_requires_jwt():
    """Construction with jwt=None raises a clear error."""
    with pytest.raises(RuntimeError, match="DEV_JWT"):
        ApiClient(base_url="https://api.example", jwt=None)
