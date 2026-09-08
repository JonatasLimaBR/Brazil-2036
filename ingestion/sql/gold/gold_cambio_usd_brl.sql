-- Gold model: canonical cambio_usd_brl metric, national, monthly.
-- data_class = 'observed' (ADR-028).
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_cambio_usd_brl`
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
FROM `${project}.${bq_dataset_silver}.cambio_usd_brl`;
