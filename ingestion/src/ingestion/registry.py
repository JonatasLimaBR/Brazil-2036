from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

_REGISTRY_FIELDS = (
    "dataset_id",
    "resource_url",
    "source_url",
    "resource_format",
    "organization",
    "license",
    "update_frequency",
    "br2036_domain",
    "br2036_module",
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
    selected = ", ".join(
        f"{sql_literal(entry.get(field, ''))} AS {field}" for field in _REGISTRY_FIELDS
    )
    run_sql(
        client,
        f"CREATE OR REPLACE TABLE {fq_name} AS SELECT {selected}, "
        "TRUE AS active, CURRENT_TIMESTAMP() AS updated_at",
    )
