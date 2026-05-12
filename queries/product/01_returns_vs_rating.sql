-- File: queries/product/01_returns_vs_rating.sql
-- Question: Is there a correlation between product rating and return rate?
-- Dialect: postgres
-- Phase 3 coverage: filter_condition (product_reviews.rating); aggregation.
-- Tables: products, product_reviews, returns, order_items

SELECT p.id,
       p.title,
       AVG(pr.rating)                AS avg_rating,
       COUNT(DISTINCT pr.id)         AS review_count,
       COUNT(DISTINCT r.id)::numeric
         / NULLIF(COUNT(DISTINCT oi.id), 0) AS return_rate
  FROM products p
  LEFT JOIN product_reviews pr ON pr.product_id = p.id
  LEFT JOIN product_variants pv ON pv.product_id = p.id
  LEFT JOIN order_items oi      ON oi.variant_id = pv.id
  LEFT JOIN returns r           ON r.order_id   = oi.order_id
 WHERE pr.rating <= 3
 GROUP BY p.id, p.title
 HAVING COUNT(DISTINCT pr.id) >= 5
 ORDER BY return_rate DESC NULLS LAST
 LIMIT 50;
