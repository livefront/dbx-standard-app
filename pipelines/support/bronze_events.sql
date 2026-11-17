CREATE OR REFRESH MATERIALIZED VIEW bronze_events AS
SELECT
  *,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/${catalog_name}/${raw_schema}/events/',
  format => 'parquet'
)