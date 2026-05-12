"""Connect madusa-analytics-queries to the Madusa org as a codebase.

Idempotent: looks up existing codebases first, skips POST if found.
After POST, polls the codebase status until it reaches 'active' (max
60s by default) so the caller knows when Generate-KB can use it.

Run:
  python -m tools.connect_madusa
or:
  docker exec uncypher-backend python -m tools.connect_madusa
"""
from __future__ import annotations

import asyncio
import sys
import time
from typing import Optional

from tools._api import ApiClient
from tools._config import Config


REPO_OWNER = "uncypher-stem"
REPO_NAME = "madusa-analytics-queries"
BRANCH = "main"
DISPLAY_NAME = "Madusa Analytics Queries"


def _matches(cb: dict) -> bool:
    return (
        cb.get("provider") == "github"
        and cb.get("repo_owner") == REPO_OWNER
        and cb.get("repo_name") == REPO_NAME
        and cb.get("branch") == BRANCH
        and cb.get("deleted_at") in (None, "")
    )


async def _find_existing(api: ApiClient, org_id: str) -> Optional[dict]:
    resp = await api.get(f"/api/orgs/{org_id}/codebases")
    resp.raise_for_status()
    for cb in resp.json():
        if _matches(cb):
            return cb
    return None


async def _create(api: ApiClient, org_id: str) -> dict:
    resp = await api.post(
        f"/api/orgs/{org_id}/codebases",
        json={
            "provider": "github",
            "repo_owner": REPO_OWNER,
            "repo_name": REPO_NAME,
            "branch": BRANCH,
            "display_name": DISPLAY_NAME,
            "is_public": True,
            "org_id": org_id,
        },
    )
    if resp.status_code == 502:
        raise RuntimeError(
            f"Codebase agent failed to onboard repository: {resp.json().get('detail')}"
        )
    resp.raise_for_status()
    return resp.json()


async def _poll_until_active(
    api: ApiClient,
    org_id: str,
    codebase_id: str,
    poll_interval: float,
    poll_timeout_s: float,
) -> str:
    deadline = time.monotonic() + poll_timeout_s
    last_status = "unknown"
    while time.monotonic() < deadline:
        resp = await api.get(f"/api/orgs/{org_id}/codebases/{codebase_id}")
        resp.raise_for_status()
        last_status = resp.json().get("status", "unknown")
        if last_status in ("active", "error"):
            return last_status
        await asyncio.sleep(poll_interval)
    raise RuntimeError(
        f"Codebase {codebase_id} did not reach 'active' within "
        f"{poll_timeout_s}s (last status: {last_status})"
    )


async def connect(
    cfg: Config,
    poll_interval: float = 2.0,
    poll_timeout_s: float = 60.0,
) -> dict:
    """Return {codebase_id, repo_key, created, final_status}."""
    async with ApiClient(cfg.backend_url, cfg.jwt) as api:
        existing = await _find_existing(api, cfg.org_id)
        if existing:
            return {
                "codebase_id": existing["id"],
                "repo_key": existing["repo_key"],
                "created": False,
                "final_status": existing.get("status", "unknown"),
            }
        created = await _create(api, cfg.org_id)
        final_status = created.get("status", "pending")
        if final_status not in ("active", "error"):
            final_status = await _poll_until_active(
                api, cfg.org_id, created["id"], poll_interval, poll_timeout_s,
            )
        return {
            "codebase_id": created["id"],
            "repo_key": created["repo_key"],
            "created": True,
            "final_status": final_status,
        }


async def _main() -> int:
    cfg = Config.from_env()
    result = await connect(cfg)
    print(
        f"codebase_id={result['codebase_id']} "
        f"repo_key={result['repo_key']} "
        f"created={result['created']} "
        f"status={result['final_status']}"
    )
    return 0 if result["final_status"] == "active" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
