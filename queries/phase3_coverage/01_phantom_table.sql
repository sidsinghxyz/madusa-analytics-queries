-- File: queries/phase3_coverage/01_phantom_table.sql
-- Question: VIP customer segmentation — joins a table that doesn't exist
--           in the live Madusa DB. We use 'customer_segments' here (the
--           real table is 'customer_groups').
-- Dialect: postgres
-- Phase 3 coverage: STAGE 1 — live_db_missing=True for `customer_segments`.
--                   This is INTENTIONAL. Verify telemetry records the miss.
-- Tables: customers, customer_segments (PHANTOM)

SELECT cs.name              AS segment,
       COUNT(c.id)          AS customer_count,
       COUNT(DISTINCT o.id) AS order_count,
       SUM(o.total)         AS revenue
  FROM customers c
  JOIN customer_segments cs ON cs.id = c.segment_id
  LEFT JOIN orders o        ON o.customer_id = c.id
 WHERE c.created_at >= NOW() - INTERVAL '12 months'
 GROUP BY cs.name
 ORDER BY revenue DESC;
