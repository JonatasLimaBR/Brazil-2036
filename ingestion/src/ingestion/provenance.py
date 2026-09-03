from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingestion.bigquery_io import BigQueryClient, insert_rows, run_sql

PROVENANCE_DDL = (
    "metric_id STRING, state_ibge_code STRING, reference_year INT64, "
    "reference_date DATE, value NUMERIC, unit STRING, source STRING, "
    "gold_object STRING, silver_transform STRING, silver_transform_version STRING, "
    "bronze_object STRING, catalog_dataset_id STRING, producing_organization STRING, "
    "model STRING, model_version STRING, scenario STRING, confidence FLOAT64, "
    "assumptions ARRAY<STRING>, run_id STRING, created_at TIMESTAMP"
)


def build_rows(
    gold_rows: Sequence[dict[str, Any]],
    *,
    source_url: str,
    gold_object: str,
    silver_transform: str,
    silver_transform_version: str,
    bronze_object: str,
    catalog_dataset_id: str,
    producing_organization: str,
    run_id: str,
    created_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in gold_rows:
        rows.append(
            {
                "metric_id": row["metric_id"],
                "state_ibge_code": row["state_ibge_code"],
                "reference_year": row["reference_year"],
                "reference_date": str(row["reference_date"]),
                "value": str(row["value"]),
                "unit": row["unit"],
                "source": source_url,
                "gold_object": gold_object,
                "silver_transform": silver_transform,
                "silver_transform_version": silver_transform_version,
                "bronze_object": bronze_object,
                "catalog_dataset_id": catalog_dataset_id,
                "producing_organization": producing_organization,
                "model": "none",
                "model_version": "n/a",
                "scenario": "observed",
                "confidence": 1.0,
                "assumptions": [
                    "value reported by the producing organization under the PAF",
                    "reference_date set to the fiscal year end (December 31)",
                ],
                "run_id": run_id,
                "created_at": created_at,
            }
        )
    return rows


def write(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    table: str,
    rows: Sequence[dict[str, Any]],
    reference_year: int,
) -> int:
    fq_name = f"{project}.{dataset_gold}.{table}"
    run_sql(client, f"CREATE TABLE IF NOT EXISTS `{fq_name}` ({PROVENANCE_DDL})")
    run_sql(client, f"DELETE FROM `{fq_name}` WHERE reference_year = {reference_year}")
    insert_rows(client, fq_name, rows)
    return len(rows)
