-- Silver model: normalize BCB SGS series 433 (IPCA - Variacao mensal)
-- into (state_ibge_code, metric_id, reference_date, value) rows.
-- state_ibge_code is a constant 'BR' sentinel (same convention as
-- pib_mensal.sql/divida_bruta_pib.sql). Value stays as the raw percentage
-- as published, legitimately negative in a deflation month -- enforced
-- per-metric_id via contract.check_gold_period(allow_negative=True) at
-- the caller, not here (same pattern as fiscal_primario).
-- Whole-table rebuild every run: source republishes its entire history
-- each call (same as pib_mensal/divida_bruta_pib).
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.ipca_mensal`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  'ipca_mensal' AS metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value AS NUMERIC) AS value,
  'pct' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
