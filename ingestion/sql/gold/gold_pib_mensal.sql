-- Gold model: canonical pib_mensal metric, national, monthly.
-- data_class = 'observed' (ADR-028). Whole-table rebuild every run (same
-- reasoning as the Silver model above).
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_pib_mensal`
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
FROM `${project}.${bq_dataset_silver}.pib_mensal`;
