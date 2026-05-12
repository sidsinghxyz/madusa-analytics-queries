"""asyncpg connection helper for direct KB / backend Postgres access.

Both reset_madusa_kb and verify_hydration use this. Wrap is a context
manager so connections close on exit even when --apply errors mid-run.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
import asyncpg


@asynccontextmanager
async def pg(dsn: str) -> AsyncIterator[asyncpg.Connection]:
    """Open one asyncpg connection. Caller awaits queries through `conn`."""
    conn = await asyncpg.connect(dsn=dsn)
    try:
        yield conn
    finally:
        await conn.close()
