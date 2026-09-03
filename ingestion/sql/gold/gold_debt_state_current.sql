-- Gold model: canonical annual consolidated-debt metric per state.
-- metric_id = 'divida_consolidada' (gross, PAF -- DESIGN D12). data_class = 'observed' (ADR-028).
-- Full idempotent rebuild (walking skeleton): no DML, so no streaming-buffer constraint,
-- and the table needs no pre-existing schema.
-- Placeholders substituted from config.yaml:
--   ${project} ${bq_dataset_gold} ${bq_dataset_silver} ${gold_table} ${silver_table}
--   ${metric_id} ${unit} ${data_class}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.${gold_table}`
PARTITION BY reference_date
CLUSTER BY state_ibge_code
AS
SELECT
  s.state_ibge_code,
  s.state_name,
  s.reference_year,
  s.reference_date,
  '${metric_id}' AS metric_id,
  s.value,
  '${unit}' AS unit,
  '${data_class}' AS data_class
FROM `${project}.${bq_dataset_silver}.${silver_table}` AS s;
