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
        f"{sql_literal(r['state_name'])} AS state_name, "
        f"{sql_literal(r['state_name_normalized'])} AS state_name_normalized)"
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
    # MERGE, not CREATE OR REPLACE: the table is shared across every dataset this
    # project ingests. A full-table replace here would silently erase every other
    # dataset's registry row (e.g. running this for INSS would delete the debt
    # dataset's row) the first time a second dataset called this function.
    fq_name = f"`{project}.{dataset_control}.{table}`"
    run_sql(
        client,
        f"CREATE TABLE IF NOT EXISTS {fq_name} ("
        "dataset_id STRING, resource_url STRING, source_url STRING, "
        "resource_format STRING, organization STRING, license STRING, "
        "update_frequency STRING, br2036_domain STRING, br2036_module STRING, "
        "active BOOL, updated_at TIMESTAMP)",
    )
    selected = ", ".join(
        f"{sql_literal(entry.get(field, ''))} AS {field}" for field in _REGISTRY_FIELDS
    )
    update_set = ", ".join(
        f"{field} = S.{field}" for field in _REGISTRY_FIELDS if field != "dataset_id"
    )
    insert_cols = ", ".join(_REGISTRY_FIELDS)
    insert_vals = ", ".join(f"S.{field}" for field in _REGISTRY_FIELDS)
    run_sql(
        client,
        f"MERGE {fq_name} T USING (SELECT {selected}) S "
        "ON T.dataset_id = S.dataset_id "
        f"WHEN MATCHED THEN UPDATE SET {update_set}, active = TRUE, "
        "updated_at = CURRENT_TIMESTAMP() "
        f"WHEN NOT MATCHED THEN INSERT ({insert_cols}, active, updated_at) "
        f"VALUES ({insert_vals}, TRUE, CURRENT_TIMESTAMP())",
    )
