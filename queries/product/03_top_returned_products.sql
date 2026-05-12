-- File: queries/product/03_top_returned_products.sql
-- Question: Most-returned products by reason category.
-- Dialect: postgres
-- Phase 3 coverage: enum (returns.reason IN (...)).
-- Tables: products, returns, return_items, order_items, product_variants

SELECT p.title,
       r.reason,
       COUNT(*) AS return_count,
       SUM(r.refund_amount) AS refund_total
  FROM returns r
  JOIN return_items ri ON ri.return_id = r.id
  JOIN order_items oi  ON oi.id = ri.order_item_id
  JOIN product_variants pv ON pv.id = oi.variant_id
  JOIN products p          ON p.id  = pv.product_id
 WHERE r.reason IN ('defective', 'wrong_item', 'not_as_described')
 GROUP BY p.title, r.reason
 ORDER BY return_count DESC
 LIMIT 25;
