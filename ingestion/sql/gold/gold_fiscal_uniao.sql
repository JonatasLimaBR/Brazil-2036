-- Gold model: canonical fiscal_receita/fiscal_despesa/fiscal_primario metrics,
-- Central Government, monthly. 1 table, 3 metric_id values (DESIGN D2): unlike
-- INSS's 3 separate Gold tables, these 3 metrics come from the same file, same
-- grain, same pipeline run -- fusing them costs nothing and matches how
-- Config.metric_tables already maps many metric_id keys to one table.
-- data_class = 'observed' (ADR-028). fiscal_primario is legitimately negative
-- in a primary deficit -- see contract.check_gold_period(allow_negative=True)
-- at the caller, not enforced here.
-- Whole-table rebuild every run (same reasoning as the Silver model above).
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}

CREATE OR REPLACE TABLE `${project}.${bq_dataset_gold}.gold_fiscal_uniao`
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
FROM `${project}.${bq_dataset_silver}.fiscal_uniao`;
