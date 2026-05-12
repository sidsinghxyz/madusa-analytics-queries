-- File: queries/revenue/04_top_skus_by_margin.sql
-- Question: Top 20 SKUs by realised margin (sale price - cost).
-- Dialect: postgres
-- Phase 3 coverage: display_column (product_variants.compare_at_price);
--                   multi-JOIN.
-- Tables: order_items, product_variants, products

SELECT pv.sku,
       p.title,
       SUM(oi.quantity)               AS units_sold,
       SUM(oi.total)                  AS gross_revenue,
       AVG(pv.compare_at_price - pv.price) AS avg_discount_per_unit
  FROM order_items oi
  JOIN product_variants pv ON pv.id = oi.variant_id
  JOIN products p          ON p.id  = pv.product_id
 GROUP BY pv.sku, p.title
 ORDER BY gross_revenue DESC
 LIMIT 20;
