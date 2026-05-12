-- File: queries/revenue/01_monthly_revenue_yoy.sql
-- Question: Monthly GMV (gross merchandise value) with YoY % change.
-- Dialect: postgres
-- Phase 3 coverage: date_filter (DATE_TRUNC on orders.created_at);
--                   display_column (orders.total).
-- Tables: orders

WITH monthly AS (
  SELECT DATE_TRUNC('month', created_at) AS month,
         SUM(total) AS gmv
    FROM orders
   WHERE status IN ('shipped', 'delivered', 'returned')
     AND created_at >= NOW() - INTERVAL '24 months'
   GROUP BY 1
)
SELECT month,
       gmv,
       LAG(gmv, 12) OVER (ORDER BY month) AS gmv_prior_year,
       CASE WHEN LAG(gmv, 12) OVER (ORDER BY month) IS NULL THEN NULL
            ELSE (gmv - LAG(gmv, 12) OVER (ORDER BY month))
                  / NULLIF(LAG(gmv, 12) OVER (ORDER BY month), 0)
       END AS yoy_change
  FROM monthly
 ORDER BY month;
