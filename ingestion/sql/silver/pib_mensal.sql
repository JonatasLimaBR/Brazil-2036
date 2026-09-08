-- Silver model: normalize BCB SGS series 4380 (PIB mensal, valores
-- correntes) into (state_ibge_code, metric_id, reference_date, value) rows.
-- state_ibge_code is a constant 'BR' sentinel: this source has no
-- territorial dimension (national), kept only so this table shares the same
-- key-field shape debt/INSS/fiscal already use (same convention as
-- fiscal_uniao.sql).
-- value (source unit, R$ millions) is converted to reais here so the
-- API/frontend never see a unit other than 'BRL'.
-- Whole-table rebuild every run: the source republishes its entire history
-- each call, same as fiscal_uniao (DESIGN §0.1).
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.pib_mensal`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  'pib_mensal' AS metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value AS NUMERIC) * 1000000 AS value,
  'BRL' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
