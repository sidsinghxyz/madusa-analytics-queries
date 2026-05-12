-- File: queries/phase3_coverage/03_dominant_role_flip.sql
-- Question: Multiple statements that touch `orders.channel` — five WHERE
--           uses, two SELECT-only uses. Stage 2 should classify `channel`
--           as filter_condition (WHERE wins).
-- Dialect: postgres
-- Phase 3 coverage: STAGE 2 dominant-role tiebreak.
-- Tables: orders

-- 1: WHERE
SELECT COUNT(*) FROM orders WHERE channel = 'web';

-- 2: WHERE
SELECT COUNT(*) FROM orders WHERE channel = 'mobile_app';

-- 3: WHERE
SELECT SUM(total) FROM orders WHERE channel = 'pos';

-- 4: WHERE
SELECT customer_id FROM orders WHERE channel = 'marketplace' GROUP BY customer_id;

-- 5: WHERE
SELECT created_at FROM orders WHERE channel <> 'web';

-- 6: SELECT-only
SELECT id, channel FROM orders LIMIT 100;

-- 7: SELECT-only
SELECT channel FROM orders ORDER BY created_at DESC LIMIT 10;
