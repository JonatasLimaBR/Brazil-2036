-- Silver model: normalize BCB SGS series 13762 (Divida Bruta do Governo
-- Geral, % PIB) into (state_ibge_code, metric_id, reference_date, value)
-- rows. state_ibge_code is a constant 'BR' sentinel (same convention as
-- fiscal_uniao.sql/pib_mensal.sql). Value is already a percentage as
-- published -- no unit conversion needed (unlike pib_mensal's millions ->
-- reais).
-- Whole-table rebuild every run: source republishes its entire history each
-- call (DESIGN §0.1).
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.divida_bruta_pib`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  'divida_bruta_pib' AS metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value AS NUMERIC) AS value,
  'pct_pib' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
