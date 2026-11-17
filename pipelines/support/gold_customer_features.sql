CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.gold_customer_features AS
SELECT
  c.customer_id,
  c.company_name,
  c.plan_tier,
  c.region,
  c.industry,
  c.seats,
  c.mrr,
  DATEDIFF(current_date(), to_date(c.signup_date)) AS account_age_days,
  COALESCE(t.tickets_total, 0) AS tickets_total,
  COALESCE(t.tickets_30d, 0) AS tickets_30d,
  COALESCE(t.urgent_tickets_30d, 0) AS urgent_tickets_30d,
  COALESCE(t.open_tickets, 0) AS open_tickets,
  t.avg_first_response_minutes,
  t.avg_resolution_hours,
  COALESCE(e.events_7d, 0) AS events_7d,
  COALESCE(e.errors_7d, 0) AS errors_7d
FROM ${silver_schema}.silver_customers c
LEFT JOIN (
  SELECT
    customer_id,
    COUNT(*) AS tickets_total,
    COUNT_IF(created_at >= current_date() - INTERVAL 30 DAYS) AS tickets_30d,
    COUNT_IF(priority = 'urgent' AND created_at >= current_date() - INTERVAL 30 DAYS) AS urgent_tickets_30d,
    COUNT_IF(NOT is_resolved) AS open_tickets,
    ROUND(AVG(first_response_minutes), 1) AS avg_first_response_minutes,
    ROUND(AVG(resolution_hours), 1) AS avg_resolution_hours
  FROM ${silver_schema}.silver_tickets
  GROUP BY customer_id
) t ON t.customer_id = c.customer_id
LEFT JOIN (
  SELECT
    customer_id,
    COUNT(*) AS events_7d,
    COUNT_IF(is_error) AS errors_7d
  FROM ${silver_schema}.silver_events
  WHERE event_ts >= current_date() - INTERVAL 7 DAYS
  GROUP BY customer_id
) e ON e.customer_id = c.customer_id