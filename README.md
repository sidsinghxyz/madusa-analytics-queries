# madusa-analytics-queries

Curated analyst SQL queries for the **Madusa** dev org on Uncypher, plus
operator tooling to test the Generate-KB flow.

The 17 `.sql` files under `queries/` are designed so the **set as a whole**
exercises every Phase 3 hydration path of the KB-audit waterfall:

- `revenue/`, `retention/`, `product/`, `fraud_ops/` — realistic analyst
  questions (4 + 3 + 3 + 3 files).
- `phase3_coverage/` — four surgical edge cases:
  - `01_phantom_table.sql` — references a table that doesn't exist (Stage 1
    `live_db_missing=True`).
  - `02_typo_column.sql` — references a column whose name is a typo of a
    real one.
  - `03_dominant_role_flip.sql` — same column used in WHERE 5× and SELECT 2×;
    Stage 2 dominant-role tiebreak should pick `filter_condition`.
  - `04_enum_in_clause.sql` — three WHERE-IN clauses covering five distinct
    values; Stage 2 value-enum extraction should collect them all.

## Setup

```bash
make install
export DEV_BACKEND_URL=https://api.uncypher.sidsingh.xyz
export DEV_JWT=<grab from a dev frontend session>
export KB_PG_DSN=postgresql://kb:<pw>@localhost:5432/kb        # or in-container default
export BACKEND_PG_DSN=postgresql://postgres:<pw>@localhost:5432/data_decipher
```

If you're running the tools from inside the backend container, the DSNs
default to in-container service names (`uncypher-kb-postgres`, etc.) — you
only need `DEV_JWT` set.

## Connect to Madusa (one-time, idempotent)

```bash
make connect
```

This POSTs a new codebase to Madusa's org via `/api/orgs/<org>/codebases`
and waits for clone to finish. Re-running is safe — it returns the existing
codebase if one already matches.

## Reset Madusa KB (between test iterations)

```bash
make reset           # dry-run, prints affected counts
make reset-apply     # actually wipes
```

Wipes are **soft** (`is_deleted=true` / `soft_deleted=true`). After apply
the script prints the undo SQL.

## Verify a run

After triggering Generate KB on Madusa pointing at this repo's `queries/`,
grab the `run_id` from the UI (or `kb_bulk_runs` table) and run:

```bash
make verify RUN_ID=<id>
```

Output is a tick/cross coverage table over the Phase 3 hydration paths.
Exit code 0 = all pass, non-zero = something missing.

## Phase 3 acceptance one-liner

```bash
make accept-phase3 RUN_ID=<id>
```

Chains `reset-apply` → `verify`. Trigger Generate KB between the two calls.

## Constants

`tools/_config.py` holds the Madusa-on-dev IDs (org, project, database).
Override via env vars (`MADUSA_ORG_ID`, `MADUSA_PROJECT_ID`,
`MADUSA_DATABASE_ID`) if you point the seed at a different env.
