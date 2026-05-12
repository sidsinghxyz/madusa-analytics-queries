-- File: queries/phase3_coverage/04_enum_in_clause.sql
-- Question: Three statements that filter `payments.status` with WHERE-IN
--           clauses, covering five distinct values. Stage 2 should extract
--           {'paid','pending','refunded','failed','cancelled'} as enum
--           candidates with confidence='low'.
-- Note: plan example used `order_status`; the real Madusa column is
--       `payments.status` (per docs/plans/2026-02-25-demo-data-design.md),
--       so this file uses `status`.
-- Dialect: postgres
-- Phase 3 coverage: STAGE 2 value-enum extraction.
-- Tables: payments

-- 1: two values
SELECT COUNT(*) FROM payments WHERE status IN ('paid', 'refunded');

-- 2: three values, two overlap with statement 1
SELECT SUM(amount) FROM payments WHERE status IN ('paid', 'pending', 'failed');

-- 3: two values, one new
SELECT status, COUNT(*) FROM payments
 WHERE status IN ('paid', 'cancelled')
 GROUP BY status;
