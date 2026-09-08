-- Silver model: normalize BCB SGS series 3695 (Taxa de cambio USD/BRL,
-- media de periodo mensal) into (state_ibge_code, metric_id,
-- reference_date, value) rows. state_ibge_code is a constant 'BR'
-- sentinel (same convention as pib_mensal.sql). No consumer in the
-- DebtLab engine yet -- pure Macro Twin coverage.
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.cambio_usd_brl`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  'cambio_usd_brl' AS metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value AS NUMERIC) AS value,
  'brl_per_usd' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
