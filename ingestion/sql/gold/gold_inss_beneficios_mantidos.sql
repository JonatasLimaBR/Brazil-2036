-- Gold model: UF x especie x status_manutencao x month aggregate.
-- 1 Gold table for all 3 sub-states (ativo/suspenso/cessado), not 3 separate
-- tables -- they are states of the same event type, not distinct semantics
-- (ADR-055 D7 / DESIGN D7).
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}
--   ${metric_id} ${unit} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_gold}.gold_inss_beneficios_mantidos` (
  state_ibge_code STRING,
  especie_nome STRING,
  status_manutencao STRING,
  reference_date DATE,
  metric_id STRING,
  value NUMERIC,
  unit STRING,
  count INT64
)
PARTITION BY reference_date
CLUSTER BY state_ibge_code, status_manutencao;

DELETE FROM `${project}.${bq_dataset_gold}.gold_inss_beneficios_mantidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_gold}.gold_inss_beneficios_mantidos`
SELECT
  state_ibge_code,
  especie_nome,
  status_manutencao,
  reference_date,
  '${metric_id}' AS metric_id,
  SUM(value) AS value,
  '${unit}' AS unit,
  COUNT(*) AS count
FROM `${project}.${bq_dataset_silver}.inss_beneficios_mantidos`
WHERE reference_date = DATE('${reference_period}')
GROUP BY state_ibge_code, especie_nome, status_manutencao, reference_date;
