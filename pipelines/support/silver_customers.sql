CREATE OR REFRESH MATERIALIZED VIEW ${silver_schema}.silver_customers AS
SELECT
  id as customer_id
  , name as company_name 
  , industry
  , plan_tier
  , region
  , seats
  , mrr
  , signup_date
  , account_contact
FROM bronze_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY ingested_at DESC) = 1