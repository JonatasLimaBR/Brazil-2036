-- Silver model: normalize 1 month of Beneficios Emitidos microdata.
-- UF arrives unaccented/uppercase already (confirmed against a real file), but
-- the join still strips accents defensively (NFD decompose + drop combining
-- marks) so a future source change in casing/accents does not silently lose rows.
-- DELETE+INSERT scoped to reference_period (ADR-055 D3): this table accumulates
-- one month per backfill resource, so CREATE OR REPLACE would erase prior months.
-- The INSERT's SELECT is scoped to the same period (WHERE b._reference_period =
-- ...): Bronze itself accumulates every month ever loaded, so without this
-- filter every run would re-insert the entire history, not just this month.
-- Placeholders substituted by pipeline_incremental.run():
--   ${project} ${bq_dataset_silver} ${bq_dataset_bronze} ${bq_dataset_control}
--   ${bronze_table} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_silver}.inss_beneficios_emitidos` (
  state_ibge_code STRING,
  especie_codigo STRING,
  especie_nome STRING,
  reference_date DATE,
  value NUMERIC,
  _row_hash STRING
)
PARTITION BY reference_date
CLUSTER BY state_ibge_code, especie_codigo;

DELETE FROM `${project}.${bq_dataset_silver}.inss_beneficios_emitidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_silver}.inss_beneficios_emitidos`
SELECT
  u.state_ibge_code,
  b.especie AS especie_codigo,
  b.especie_codigo_nome AS especie_nome,
  DATE('${reference_period}') AS reference_date,
  CAST(REPLACE(b.vl_liquido, ',', '.') AS NUMERIC) AS value,
  b._row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}` AS b
JOIN `${project}.${bq_dataset_control}.uf_ibge` AS u
  ON u.state_name_normalized = UPPER(REGEXP_REPLACE(NORMALIZE(b.uf, NFD), r"\pM", ""))
WHERE b._reference_period = DATE('${reference_period}');
