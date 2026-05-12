-- File: queries/revenue/02_revenue_by_region_channel.sql
-- Question: Revenue by region × channel for the last 90 days.
-- Dialect: postgres
-- Phase 3 coverage: enum (orders.status IN ('shipped','delivered','returned'));
--                   3-table JOIN (orders↔regions↔sales_channels).
-- Tables: orders, regions, sales_channels

SELECT r.name           AS region,
       sc.name          AS channel,
       COUNT(*)         AS order_count,
       SUM(o.total)     AS revenue
  FROM orders o
  JOIN regions r           ON r.id  = o.region_id
  JOIN sales_channels sc   ON sc.id = o.sales_channel_id
 WHERE o.status IN ('shipped', 'delivered', 'returned')
   AND o.created_at >= NOW() - INTERVAL '90 days'
 GROUP BY r.name, sc.name
 ORDER BY revenue DESC;
