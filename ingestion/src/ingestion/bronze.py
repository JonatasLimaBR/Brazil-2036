from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from ingestion.bigquery_io import BigQueryClient, run_sql, scalar, sql_literal

BRONZE_COLUMNS = ("UF", "ANO", "VALOR")
_TECHNICAL_PREFIX = "_"


@dataclass(frozen=True)
class BronzeLoad:
    table: str
    rows_loaded: int
    source_uri: str
    row_hash: str


def _fqtn(project: str, dataset: str, table: str) -> str:
    return f"`{project}.{dataset}.{table}`"


def load(
    client: BigQueryClient,
    *,
    project: str,
    dataset_bronze: str,
    table: str,
    raw_uri: str,
    source_uri: str,
    row_hash: str,
) -> BronzeLoad:
    staging = _fqtn(project, dataset_bronze, f"{table}_stg")
    target = _fqtn(project, dataset_bronze, table)

    run_sql(
        client,
        f"LOAD DATA OVERWRITE {staging} (UF STRING, ANO STRING, VALOR STRING) "
        "FROM FILES (format='CSV', field_delimiter=';', skip_leading_rows=1, "
        f"encoding='UTF-8', uris=['{raw_uri}'])",
    )
    run_sql(
        client,
        f"CREATE OR REPLACE TABLE {target} AS SELECT UF, ANO, VALOR, "
        f"{sql_literal(source_uri)} AS _source_uri, "
        "CURRENT_TIMESTAMP() AS _ingested_at, "
        f"{sql_literal(row_hash)} AS _row_hash FROM {staging}",
    )
    counted = scalar(client, f"SELECT COUNT(*) FROM {target}")
    return BronzeLoad(
        table=f"{project}.{dataset_bronze}.{table}",
        rows_loaded=int(counted or 0),
        source_uri=source_uri,
        row_hash=row_hash,
    )


def load_partition(
    client: BigQueryClient,
    *,
    project: str,
    dataset_bronze: str,
    table: str,
    columns: Sequence[str],
    field_delimiter: str,
    reference_period: dt.date,
    raw_uri: str,
    source_uri: str,
    row_hash: str,
) -> BronzeLoad:
    # DELETE+INSERT scoped by (_reference_period, _source_uri), not CREATE OR
    # REPLACE: this table accumulates one month per resource across a
    # resumable backfill, so a full-table replace would erase every month
    # already loaded. Scoping by _source_uri too (not period alone) matters
    # for datasets that publish more than one resource per month (e.g. INSS
    # Mantidos: Ativos/Suspensos/Cessados) -- otherwise loading the second
    # resource for a month would delete the first resource's rows for that
    # same month before inserting its own.
    staging = _fqtn(project, dataset_bronze, f"{table}_stg")
    target = _fqtn(project, dataset_bronze, table)
    col_defs = ", ".join(f"{c} STRING" for c in columns)
    period_lit = sql_literal(reference_period.isoformat())
    source_lit = sql_literal(source_uri)
    scope = f"_reference_period = DATE({period_lit}) AND _source_uri = {source_lit}"

    run_sql(
        client,
        f"CREATE TABLE IF NOT EXISTS {target} ({col_defs}, "
        "_source_uri STRING, _ingested_at TIMESTAMP, _row_hash STRING, "
        "_reference_period DATE) PARTITION BY _reference_period",
    )
    run_sql(
        client,
        f"LOAD DATA OVERWRITE {staging} ({col_defs}) "
        f"FROM FILES (format='CSV', field_delimiter='{field_delimiter}', "
        f"skip_leading_rows=1, encoding='UTF-8', uris=['{raw_uri}'])",
    )
    run_sql(client, f"DELETE FROM {target} WHERE {scope}")
    select_cols = ", ".join(columns)
    run_sql(
        client,
        f"INSERT INTO {target} SELECT {select_cols}, "
        f"{source_lit} AS _source_uri, "
        "CURRENT_TIMESTAMP() AS _ingested_at, "
        f"{sql_literal(row_hash)} AS _row_hash, "
        f"DATE({period_lit}) AS _reference_period "
        f"FROM {staging}",
    )
    counted = scalar(client, f"SELECT COUNT(*) FROM {target} WHERE {scope}")
    return BronzeLoad(
        table=f"{project}.{dataset_bronze}.{table}",
        rows_loaded=int(counted or 0),
        source_uri=source_uri,
        row_hash=row_hash,
    )


def source_columns(
    client: BigQueryClient, *, project: str, dataset_bronze: str, table: str
) -> list[str]:
    rows = run_sql(
        client,
        "SELECT column_name FROM "
        f"`{project}.{dataset_bronze}`.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE table_name = '{table}' ORDER BY ordinal_position",
    )
    return [
        r["column_name"] for r in rows if not str(r["column_name"]).startswith(_TECHNICAL_PREFIX)
    ]
