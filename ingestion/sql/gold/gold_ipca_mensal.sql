-- Gold model: canonical ipca_mensal metric, national, monthly.
-- data_class = 'observed' (ADR-028). Legitimately negative in a real
-- deflation month -- contract.check_gold_period(allow_negative=True) at
-- the caller (MACRO_TWIN_EXPANSION DESIGN 0.2), not enforced here.
-- Whole-table rebuild every run.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_ipca_mensal`
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
FROM `${project}.${bq_dataset_silver}.ipca_mensal`;
