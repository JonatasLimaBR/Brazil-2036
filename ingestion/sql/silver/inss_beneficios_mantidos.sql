-- Silver model: normalize 1 month of Beneficios Mantidos microdata.
-- status_manutencao comes from grupo_situacao in the data itself (ATIVO /
-- SUSPENSO / CESSADO), not from which CKAN resource was fetched -- the source
-- self-describes it (ADR-055 D7). cid10 and dt_nascimento_titular (sensitive:
-- diagnosis code, birth date) are read in Bronze but deliberately dropped here
-- -- they never reach Silver/Gold/the public API.
-- 3 resources share one reference_period (Ativos/Suspensos/Cessados); Bronze
-- keeps all 3 side by side (scoped by _source_uri, see bronze.load_partition).
-- This model always rebuilds the whole period from whatever Bronze currently
-- holds for it (WHERE b._reference_period = ...), so re-running after each of
-- the 3 resources loads converges to the full month once all 3 have run, and
-- is safe/idempotent at every intermediate step in between.
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze}
--   ${bq_dataset_control} ${bronze_table} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_silver}.inss_beneficios_mantidos` (
  state_ibge_code STRING,
  especie_nome STRING,
  status_manutencao STRING,
  reference_date DATE,
  value NUMERIC,
  _row_hash STRING
)
PARTITION BY reference_date
CLUSTER BY state_ibge_code, status_manutencao;

DELETE FROM `${project}.${bq_dataset_silver}.inss_beneficios_mantidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_silver}.inss_beneficios_mantidos`
SELECT
  u.state_ibge_code,
  b.especie_beneficio AS especie_nome,
  UPPER(b.grupo_situacao) AS status_manutencao,
  DATE('${reference_period}') AS reference_date,
  CAST(REPLACE(b.valor_renda_mensal, ',', '.') AS NUMERIC) AS value,
  b._row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}` AS b
JOIN `${project}.${bq_dataset_control}.uf_ibge` AS u
  ON u.state_name_normalized = UPPER(REGEXP_REPLACE(NORMALIZE(b.uf, NFD), r"\pM", ""))
WHERE b._reference_period = DATE('${reference_period}');
