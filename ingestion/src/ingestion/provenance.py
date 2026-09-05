from __future__ import annotations

import datetime as dt

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

_ASSUMPTIONS = (
    "['value reported by the producing organization under the PAF', "
    "'reference_date set to the fiscal year end (December 31)']"
)

_SCHEMA = (
    "metric_id STRING, state_ibge_code STRING, reference_year INT64, "
    "reference_date DATE, value NUMERIC, unit STRING, source STRING, "
    "gold_object STRING, silver_transform STRING, silver_transform_version STRING, "
    "bronze_object STRING, catalog_dataset_id STRING, producing_organization STRING, "
    "model STRING, model_version STRING, scenario STRING, confidence FLOAT64, "
    "assumptions ARRAY<STRING>, run_id STRING, created_at TIMESTAMP"
)


def write_from_gold(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    gold_table: str,
    provenance_table: str,
    metric_id: str,
    reference_date: dt.date | None,
    source_url: str,
    silver_transform: str,
    silver_transform_version: str,
    bronze_object: str,
    catalog_dataset_id: str,
    producing_organization: str,
    run_id: str,
) -> int:
    # DELETE+INSERT scoped by (metric_id, reference_date), not CREATE OR REPLACE:
    # metric_provenance is shared by every metric this project produces. A full-table
    # replace here would erase every other metric's (and every other period's) rows.
    #
    # reference_date=None widens the scope to the whole metric_id (no date
    # filter): for a source that republishes its entire history in one file
    # every run (e.g. the Tesouro Nacional wide monthly series), there is no
    # single period to scope by -- the run recomputes every period at once, so
    # provenance for that metric_id is replaced atomically in one statement.
    gold = f"`{project}.{dataset_gold}.{gold_table}`"
    prov = f"`{project}.{dataset_gold}.{provenance_table}`"
    gold_object = f"{project}.{dataset_gold}.{gold_table}"
    metric_lit = sql_literal(metric_id)
    if reference_date is None:
        scope = f"metric_id = {metric_lit}"
    else:
        date_lit = sql_literal(reference_date.isoformat())
        scope = f"metric_id = {metric_lit} AND reference_date = DATE({date_lit})"

    run_sql(client, f"CREATE TABLE IF NOT EXISTS {prov} ({_SCHEMA})")
    run_sql(client, f"DELETE FROM {prov} WHERE {scope}")
    run_sql(
        client,
        f"INSERT INTO {prov} SELECT "
        "metric_id, state_ibge_code, EXTRACT(YEAR FROM reference_date) AS reference_year, "
        "reference_date, value, unit, "
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
        f"FROM {gold} WHERE {scope}",
    )
    counted = run_sql(client, f"SELECT COUNT(*) AS n FROM {prov} WHERE {scope}")
    return int(counted[0]["n"]) if counted else 0
