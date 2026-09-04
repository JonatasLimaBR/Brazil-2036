-- Silver model: normalize 1 month of Beneficios Indeferidos microdata.
-- Source `uf` here is accented, mixed-case (e.g. "Alagoas"), unlike Emitidos/
-- Mantidos (unaccented uppercase) -- the join strips accents (NFD decompose +
-- drop combining marks) so this is not a silent join miss. dt_nascimento
-- (birth date) is read in Bronze but deliberately dropped here.
-- Indeferidos has no monetary field in the source -- it is a denial-count
-- metric (Gold aggregates via COUNT(*), not SUM).
-- Placeholders: ${project} ${bq_dataset_silver} ${bq_dataset_bronze}
--   ${bq_dataset_control} ${bronze_table} ${reference_period}

CREATE TABLE IF NOT EXISTS `${project}.${bq_dataset_silver}.inss_beneficios_indeferidos` (
  state_ibge_code STRING,
  especie_codigo STRING,
  especie_nome STRING,
  reference_date DATE,
  _row_hash STRING
)
PARTITION BY reference_date
CLUSTER BY state_ibge_code, especie_codigo;

DELETE FROM `${project}.${bq_dataset_silver}.inss_beneficios_indeferidos`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_silver}.inss_beneficios_indeferidos`
SELECT
  u.state_ibge_code,
  b.especie_codigo,
  b.especie_nome,
  DATE('${reference_period}') AS reference_date,
  b._row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}` AS b
JOIN `${project}.${bq_dataset_control}.uf_ibge` AS u
  ON u.state_name_normalized = UPPER(REGEXP_REPLACE(NORMALIZE(b.uf, NFD), r"\pM", ""))
WHERE b._reference_period = DATE('${reference_period}');
