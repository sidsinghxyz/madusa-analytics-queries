"""Tests for connect_madusa.py.

Covers:
- Happy path: POST creates codebase, returns id + repo_key.
- Idempotent path: GET finds existing matching codebase, skips POST.
- Polling: codebase status flips from `pending` → `active` within budget.
- Failure: POST returns 502, tool raises with clear message.
"""
import json
import pytest
import respx
import httpx

from tools._config import Config
from tools.connect_madusa import connect


CFG = Config(
    backend_url="https://api.example",
    jwt="t",
    kb_pg_dsn="",
    backend_pg_dsn="",
    org_id="org-1",
    project_id="proj-1",
    database_id="db-1",
    github_repo_url="https://github.com/sidsinghxyz/madusa-analytics-queries",
)


@pytest.mark.asyncio
@respx.mock
async def test_connect_happy_path():
    """No existing codebase → POST creates one, returns id + repo_key."""
    respx.get("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.post("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "cb-xyz",
                "org_id": "org-1",
                "provider": "github",
                "repo_owner": "sidsinghxyz",
                "repo_name": "madusa-analytics-queries",
                "branch": "main",
                "display_name": "Madusa Analytics Queries",
                "repo_key": "madusa-analytics-queries",
                "status": "active",
                "is_public": True,
                "created_at": "2026-05-12T00:00:00Z",
                "updated_at": "2026-05-12T00:00:00Z",
            },
        )
    )
    result = await connect(CFG, poll_interval=0.01)
    assert result["codebase_id"] == "cb-xyz"
    assert result["repo_key"] == "madusa-analytics-queries"
    assert result["created"] is True


@pytest.mark.asyncio
@respx.mock
async def test_connect_idempotent_when_existing():
    """Existing codebase matching repo_owner+repo_name → skip POST."""
    existing = {
        "id": "cb-existing",
        "org_id": "org-1",
        "provider": "github",
        "repo_owner": "sidsinghxyz",
        "repo_name": "madusa-analytics-queries",
        "branch": "main",
        "display_name": "Madusa Analytics Queries",
        "repo_key": "madusa-analytics-queries",
        "status": "active",
        "is_public": True,
        "created_at": "2026-05-10T00:00:00Z",
        "updated_at": "2026-05-10T00:00:00Z",
    }
    respx.get("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(200, json=[existing])
    )
    post = respx.post("https://api.example/api/orgs/org-1/codebases")
    result = await connect(CFG, poll_interval=0.01)
    assert result["codebase_id"] == "cb-existing"
    assert result["created"] is False
    assert post.called is False


@pytest.mark.asyncio
@respx.mock
async def test_connect_polls_until_active():
    """Created codebase returns status=pending; poll until active."""
    respx.get("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(200, json=[])
    )
    base_cb = {
        "id": "cb-1", "org_id": "org-1", "provider": "github",
        "repo_owner": "sidsinghxyz", "repo_name": "madusa-analytics-queries",
        "branch": "main", "display_name": "Madusa Analytics Queries",
        "repo_key": "madusa-analytics-queries", "is_public": True,
        "created_at": "2026-05-12T00:00:00Z",
        "updated_at": "2026-05-12T00:00:00Z",
    }
    respx.post("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(201, json={**base_cb, "status": "pending"})
    )
    # First two polls return pending, third returns active.
    poll_responses = [
        httpx.Response(200, json={**base_cb, "status": "pending"}),
        httpx.Response(200, json={**base_cb, "status": "pending"}),
        httpx.Response(200, json={**base_cb, "status": "active"}),
    ]
    respx.get("https://api.example/api/orgs/org-1/codebases/cb-1").mock(
        side_effect=poll_responses
    )
    result = await connect(CFG, poll_interval=0.01, poll_timeout_s=2.0)
    assert result["codebase_id"] == "cb-1"
    assert result["final_status"] == "active"


@pytest.mark.asyncio
@respx.mock
async def test_connect_raises_on_502():
    """Backend returns 502 → tool raises with a clear error message."""
    respx.get("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.post("https://api.example/api/orgs/org-1/codebases").mock(
        return_value=httpx.Response(
            502,
            json={"detail": "Codebase agent failed to onboard repository: timeout"},
        )
    )
    with pytest.raises(RuntimeError, match="agent failed"):
        await connect(CFG, poll_interval=0.01)
