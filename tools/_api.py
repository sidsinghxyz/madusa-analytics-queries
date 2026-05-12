"""Thin async httpx wrapper used by connect/verify tools.

Centralises base URL, JWT injection, and default timeouts. Not a generic SDK —
just enough for the three tools to share."""
from __future__ import annotations

from typing import Optional, Any
import httpx


class ApiClient:
    def __init__(
        self,
        base_url: str,
        jwt: Optional[str],
        timeout: float = 15.0,
    ) -> None:
        if not jwt:
            raise RuntimeError(
                "ApiClient requires a JWT. Set DEV_JWT in the environment "
                "(grab it from your browser session on the dev frontend)."
            )
        self._base_url = base_url.rstrip("/")
        self._jwt = jwt
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ApiClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._jwt}"},
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        assert self._client is not None, "use as `async with ApiClient(...)`"
        return await self._client.get(path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        assert self._client is not None, "use as `async with ApiClient(...)`"
        return await self._client.post(path, **kwargs)
