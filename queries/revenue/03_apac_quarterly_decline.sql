-- File: queries/revenue/03_apac_quarterly_decline.sql
-- Question: APAC revenue quarter-over-quarter — drilldown to detect declines.
-- Dialect: postgres
-- Phase 3 coverage: filter_condition (regions.name='Asia Pacific');
--                   date_filter BETWEEN with quarterly buckets.
-- Tables: orders, regions, product_categories

SELECT DATE_TRUNC('quarter', o.created_at) AS quarter,
       pc.name                              AS category,
       SUM(o.total)                         AS revenue
  FROM orders o
  JOIN regions r            ON r.id  = o.region_id
  JOIN order_items oi       ON oi.order_id = o.id
  JOIN product_variants pv  ON pv.id = oi.variant_id
  JOIN products p           ON p.id  = pv.product_id
  JOIN product_categories pc ON pc.id = p.category_id
 WHERE r.name = 'Asia Pacific'
   AND o.created_at BETWEEN NOW() - INTERVAL '8 quarters' AND NOW()
 GROUP BY 1, 2
 ORDER BY 1, revenue DESC;
