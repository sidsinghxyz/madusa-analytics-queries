"""Audit Phase 3 hydration coverage after a Generate-KB run.

Computes a deterministic report against the KB + backend Postgres and the
backend container logs, then prints a tick/cross table. Exits 0 if all
checks pass, non-zero otherwise.

Run:
  python -m tools.verify_hydration --run-id <KBBulkRun.id>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from typing import Any

from tools._config import Config
from tools._db import pg


# Minimum counts for a pass — see spec §"Coverage report".
_THRESHOLDS = {
    "live_db_descriptions":     1,
    "date_filter_columns":      1,
    "filter_condition_columns": 1,
    "enum_value_columns":       1,
    "unattempted_descriptions": 1,
}


_KB_QUERIES = {
    # 1) live_db source descriptions — Stage 1 working.
    "live_db_descriptions": """
        SELECT COUNT(*) FROM node_descriptions
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND is_deleted=false
           AND source='live_db'
    """,
    # 2) date_filter role — Stage 2 date predicate detection.
    "date_filter_columns": """
        SELECT COUNT(*) FROM node_columns
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND soft_deleted=false
           AND query_role='date_filter'
    """,
    # 3) filter_condition role — Stage 2 WHERE / JOIN-key classification.
    "filter_condition_columns": """
        SELECT COUNT(*) FROM node_columns
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND soft_deleted=false
           AND query_role='filter_condition'
    """,
    # 4) Enum-extracted values — Stage 2 low-card IN extraction.
    "enum_value_columns": """
        SELECT COUNT(DISTINCT cv.node_column_id) FROM column_values cv
          JOIN node_columns nc ON nc.id = cv.node_column_id
         WHERE nc.node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND cv.soft_deleted=false
           AND nc.soft_deleted=false
    """,
    # 5) Unattempted descriptions — Stage 3 gap-fill.
    "unattempted_descriptions": """
        SELECT COUNT(*) FROM node_descriptions
         WHERE node_id IN (SELECT id FROM nodes WHERE org_id=$1)
           AND is_deleted=false
           AND status='unattempted'
    """,
}


_BACKEND_RUN = """
SELECT parsing_stats
  FROM kb_bulk_runs
 WHERE id=$1 AND org_id=$2
"""


async def compute_report(
    *,
    kb_conn,
    backend_conn,
    run_id: str,
    org_id: str,
    log_text: str,
    kb_bulk_v2_enabled: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for key, sql in _KB_QUERIES.items():
        report[key] = await kb_conn.fetchval(sql, org_id) or 0
    row = await backend_conn.fetchrow(_BACKEND_RUN, run_id, org_id)
    parsing_stats = (row or {}).get("parsing_stats") or {}
    if isinstance(parsing_stats, str):
        try:
            parsing_stats = json.loads(parsing_stats)
        except (ValueError, TypeError):
            parsing_stats = {}
    phantoms = parsing_stats.get("phantom_tables") or []
    report["phantom_table_flagged"] = bool(phantoms)
    report["confidence_dist_log_present"] = "kb_bulk.agent_descriptions" in log_text
    report["kb_bulk_v2_enabled"] = bool(kb_bulk_v2_enabled)
    return report


def report_passes(report: dict[str, Any]) -> bool:
    if not report.get("kb_bulk_v2_enabled"):
        return False
    if not report.get("phantom_table_flagged"):
        return False
    if not report.get("confidence_dist_log_present"):
        return False
    for k, threshold in _THRESHOLDS.items():
        if int(report.get(k, 0)) < threshold:
            return False
    return True


_LABELS = {
    "live_db_descriptions":     "live_db source descriptions",
    "date_filter_columns":      "date_filter columns",
    "filter_condition_columns": "filter_condition columns",
    "enum_value_columns":       "enum-extracted value columns",
    "unattempted_descriptions": "unattempted descriptions",
}


def format_report(report: dict[str, Any]) -> str:
    out = []
    for key, label in _LABELS.items():
        value = int(report.get(key, 0))
        threshold = _THRESHOLDS[key]
        mark = "✓" if value >= threshold else "✗"
        suffix = "" if value >= threshold else f"  ← below {threshold}"
        out.append(f"{mark} {label:32s} {value:>6d}   (≥{threshold}){suffix}")
    out.append(
        f"{'✓' if report.get('phantom_table_flagged') else '✗'} "
        f"phantom-table flagged:           "
        f"{str(report.get('phantom_table_flagged')).lower()}"
    )
    out.append(
        f"{'✓' if report.get('confidence_dist_log_present') else '✗'} "
        f"confidence-dist log present:     "
        f"{str(report.get('confidence_dist_log_present')).lower()}"
    )
    out.append(
        f"{'✓' if report.get('kb_bulk_v2_enabled') else '✗'} "
        f"KB_BULK_V2_ENABLED:              "
        f"{str(report.get('kb_bulk_v2_enabled')).lower()}"
    )
    return "\n".join(out)


def _read_log_text(log_file: str | None, run_id: str) -> str:
    """Load log text the operator captured outside this process.

    Two ways to feed logs in:
      --log-file <path>   read the file (use '-' for stdin)
      (nothing)           best-effort: try `docker compose` on host. Fails
                          silently inside a container that has no docker socket.

    Returns whichever lines mention the run_id or the telemetry tag.
    """
    if log_file == "-":
        raw = sys.stdin.read()
    elif log_file:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    else:
        try:
            out = subprocess.check_output(
                [
                    "docker", "compose",
                    "-f", "/home/cloberxyz/projects/uncypher-platform/docker-compose.prod.yml",
                    "logs", "--tail", "2000", "backend",
                ],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            raw = out
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raw = ""
    return "\n".join(
        l for l in raw.splitlines()
        if run_id in l or "kb_bulk.agent_descriptions" in l
    )


def _probe_flag() -> bool:
    """Read KB_BULK_V2_ENABLED from env (best-effort)."""
    raw = os.environ.get("KB_BULK_V2_ENABLED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


async def _main(run_id: str, log_file: str | None) -> int:
    cfg = Config.from_env()
    log_text = _read_log_text(log_file, run_id)
    flag = _probe_flag()
    async with pg(cfg.kb_pg_dsn) as kb_conn, pg(cfg.backend_pg_dsn) as backend_conn:
        report = await compute_report(
            kb_conn=kb_conn,
            backend_conn=backend_conn,
            run_id=run_id,
            org_id=cfg.org_id,
            log_text=log_text,
            kb_bulk_v2_enabled=flag,
        )
    print(format_report(report))
    print()
    print(json.dumps(report, indent=2))
    return 0 if report_passes(report) else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument(
        "--log-file",
        default=None,
        help="Path to backend log dump for the run; use '-' to read stdin. "
             "Omit to let verify shell out to `docker compose logs` (only "
             "works when run on the SSH host, not inside a container).",
    )
    args = p.parse_args()
    sys.exit(asyncio.run(_main(args.run_id, args.log_file)))
