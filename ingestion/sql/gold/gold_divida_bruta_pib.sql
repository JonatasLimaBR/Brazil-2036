-- Gold model: canonical divida_bruta_pib metric, national, monthly.
-- data_class = 'observed' (ADR-028). This is the real base input for the
-- DebtLab simulator (SPEC-010) -- SIMULATED projections never overwrite
-- this table (ADR-013/ADR-042: the simulator reads this, never writes it).
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_divida_bruta_pib`
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
FROM `${project}.${bq_dataset_silver}.divida_bruta_pib`;
