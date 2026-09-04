-- Gold model: UF x especie x month aggregate of Beneficios Indeferidos.
-- `value` here is a denial COUNT (unit='count'), not a currency sum -- the
-- source has no monetary field for this dataset.
-- Placeholders: ${project} ${bq_dataset_gold} ${bq_dataset_silver}
--   ${metric_id} ${unit} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_gold}.gold_inss_beneficios_indeferidos` (
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

DELETE FROM `${project}.${bq_dataset_gold}.gold_inss_beneficios_indeferidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_gold}.gold_inss_beneficios_indeferidos`
SELECT
  state_ibge_code,
  especie_codigo,
  especie_nome,
  reference_date,
  '${metric_id}' AS metric_id,
  COUNT(*) AS value,
  '${unit}' AS unit,
  COUNT(*) AS count
FROM `${project}.${bq_dataset_silver}.inss_beneficios_indeferidos`
WHERE reference_date = DATE('${reference_period}')
GROUP BY state_ibge_code, especie_codigo, especie_nome, reference_date;
