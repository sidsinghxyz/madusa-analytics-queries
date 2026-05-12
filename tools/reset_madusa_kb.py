"""Soft-reset Madusa's KB rows + delete its KBBulkRun/Proposal/Config rows.

Reversible. After --apply, prints the undo SQL the operator can paste back
within ~24h.

Run:
  python -m tools.reset_madusa_kb              # dry-run (prints counts)
  python -m tools.reset_madusa_kb --apply      # execute
  python -m tools.reset_madusa_kb --apply --force   # bypass in-flight run check
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

import asyncpg

from tools._config import Config
from tools._db import pg


_KB_UPDATES = {
    "node_descriptions": """
        UPDATE node_descriptions SET is_deleted=true, deleted_at=now(), updated_at=now()
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND is_deleted=false
    """,
    "node_columns": """
        UPDATE node_columns SET soft_deleted=true, deleted_at=now(), updated_at=now()
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND soft_deleted=false
    """,
    "nodes_connection": """
        UPDATE nodes_connection SET soft_deleted=true, deleted_at=now(), updated_at=now()
         WHERE (from_node_id IN (SELECT id FROM nodes WHERE org_id=$1)
             OR to_node_id   IN (SELECT id FROM nodes WHERE org_id=$1))
           AND soft_deleted=false
    """,
    "nodes": """
        UPDATE nodes SET soft_deleted=true, deleted_at=now(), updated_at=now()
         WHERE org_id=$1 AND soft_deleted=false
    """,
}

_KB_COUNT_LIVE = {
    "node_descriptions": "SELECT COUNT(*) FROM node_descriptions WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1) AND is_deleted=false",
    "node_columns":      "SELECT COUNT(*) FROM node_columns      WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1) AND soft_deleted=false",
    "nodes_connection":  "SELECT COUNT(*) FROM nodes_connection  WHERE (from_node_id IN (SELECT id FROM nodes WHERE org_id=$1) OR to_node_id IN (SELECT id FROM nodes WHERE org_id=$1)) AND soft_deleted=false",
    "nodes":             "SELECT COUNT(*) FROM nodes             WHERE org_id=$1 AND soft_deleted=false",
}

_BACKEND_DELETES = {
    "kb_bulk_proposals": "DELETE FROM kb_bulk_proposals WHERE run_id IN (SELECT id FROM kb_bulk_runs WHERE org_id=$1)",
    "kb_bulk_runs":      "DELETE FROM kb_bulk_runs      WHERE org_id=$1",
    "kb_bulk_configs":   "DELETE FROM kb_bulk_configs   WHERE org_id=$1",
}

_BACKEND_COUNTS = {
    "kb_bulk_proposals": "SELECT COUNT(*) FROM kb_bulk_proposals WHERE run_id IN (SELECT id FROM kb_bulk_runs WHERE org_id=$1)",
    "kb_bulk_runs":      "SELECT COUNT(*) FROM kb_bulk_runs      WHERE org_id=$1",
    "kb_bulk_configs":   "SELECT COUNT(*) FROM kb_bulk_configs   WHERE org_id=$1",
}


async def plan_reset(kb_conn, backend_conn, org_id: str) -> dict:
    kb = {}
    for name, sql in _KB_COUNT_LIVE.items():
        kb[name] = await kb_conn.fetchval(sql, org_id)
    backend = {}
    for name, sql in _BACKEND_COUNTS.items():
        backend[name] = await backend_conn.fetchval(sql, org_id)
    return {"kb": kb, "backend": backend}


async def execute_reset(kb_conn, backend_conn, org_id: str) -> str:
    """Run all 4 KB UPDATEs (in one txn) + 3 backend DELETEs (in one txn).

    Returns the reset timestamp (ISO 8601, UTC) for the undo line.
    """
    ts = datetime.now(timezone.utc).isoformat()
    async with kb_conn.transaction():
        for sql in _KB_UPDATES.values():
            await kb_conn.execute(sql, org_id)
    async with backend_conn.transaction():
        for sql in _BACKEND_DELETES.values():
            await backend_conn.execute(sql, org_id)
    return ts


async def in_flight_run_exists(backend_conn, org_id: str) -> bool:
    return await backend_conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM kb_bulk_runs "
        "WHERE org_id=$1 AND status IN ('parsing','running'))",
        org_id,
    )


def _print_undo(ts: str, org_id: str) -> None:
    print()
    print("# Undo (valid until next reset overwrites updated_at):")
    print(
        f"# UPDATE nodes               SET soft_deleted=false WHERE org_id='{org_id}' AND updated_at >= '{ts}';"
    )
    print(
        f"# UPDATE node_columns        SET soft_deleted=false WHERE node_id IN (SELECT id FROM nodes WHERE org_id='{org_id}') AND updated_at >= '{ts}';"
    )
    print(
        f"# UPDATE node_descriptions   SET is_deleted=false   WHERE node_id IN (SELECT id FROM nodes WHERE org_id='{org_id}') AND updated_at >= '{ts}';"
    )
    print(
        f"# UPDATE nodes_connection    SET soft_deleted=false WHERE (from_node_id IN (SELECT id FROM nodes WHERE org_id='{org_id}') OR to_node_id IN (SELECT id FROM nodes WHERE org_id='{org_id}')) AND updated_at >= '{ts}';"
    )


def _format_plan(plan: dict) -> str:
    lines = ["Planned reset (dry-run):", "  KB Postgres:"]
    for k, v in plan["kb"].items():
        lines.append(f"    {k:24s} {v:>6d} rows")
    lines.append("  Backend Postgres:")
    for k, v in plan["backend"].items():
        lines.append(f"    {k:24s} {v:>6d} rows")
    return "\n".join(lines)


async def _main(apply_changes: bool, force: bool) -> int:
    cfg = Config.from_env()
    async with pg(cfg.kb_pg_dsn) as kb_conn, pg(cfg.backend_pg_dsn) as backend_conn:
        if apply_changes and not force:
            if await in_flight_run_exists(backend_conn, cfg.org_id):
                print(
                    "ERROR: an in-flight kb_bulk_runs row exists for org "
                    f"{cfg.org_id}. Use --force to wipe anyway.",
                    file=sys.stderr,
                )
                return 2
        plan = await plan_reset(kb_conn, backend_conn, cfg.org_id)
        print(_format_plan(plan))
        if not apply_changes:
            print("\n(dry-run; re-run with --apply to execute)")
            return 0
        ts = await execute_reset(kb_conn, backend_conn, cfg.org_id)
        print("\nApplied.")
        _print_undo(ts, cfg.org_id)
        return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="actually run the reset")
    p.add_argument("--force", action="store_true", help="bypass in-flight run check")
    args = p.parse_args()
    sys.exit(asyncio.run(_main(args.apply, args.force)))
