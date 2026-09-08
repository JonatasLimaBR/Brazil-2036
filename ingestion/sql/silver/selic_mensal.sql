-- Silver model: normalize BCB SGS series 4390 (Selic acumulada no mes)
-- into (state_ibge_code, metric_id, reference_date, value) rows.
-- state_ibge_code is a constant 'BR' sentinel (same convention as
-- pib_mensal.sql). Value stays as the raw monthly accumulated rate as
-- published (%) -- annualized later, at read time, by
-- bigquery_repo.py::suggested_assumptions() (DESIGN D2), not here.
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.selic_mensal`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  'selic_mensal' AS metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value AS NUMERIC) AS value,
  'pct' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
