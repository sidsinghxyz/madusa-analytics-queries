-- File: queries/fraud_ops/02_support_sla_breach.sql
-- Question: Tickets breaching 24h first-response SLA, by priority.
-- Dialect: postgres
-- Phase 3 coverage: enum (support_tickets.priority); date math.
-- Tables: support_tickets

SELECT priority,
       COUNT(*) AS total_tickets,
       SUM(CASE
             WHEN first_response_at IS NULL
               OR first_response_at > created_at + INTERVAL '24 hours'
             THEN 1 ELSE 0
           END) AS sla_breaches
  FROM support_tickets
 WHERE priority IN ('low', 'medium', 'high', 'urgent')
   AND created_at >= NOW() - INTERVAL '30 days'
 GROUP BY priority
 ORDER BY CASE priority
            WHEN 'urgent' THEN 0
            WHEN 'high'   THEN 1
            WHEN 'medium' THEN 2
            ELSE 3
          END;
