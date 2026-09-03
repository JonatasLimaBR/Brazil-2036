-- Silver model: normalize the PAF consolidated-debt CSV.
-- Dataform-shaped (one model per file); executed via the BigQuery client on the
-- walking skeleton (ADR-052). Placeholders are substituted from config.yaml.
--   ${project}                    GCP project id
--   ${bq_dataset_silver}          e.g. br2036_silver
--   ${bq_dataset_bronze}         e.g. br2036_bronze
--   ${bq_dataset_control}        e.g. br2036_control
--   ${silver_table} ${bronze_table} ${uf_ibge_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.${silver_table}`
PARTITION BY reference_date
CLUSTER BY state_ibge_code
AS
SELECT
  u.state_ibge_code,
  u.state_name,
  CAST(b.ANO AS INT64) AS reference_year,
  DATE(CAST(b.ANO AS INT64), 12, 31) AS reference_date,
  CAST(REPLACE(REPLACE(b.VALOR, '.', ''), ',', '.') AS NUMERIC) AS value,
  'BRL' AS unit,
  b._row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}` AS b
JOIN `${project}.${bq_dataset_control}.${uf_ibge_table}` AS u
  ON u.uf = b.UF;
