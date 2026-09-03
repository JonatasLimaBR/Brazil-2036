from __future__ import annotations

from dataclasses import dataclass

from ingestion.bigquery_io import BigQueryClient, run_sql

BRONZE_COLUMNS = ("UF", "ANO", "VALOR")
_TECHNICAL_PREFIX = "_"


@dataclass(frozen=True)
class BronzeLoad:
    table: str
    rows_loaded: int
    source_uri: str
    row_hash: str


def _fqtn(project: str, dataset_bronze: str, table: str) -> str:
    return f"`{project}.{dataset_bronze}.{table}`"


def load_ddl(project: str, dataset_bronze: str, table: str) -> str:
    return (
        f"CREATE TABLE IF NOT EXISTS {_fqtn(project, dataset_bronze, table)} "
        "(UF STRING, ANO STRING, VALOR STRING, "
        "_source_uri STRING, _ingested_at TIMESTAMP, _row_hash STRING)"
    )


def load_data_sql(project: str, dataset_bronze: str, table: str, raw_uri: str) -> str:
    return (
        f"LOAD DATA INTO {_fqtn(project, dataset_bronze, table)} "
        "(UF STRING, ANO STRING, VALOR STRING) "
        "FROM FILES (format='CSV', field_delimiter=';', skip_leading_rows=1, "
        f"encoding='UTF-8', uris=['{raw_uri}'])"
    )


def tag_rows_sql(
    project: str, dataset_bronze: str, table: str, source_uri: str, row_hash: str
) -> str:
    return (
        f"UPDATE {_fqtn(project, dataset_bronze, table)} "
        f"SET _source_uri='{source_uri}', _ingested_at=CURRENT_TIMESTAMP(), "
        f"_row_hash='{row_hash}' WHERE _row_hash IS NULL"
    )


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
    fqtn = _fqtn(project, dataset_bronze, table)
    run_sql(client, load_ddl(project, dataset_bronze, table))
    run_sql(client, load_data_sql(project, dataset_bronze, table, raw_uri))
    run_sql(client, tag_rows_sql(project, dataset_bronze, table, source_uri, row_hash))
    counted = run_sql(
        client, f"SELECT COUNT(*) AS n FROM {fqtn} WHERE _row_hash='{row_hash}'"
    )
    return BronzeLoad(
        table=f"{project}.{dataset_bronze}.{table}",
        rows_loaded=int(counted[0]["n"]) if counted else 0,
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
