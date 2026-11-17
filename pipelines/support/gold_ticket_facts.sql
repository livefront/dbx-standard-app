CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.gold_ticket_facts AS
WITH errors_before AS (
  SELECT t.ticket_id, COUNT(e.event_id) AS errors_24h_before
  FROM ${silver_schema}.silver_tickets t
  LEFT JOIN ${silver_schema}.silver_events e
    ON e.customer_id = t.customer_id
   AND e.is_error
   AND e.event_ts >= t.created_at - INTERVAL 24 HOURS
   AND e.event_ts < t.created_at
  GROUP BY t.ticket_id
)
SELECT
  t.ticket_id,
  t.customer_id,
  c.company_name,
  c.industry,
  c.plan_tier,
  c.region,
  c.seats,
  c.mrr,
  t.created_at,
  to_date(t.created_at) AS created_date,
  t.resolved_at,
  t.category,
  t.priority,
  t.status,
  t.is_resolved,
  t.first_response_minutes,
  t.resolution_hours,
  eb.errors_24h_before
FROM ${silver_schema}.silver_tickets t
JOIN ${silver_schema}.silver_customers c ON c.customer_id = t.customer_id
LEFT JOIN errors_before eb ON eb.ticket_id = t.ticket_id