-- Silver model: normalize the Tesouro Nacional wide monthly series (RTN) into
-- (state_ibge_code, metric_id, reference_date, value) rows.
-- state_ibge_code is a constant 'BR' sentinel: this source has no territorial
-- dimension (Central Government consolidated), kept only so this table shares
-- the same key-field shape debt/INSS already use, so provenance.write_from_gold
-- and contract.check_gold_period need no per-dataset branching (DESIGN D2).
-- value_millions (source unit, R$ millions) is converted to reais here so the
-- API/frontend never see a unit other than 'BRL' (DESIGN D7).
-- Whole-table rebuild every run: the source republishes its entire history
-- each time there is no prior period to preserve, unlike INSS's partitioned
-- accumulation (DESIGN D8).
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bronze_table}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_silver}.fiscal_uniao`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  'BR' AS state_ibge_code,
  metric_id,
  DATE(reference_period) AS reference_date,
  CAST(value_millions AS NUMERIC) * 1000000 AS value,
  'BRL' AS unit,
  _row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}`;
