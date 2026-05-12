-- File: queries/fraud_ops/01_chargeback_rate.sql
-- Question: Chargeback rate by payment provider.
-- Dialect: postgres
-- Phase 3 coverage: enum (payments.provider IN ('stripe','paypal','apple_pay'));
--                   filter_condition (payments.status='refunded').
-- Tables: payments, chargebacks

SELECT p.provider,
       COUNT(DISTINCT p.id)              AS total_payments,
       COUNT(DISTINCT cb.id)             AS chargebacks,
       COUNT(DISTINCT cb.id)::numeric
         / NULLIF(COUNT(DISTINCT p.id), 0) AS chargeback_rate
  FROM payments p
  LEFT JOIN chargebacks cb ON cb.payment_id = p.id
 WHERE p.provider IN ('stripe', 'paypal', 'apple_pay', 'bank_transfer')
   AND p.status   <> 'refunded'
   AND p.created_at >= NOW() - INTERVAL '180 days'
 GROUP BY p.provider
 ORDER BY chargeback_rate DESC;
