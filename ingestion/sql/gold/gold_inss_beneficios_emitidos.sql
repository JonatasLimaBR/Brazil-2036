-- Gold model: UF x especie x month aggregate of Beneficios Emitidos.
-- DELETE+INSERT scoped to reference_period (ADR-055 D3): accumulates months.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}
--   ${metric_id} ${unit} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_gold}.gold_inss_beneficios_emitidos` (
  state_ibge_code STRING,
  especie_codigo STRING,
  especie_nome STRING,
  reference_date DATE,
  metric_id STRING,
  value NUMERIC,
  unit STRING,
  count INT64
)
PARTITION BY reference_date
CLUSTER BY state_ibge_code, especie_codigo;

DELETE FROM `${project}.${bq_dataset_gold}.gold_inss_beneficios_emitidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_gold}.gold_inss_beneficios_emitidos`
SELECT
  state_ibge_code,
  especie_codigo,
  especie_nome,
  reference_date,
  '${metric_id}' AS metric_id,
  SUM(value) AS value,
  '${unit}' AS unit,
  COUNT(*) AS count
FROM `${project}.${bq_dataset_silver}.inss_beneficios_emitidos`
WHERE reference_date = DATE('${reference_period}')
GROUP BY state_ibge_code, especie_codigo, especie_nome, reference_date;
