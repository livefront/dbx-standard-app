CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.gold_ticket_facts (
  ticket_id BIGINT COMMENT 'Support ticket identifier.',
  customer_id BIGINT COMMENT 'Customer identifier. Joins to gold_customer_features and gold_customer_daily_activity.',
  company_name STRING COMMENT 'Customer company name.',
  industry STRING COMMENT 'Customer industry.',
  plan_tier STRING COMMENT 'Customer subscription plan: Basic, Pro, or Enterprise. Together with priority it sets the response-time SLA target.',
  region STRING COMMENT 'Customer region: NA-East, NA-West, NA-Central, EU, or APAC.',
  seats BIGINT COMMENT 'Number of licensed seats on the customer account.',
  mrr BIGINT COMMENT 'Customer monthly recurring revenue in USD (account level, not per ticket).',
  created_at TIMESTAMP COMMENT 'When the ticket was opened (UTC).',
  created_date DATE COMMENT 'Date the ticket was opened (UTC). Use for daily, weekly, and monthly ticket trends.',
  resolved_at TIMESTAMP COMMENT 'When the ticket was resolved (UTC). Null while the ticket is open.',
  category STRING COMMENT 'Ticket type: billing, bug, integration, access, or how-to.',
  priority STRING COMMENT 'Ticket priority, from least to most severe: low, medium, high, urgent.',
  status STRING COMMENT 'Ticket status: open or resolved.',
  is_resolved BOOLEAN COMMENT 'True when the ticket has been resolved.',
  first_response_minutes BIGINT COMMENT 'Minutes from ticket creation until the first support response. Compared against the SLA target for the plan tier and priority.',
  resolution_hours DECIMAL(24,2) COMMENT 'Hours from ticket creation to resolution. Null for open tickets.',
  errors_24h_before BIGINT COMMENT 'Number of product error events for the customer in the 24 hours before the ticket was opened. High values suggest the ticket was triggered by a product failure.'
)
COMMENT 'One row per support ticket with customer attributes, response and resolution times, and preceding product errors. Use for ticket queues, SLA performance, volume trends, and root-cause questions.'
AS WITH errors_before AS (
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
