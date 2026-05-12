-- File: queries/retention/01_cohort_retention.sql
-- Question: Monthly cohort retention matrix — how many of each signup-month
--           cohort placed an order N months later?
-- Dialect: postgres
-- Phase 3 coverage: self-JOIN on orders; two date_filter usages
--                   (orders.created_at appears twice with date-month math).
-- Tables: customers, orders

WITH first_orders AS (
  SELECT customer_id,
         DATE_TRUNC('month', MIN(created_at)) AS cohort_month
    FROM orders
   GROUP BY customer_id
)
SELECT fo.cohort_month,
       DATE_TRUNC('month', o.created_at) AS order_month,
       COUNT(DISTINCT o.customer_id) AS active_customers
  FROM first_orders fo
  JOIN orders o ON o.customer_id = fo.customer_id
 WHERE fo.cohort_month >= NOW() - INTERVAL '12 months'
   AND o.created_at    >= fo.cohort_month
 GROUP BY fo.cohort_month, DATE_TRUNC('month', o.created_at)
 ORDER BY fo.cohort_month, order_month;
