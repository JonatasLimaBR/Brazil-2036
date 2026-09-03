from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

REGISTRY_DDL = (
    "dataset_id STRING, resource_url STRING, source_url STRING, "
    "resource_format STRING, organization STRING, license STRING, "
    "update_frequency STRING, br2036_domain STRING, br2036_module STRING, "
    "active BOOL, updated_at TIMESTAMP"
)


def load_uf_ibge_rows(csv_path: str | Path) -> list[dict[str, str]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def ensure_uf_ibge(
    client: BigQueryClient,
    *,
    project: str,
    dataset_control: str,
    table: str,
    csv_path: str | Path,
) -> int:
    rows = load_uf_ibge_rows(csv_path)
    fq_name = f"`{project}.{dataset_control}.{table}`"
    structs = ",\n".join(
        f"STRUCT({sql_literal(r['uf'])} AS uf, "
        f"{sql_literal(r['state_ibge_code'])} AS state_ibge_code, "
        f"{sql_literal(r['state_name'])} AS state_name)"
        for r in rows
    )
    run_sql(
        client,
        f"CREATE OR REPLACE TABLE {fq_name} AS SELECT * FROM UNNEST([{structs}])",
    )
    return len(rows)


def upsert_dataset_registry(
    client: BigQueryClient,
    *,
    project: str,
    dataset_control: str,
    table: str,
    entry: Mapping[str, str],
) -> None:
    fq_name = f"`{project}.{dataset_control}.{table}`"
    run_sql(client, f"CREATE TABLE IF NOT EXISTS {fq_name} ({REGISTRY_DDL})")
    run_sql(
        client,
        f"DELETE FROM {fq_name} WHERE dataset_id = {sql_literal(entry['dataset_id'])}",
    )
    columns = (
        "dataset_id, resource_url, source_url, resource_format, organization, "
        "license, update_frequency, br2036_domain, br2036_module, active, updated_at"
    )
    values = ", ".join(
        [
            sql_literal(entry["dataset_id"]),
            sql_literal(entry["resource_url"]),
            sql_literal(entry.get("source_url", "")),
            sql_literal(entry["resource_format"]),
            sql_literal(entry["organization"]),
            sql_literal(entry["license"]),
            sql_literal(entry["update_frequency"]),
            sql_literal(entry["br2036_domain"]),
            sql_literal(entry["br2036_module"]),
            "TRUE",
            "CURRENT_TIMESTAMP()",
        ]
    )
    run_sql(client, f"INSERT INTO {fq_name} ({columns}) VALUES ({values})")
