-- File: queries/fraud_ops/03_fulfillment_lag.sql
-- Question: Average shipping lag (placed → shipped) by region & channel.
-- Dialect: postgres
-- Phase 3 coverage: display_column for rarely-used tracking fields; 4-JOIN.
-- Tables: orders, fulfillments, regions, sales_channels

SELECT r.name           AS region,
       sc.name          AS channel,
       AVG(EXTRACT(EPOCH FROM (f.shipped_at - o.created_at)) / 3600.0) AS hours_to_ship,
       AVG(EXTRACT(EPOCH FROM (f.delivered_at - f.shipped_at)) / 3600.0) AS hours_to_deliver,
       AVG(EXTRACT(EPOCH FROM (f.shipped_at - o.created_at)) / 3600.0) FILTER (WHERE f.tracking_number IS NOT NULL) AS hours_to_ship_with_tracking
  FROM orders o
  JOIN fulfillments f      ON f.order_id = o.id
  JOIN regions r           ON r.id  = o.region_id
  JOIN sales_channels sc   ON sc.id = o.sales_channel_id
 WHERE f.shipped_at IS NOT NULL
   AND o.created_at >= NOW() - INTERVAL '60 days'
 GROUP BY r.name, sc.name
 ORDER BY hours_to_ship DESC;
