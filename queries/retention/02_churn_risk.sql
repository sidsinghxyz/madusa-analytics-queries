-- File: queries/retention/02_churn_risk.sql
-- Question: Customers at churn risk — no orders in 60d, open support ticket,
--           and a non-active subscription.
-- Dialect: postgres
-- Phase 3 coverage: enum (subscription_plans.status IN ('past_due','canceled'));
--                   4-table JOIN.
-- Tables: customers, orders, support_tickets, subscription_plans

SELECT c.id,
       c.email,
       MAX(o.created_at)                 AS last_order_at,
       COUNT(DISTINCT t.id)              AS open_tickets,
       sp.status                         AS subscription_status
  FROM customers c
  LEFT JOIN orders o            ON o.customer_id = c.id
  LEFT JOIN support_tickets t   ON t.customer_id = c.id AND t.status='open'
  LEFT JOIN subscription_plans sp ON sp.customer_id = c.id
 WHERE sp.status IN ('past_due', 'canceled')
 GROUP BY c.id, c.email, sp.status
HAVING MAX(o.created_at) < NOW() - INTERVAL '60 days'
   AND COUNT(DISTINCT t.id) > 0
 ORDER BY open_tickets DESC;
