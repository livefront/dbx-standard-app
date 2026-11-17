CREATE OR REFRESH MATERIALIZED VIEW ${silver_schema}.silver_tickets AS
SELECT
  ticket_id
  , customer_id
  , created_at
  , resolved_at
  , category
  , subject
  , priority
  , status
  , first_response_minutes
  , resolved_at IS NOT NULL AS is_resolved
  , ROUND((unix_timestamp(resolved_at) - unix_timestamp(created_at)) / 3600.0, 2) AS resolution_hours
FROM bronze_tickets
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY ingested_at DESC) = 1