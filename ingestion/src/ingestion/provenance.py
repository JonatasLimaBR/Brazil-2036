from __future__ import annotations

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

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

    run_sql(
        client,
        f"CREATE OR REPLACE TABLE {prov} AS SELECT "
        "metric_id, state_ibge_code, reference_year, reference_date, value, unit, "
        f"{sql_literal(source_url)} AS source, "
        f"{sql_literal(gold_object)} AS gold_object, "
        f"{sql_literal(silver_transform)} AS silver_transform, "
        f"{sql_literal(silver_transform_version)} AS silver_transform_version, "
        f"{sql_literal(bronze_object)} AS bronze_object, "
        f"{sql_literal(catalog_dataset_id)} AS catalog_dataset_id, "
        f"{sql_literal(producing_organization)} AS producing_organization, "
        "'none' AS model, 'n/a' AS model_version, 'observed' AS scenario, "
        f"1.0 AS confidence, {_ASSUMPTIONS} AS assumptions, "
        f"{sql_literal(run_id)} AS run_id, CURRENT_TIMESTAMP() AS created_at "
        f"FROM {gold} WHERE reference_year = {reference_year}",
    )
    counted = run_sql(
        client,
        f"SELECT COUNT(*) AS n FROM {prov} WHERE reference_year = {reference_year}",
    )
    return int(counted[0]["n"]) if counted else 0
