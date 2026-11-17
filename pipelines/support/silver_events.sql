CREATE OR REFRESH MATERIALIZED VIEW ${silver_schema}.silver_events
SELECT
  event_id
  , customer_id
  , event_ts
  , to_date(event_ts) AS event_date
  , event_type
  , feature_name
  , status_code
  , latency_ms
  , (event_type = 'error' OR status_code >= 500) AS is_error
FROM bronze_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingested_at DESC) = 1