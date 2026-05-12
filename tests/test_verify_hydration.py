"""Tests for verify_hydration.py.

verify_hydration assembles a coverage report from 4 sources:
  1. KB postgres counts (live_db source descs, date_filter / filter_condition
     columns, unattempted descs, enum-extracted values via column_values rows).
  2. Backend postgres: kb_bulk_runs metadata (phantom-table evidence in
     telemetry hooks, table_reference_map).
  3. Backend docker logs (confidence-distribution line).
  4. KB_BULK_V2_ENABLED settings via a backend `/healthz/flags` probe OR by
     reading env from the backend container.

Tests cover the report-shape and the pass/fail computation. The data sources
are mocked.
"""
import pytest
from unittest.mock import AsyncMock

from tools.verify_hydration import compute_report, report_passes, format_report


@pytest.mark.asyncio
async def test_compute_report_full_pass():
    kb_conn = AsyncMock()
    # Order: live_db, date_filter, filter_condition, enum_values, unattempted
    kb_conn.fetchval = AsyncMock(side_effect=[42, 7, 19, 3, 113])
    backend_conn = AsyncMock()
    backend_conn.fetchrow = AsyncMock(return_value={
        "parsing_stats": {"phantom_tables": ["customer_segments"]},
    })
    log_text = (
        "2026-05-12 10:00:00 INFO kb_bulk.agent_descriptions: run=r batch=0 "
        "proposed=5 with_evidence=4 refusal=1 "
        "confidence_distribution={high:2, medium:2, low:1, low_pct:20.0}"
    )
    report = await compute_report(
        kb_conn=kb_conn, backend_conn=backend_conn,
        run_id="r-1", org_id="org-1",
        log_text=log_text, kb_bulk_v2_enabled=True,
    )
    assert report["live_db_descriptions"] == 42
    assert report["date_filter_columns"] == 7
    assert report["filter_condition_columns"] == 19
    assert report["enum_value_columns"] == 3
    assert report["unattempted_descriptions"] == 113
    assert report["phantom_table_flagged"] is True
    assert report["confidence_dist_log_present"] is True
    assert report["kb_bulk_v2_enabled"] is True
    assert report_passes(report) is True


@pytest.mark.asyncio
async def test_compute_report_flags_enum_extraction_miss():
    kb_conn = AsyncMock()
    kb_conn.fetchval = AsyncMock(side_effect=[42, 7, 19, 0, 113])
    backend_conn = AsyncMock()
    backend_conn.fetchrow = AsyncMock(return_value={
        "parsing_stats": {"phantom_tables": ["customer_segments"]},
    })
    report = await compute_report(
        kb_conn=kb_conn, backend_conn=backend_conn,
        run_id="r-1", org_id="org-1",
        log_text="kb_bulk.agent_descriptions: ...",
        kb_bulk_v2_enabled=True,
    )
    assert report["enum_value_columns"] == 0
    assert report_passes(report) is False
    formatted = format_report(report)
    assert "✗" in formatted
    assert "enum-extracted" in formatted


@pytest.mark.asyncio
async def test_compute_report_warns_when_v2_disabled():
    kb_conn = AsyncMock()
    kb_conn.fetchval = AsyncMock(side_effect=[0, 0, 0, 0, 0])
    backend_conn = AsyncMock()
    backend_conn.fetchrow = AsyncMock(return_value={"parsing_stats": {}})
    report = await compute_report(
        kb_conn=kb_conn, backend_conn=backend_conn,
        run_id="r-1", org_id="org-1",
        log_text="",
        kb_bulk_v2_enabled=False,
    )
    assert report["kb_bulk_v2_enabled"] is False
    assert report_passes(report) is False
    assert "KB_BULK_V2_ENABLED" in format_report(report)
