-- File: queries/phase3_coverage/02_typo_column.sql
-- Question: Orders by week — uses `orders.created_dt` (real column is
--           `orders.created_at`). Stage 1 returns the real columns; the
--           agent stage must reconcile the typo.
-- Dialect: postgres
-- Phase 3 coverage: typo-column reconciliation.
-- Tables: orders

SELECT DATE_TRUNC('week', created_dt) AS week,
       COUNT(*)                       AS order_count,
       SUM(total)                     AS gmv
  FROM orders
 WHERE created_dt >= NOW() - INTERVAL '12 weeks'
 GROUP BY 1
 ORDER BY 1;
