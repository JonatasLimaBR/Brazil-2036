from __future__ import annotations

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
        r["column_name"]
        for r in rows
        if not str(r["column_name"]).startswith(_TECHNICAL_PREFIX)
    ]
