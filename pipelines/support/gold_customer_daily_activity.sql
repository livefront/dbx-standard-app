CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.gold_customer_daily_activity AS
SELECT
  e.customer_id,
  c.company_name,
  c.plan_tier,
  c.region,
  c.industry,
  e.event_date,
  COUNT(*) AS events,
  COUNT_IF(e.event_type = 'login') AS logins,
  COUNT_IF(e.event_type = 'api_call') AS api_calls,
  COUNT_IF(e.event_type = 'feature_used') AS feature_uses,
  COUNT_IF(e.is_error) AS errors,
  ROUND(AVG(e.latency_ms), 1) AS avg_latency_ms
FROM ${silver_schema}.silver_events e
JOIN ${silver_schema}.silver_customers c ON c.customer_id = e.customer_id
GROUP BY e.customer_id, c.company_name, c.plan_tier, c.region, c.industry, e.event_date