-- File: queries/retention/03_mrr_trend.sql
-- Question: MRR trend with churn/expansion split.
-- Dialect: postgres
-- Phase 3 coverage: display_column (subscription_plans.mrr); date_filter.
-- Tables: subscription_plans

SELECT DATE_TRUNC('month', started_at) AS month,
       SUM(mrr)                         AS total_mrr,
       SUM(CASE WHEN status='canceled' THEN mrr ELSE 0 END) AS churned_mrr,
       SUM(CASE WHEN status='active'   THEN mrr ELSE 0 END) AS active_mrr
  FROM subscription_plans
 WHERE started_at >= NOW() - INTERVAL '18 months'
 GROUP BY 1
 ORDER BY 1;
