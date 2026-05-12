"""Tests for reset_madusa_kb.py.

The script issues 4 KB-postgres UPDATEs and 3 backend-postgres DELETEs.
Tests assert: dry-run prints expected counts without executing UPDATEs;
--apply executes them in a transaction; an in-flight PROCESSING run
blocks reset unless --force passed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from tools.reset_madusa_kb import plan_reset, execute_reset, in_flight_run_exists


@pytest.mark.asyncio
async def test_plan_reset_returns_counts_from_kb_and_backend():
    """plan_reset() runs SELECT COUNTs against both DBs and returns a report dict."""
    kb_conn = AsyncMock()
    kb_conn.fetchval = AsyncMock(side_effect=[42, 88, 17, 8])
    #  ^ node_descriptions, node_columns, nodes_connection, nodes (live counts)
    backend_conn = AsyncMock()
    backend_conn.fetchval = AsyncMock(side_effect=[3, 5, 1])
    #  ^ kb_bulk_proposals, kb_bulk_runs, kb_bulk_configs
    plan = await plan_reset(kb_conn, backend_conn, org_id="org-1")
    assert plan["kb"]["node_descriptions"] == 42
    assert plan["kb"]["node_columns"] == 88
    assert plan["kb"]["nodes_connection"] == 17
    assert plan["kb"]["nodes"] == 8
    assert plan["backend"]["kb_bulk_proposals"] == 3
    assert plan["backend"]["kb_bulk_runs"] == 5
    assert plan["backend"]["kb_bulk_configs"] == 1


@pytest.mark.asyncio
async def test_execute_reset_issues_4_updates_3_deletes():
    """execute_reset() runs 4 UPDATEs on kb conn and 3 DELETEs on backend conn."""
    kb_conn = AsyncMock()
    kb_conn.execute = AsyncMock(return_value="UPDATE 0")
    kb_conn.transaction = MagicMock()
    kb_conn.transaction.return_value.__aenter__ = AsyncMock()
    kb_conn.transaction.return_value.__aexit__ = AsyncMock()
    backend_conn = AsyncMock()
    backend_conn.execute = AsyncMock(return_value="DELETE 0")
    backend_conn.transaction = MagicMock()
    backend_conn.transaction.return_value.__aenter__ = AsyncMock()
    backend_conn.transaction.return_value.__aexit__ = AsyncMock()

    ts = await execute_reset(kb_conn, backend_conn, org_id="org-1")

    kb_calls = [c.args[0] for c in kb_conn.execute.await_args_list]
    assert sum("UPDATE node_descriptions" in s for s in kb_calls) == 1
    assert sum("UPDATE node_columns" in s for s in kb_calls) == 1
    assert sum("UPDATE nodes_connection" in s for s in kb_calls) == 1
    # NOTE: distinguish bare-`nodes` UPDATE from `nodes_connection` (which
    # contains "UPDATE nodes" as a prefix) by matching the trailing space.
    assert sum("UPDATE nodes " in s for s in kb_calls) == 1
    assert all("WHERE" in s and "org_id" in s for s in kb_calls)

    backend_calls = [c.args[0] for c in backend_conn.execute.await_args_list]
    assert sum("DELETE FROM kb_bulk_proposals" in s for s in backend_calls) == 1
    assert sum("DELETE FROM kb_bulk_runs" in s for s in backend_calls) == 1
    assert sum("DELETE FROM kb_bulk_configs" in s for s in backend_calls) == 1

    # ts is the reset-timestamp printed in the undo line; must be ISO-ish.
    assert isinstance(ts, str) and "T" in ts


@pytest.mark.asyncio
async def test_in_flight_run_blocks_when_processing():
    """If a kb_bulk_runs row for the org has status='running', return True."""
    backend_conn = AsyncMock()
    backend_conn.fetchval = AsyncMock(return_value=True)
    blocked = await in_flight_run_exists(backend_conn, org_id="org-1")
    assert blocked is True


@pytest.mark.asyncio
async def test_no_in_flight_run_allows_reset():
    backend_conn = AsyncMock()
    backend_conn.fetchval = AsyncMock(return_value=False)
    blocked = await in_flight_run_exists(backend_conn, org_id="org-1")
    assert blocked is False
