from __future__ import annotations

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

PROVENANCE_DDL = (
    "metric_id STRING, state_ibge_code STRING, reference_year INT64, "
    "reference_date DATE, value NUMERIC, unit STRING, source STRING, "
    "gold_object STRING, silver_transform STRING, silver_transform_version STRING, "
    "bronze_object STRING, catalog_dataset_id STRING, producing_organization STRING, "
    "model STRING, model_version STRING, scenario STRING, confidence FLOAT64, "
    "assumptions ARRAY<STRING>, run_id STRING, created_at TIMESTAMP"
)

_ASSUMPTIONS = (
    "['value reported by the producing organization under the PAF', "
    "'reference_date set to the fiscal year end (December 31)']"
)


def write_from_gold(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    gold_table: str,
    provenance_table: str,
    reference_year: int,
    source_url: str,
    silver_transform: str,
    silver_transform_version: str,
    bronze_object: str,
    catalog_dataset_id: str,
    producing_organization: str,
    run_id: str,
) -> int:
    gold = f"`{project}.{dataset_gold}.{gold_table}`"
    prov = f"`{project}.{dataset_gold}.{provenance_table}`"
    gold_object = f"{project}.{dataset_gold}.{gold_table}"

    run_sql(client, f"CREATE TABLE IF NOT EXISTS {prov} ({PROVENANCE_DDL})")
    run_sql(client, f"DELETE FROM {prov} WHERE reference_year = {reference_year}")
    run_sql(
        client,
        f"INSERT INTO {prov} (metric_id, state_ibge_code, reference_year, "
        "reference_date, value, unit, source, gold_object, silver_transform, "
        "silver_transform_version, bronze_object, catalog_dataset_id, "
        "producing_organization, model, model_version, scenario, confidence, "
        "assumptions, run_id, created_at) "
        "SELECT metric_id, state_ibge_code, reference_year, reference_date, value, "
        f"unit, {sql_literal(source_url)}, {sql_literal(gold_object)}, "
        f"{sql_literal(silver_transform)}, {sql_literal(silver_transform_version)}, "
        f"{sql_literal(bronze_object)}, {sql_literal(catalog_dataset_id)}, "
        f"{sql_literal(producing_organization)}, 'none', 'n/a', 'observed', 1.0, "
        f"{_ASSUMPTIONS}, {sql_literal(run_id)}, CURRENT_TIMESTAMP() "
        f"FROM {gold} WHERE reference_year = {reference_year}",
    )
    counted = run_sql(
        client,
        f"SELECT COUNT(*) AS n FROM {prov} WHERE reference_year = {reference_year}",
    )
    return int(counted[0]["n"]) if counted else 0
