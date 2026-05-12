"""Shared config for tools/. All values env-overridable; dev defaults baked in.

The defaults target the Madusa org on dev. CI / other envs override via env vars.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


# Madusa constants — confirmed in docs/plans/2026-05-11-kb-audit-phase-3-waterfall-agent.md
MADUSA_ORG_ID = "acd9ef9f-170d-4c57-ae7c-0c2ca12628a4"
MADUSA_PROJECT_ID = "ca184e50-6040-44bb-9f05-e1833217cb09"
MADUSA_DATABASE_ID = "ee7f3c28-ffcb-4c90-a765-8358513d7891"


@dataclass(frozen=True)
class Config:
    backend_url: str
    jwt: Optional[str]
    kb_pg_dsn: str
    backend_pg_dsn: str
    org_id: str
    project_id: str
    database_id: str
    github_repo_url: str = "https://github.com/uncypher-stem/madusa-analytics-queries"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            backend_url=os.environ.get(
                "DEV_BACKEND_URL", "https://api.uncypher.sidsingh.xyz"
            ),
            jwt=os.environ.get("DEV_JWT"),
            kb_pg_dsn=os.environ.get(
                "KB_PG_DSN",
                # In-container default; from host you must set this explicitly.
                "postgresql://kb:kb@uncypher-kb-postgres:5432/kb",
            ),
            backend_pg_dsn=os.environ.get(
                "BACKEND_PG_DSN",
                "postgresql://postgres:postgres@uncypher-postgres:5432/data_decipher",
            ),
            org_id=os.environ.get("MADUSA_ORG_ID", MADUSA_ORG_ID),
            project_id=os.environ.get("MADUSA_PROJECT_ID", MADUSA_PROJECT_ID),
            database_id=os.environ.get("MADUSA_DATABASE_ID", MADUSA_DATABASE_ID),
            github_repo_url=os.environ.get(
                "MADUSA_QUERIES_REPO",
                "https://github.com/uncypher-stem/madusa-analytics-queries",
            ),
        )
