CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.gold_customer_daily_activity (
  customer_id BIGINT COMMENT 'Customer identifier. Joins to gold_customer_features and gold_ticket_facts.',
  company_name STRING COMMENT 'Customer company name.',
  plan_tier STRING COMMENT 'Subscription plan: Basic, Pro, or Enterprise.',
  region STRING COMMENT 'Customer region: NA-East, NA-West, NA-Central, EU, or APAC.',
  industry STRING COMMENT 'Customer industry.',
  event_date DATE COMMENT 'Calendar date of the product activity (UTC).',
  events BIGINT COMMENT 'Total product events for the customer on this date.',
  logins BIGINT COMMENT 'Number of user logins on this date.',
  api_calls BIGINT COMMENT 'Number of API calls on this date.',
  feature_uses BIGINT COMMENT 'Number of product feature uses on this date.',
  errors BIGINT COMMENT 'Number of error events on this date, including API calls that returned a 5xx status. Rising errors often precede bug and integration tickets.',
  avg_latency_ms DOUBLE COMMENT 'Average API call latency in milliseconds on this date. Null when there were no API calls.'
)
COMMENT 'Daily product activity per customer (one row per customer per day with activity). Use for usage trends, error trends, and spotting customers whose errors are rising.'
AS SELECT
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
