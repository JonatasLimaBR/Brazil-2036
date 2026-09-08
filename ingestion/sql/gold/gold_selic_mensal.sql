-- Gold model: canonical selic_mensal metric, national, monthly.
-- data_class = 'observed' (ADR-028). Real base for the DebtLab
-- suggested-assumptions endpoint (ADR-060) -- read-only, never written
-- by the simulator.
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_selic_mensal`
PARTITION BY reference_date
CLUSTER BY metric_id
AS
SELECT
  state_ibge_code,
  metric_id,
  reference_date,
  value,
  unit,
  'observed' AS data_class
FROM `${project}.${bq_dataset_silver}.selic_mensal`;
