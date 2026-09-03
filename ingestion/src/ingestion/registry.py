from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Mapping
from pathlib import Path

from ingestion.bigquery_io import BigQueryClient, insert_rows, run_sql

UF_IBGE_DDL = "uf STRING, state_ibge_code STRING, state_name STRING"

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
    fq_name = f"{project}.{dataset_control}.{table}"
    run_sql(client, f"CREATE TABLE IF NOT EXISTS `{fq_name}` ({UF_IBGE_DDL})")
    run_sql(client, f"TRUNCATE TABLE `{fq_name}`")
    insert_rows(client, fq_name, rows)
    return len(rows)


def upsert_dataset_registry(
    client: BigQueryClient,
    *,
    project: str,
    dataset_control: str,
    table: str,
    entry: Mapping[str, str],
) -> None:
    fq_name = f"{project}.{dataset_control}.{table}"
    run_sql(client, f"CREATE TABLE IF NOT EXISTS `{fq_name}` ({REGISTRY_DDL})")
    run_sql(
        client,
        f"DELETE FROM `{fq_name}` WHERE dataset_id = '{entry['dataset_id']}'",
    )
    insert_rows(
        client,
        fq_name,
        [
            {
                "dataset_id": entry["dataset_id"],
                "resource_url": entry["resource_url"],
                "source_url": entry.get("source_url", ""),
                "resource_format": entry["resource_format"],
                "organization": entry["organization"],
                "license": entry["license"],
                "update_frequency": entry["update_frequency"],
                "br2036_domain": entry["br2036_domain"],
                "br2036_module": entry["br2036_module"],
                "active": True,
                "updated_at": dt.datetime.now(dt.UTC).isoformat(),
            }
        ],
    )
