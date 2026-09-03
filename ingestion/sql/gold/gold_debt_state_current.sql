-- Gold model: canonical annual consolidated-debt metric per state.
-- metric_id = 'divida_consolidada' (gross, PAF -- DESIGN D12). data_class = 'observed' (ADR-028).
-- Idempotent MERGE on (state_ibge_code, reference_year, metric_id).
-- Placeholders substituted from config.yaml:
--   ${project} ${bq_dataset_gold} ${bq_dataset_silver} ${gold_table} ${silver_table}
--   ${metric_id} ${unit} ${data_class}

MERGE `${project}.${bq_dataset_gold}.${gold_table}` AS target
USING (
  SELECT
    s.state_ibge_code,
    s.state_name,
    s.reference_year,
    s.reference_date,
    '${metric_id}' AS metric_id,
    s.value,
    '${unit}' AS unit,
    '${data_class}' AS data_class
  FROM `${project}.${bq_dataset_silver}.${silver_table}` AS s
) AS source
ON  target.state_ibge_code = source.state_ibge_code
AND target.reference_year  = source.reference_year
AND target.metric_id       = source.metric_id
WHEN MATCHED THEN UPDATE SET
  value = source.value,
  unit = source.unit,
  data_class = source.data_class,
  reference_date = source.reference_date,
  state_name = source.state_name
WHEN NOT MATCHED THEN INSERT ROW;
