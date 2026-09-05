from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_REPO_INGESTION_ROOT = Path(__file__).resolve().parents[2]
_LAYERS = ("control", "bronze", "silver", "gold")


@pytest.fixture(scope="module")
def project() -> str:
    value = os.environ.get("GCP_PROJECT")
    if not value:
        pytest.skip("GCP_PROJECT not set; integration test needs a real GCP project")
    return value


@pytest.fixture(scope="module")
def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or uuid.uuid4().hex[:12]


@pytest.fixture(scope="module")
def bq(project: str):  # type: ignore[no-untyped-def]
    from google.cloud import bigquery

    return bigquery.Client(project=project)


@pytest.fixture(scope="module")
def datasets(bq, project: str, run_id: str) -> Iterator[dict[str, str]]:  # type: ignore[no-untyped-def]
    from google.cloud import bigquery

    names = {layer: f"citest_{run_id}_fiscal_{layer}" for layer in _LAYERS}
    location = os.environ.get("BQ_LOCATION", "southamerica-east1")
    for name in names.values():
        dataset = bigquery.Dataset(f"{project}.{name}")
        dataset.location = location
        dataset.default_table_expiration_ms = 3600 * 1000
        bq.create_dataset(dataset, exists_ok=True)
    try:
        yield names
    finally:
        for name in names.values():
            bq.delete_dataset(f"{project}.{name}", delete_contents=True, not_found_ok=True)


def test_fiscal_uniao_pipeline_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, run_id: str, bq, datasets: dict[str, str]
) -> None:
    from google.cloud import storage

    from ingestion.ckan import CkanResource
    from ingestion.connectors.fiscal_uniao import FiscalUniaoConnector, parse_to_long_csv
    from ingestion.pipeline_wide_series import run

    fixture_xlsx = _FIXTURE_DIR / "fiscal_uniao_sample.xlsx"
    config = replace(
        _base_config(),
        gcp_project=project,
        raw_bucket=os.environ.get("RAW_BUCKET", f"{project}-raw"),
        raw_prefix=f"citest/{run_id}",
        bq_dataset_control=datasets["control"],
        bq_dataset_bronze=datasets["bronze"],
        bq_dataset_silver=datasets["silver"],
        bq_dataset_gold=datasets["gold"],
    )
    resource = CkanResource(
        resource_id="fixture",
        name="Resultado do Tesouro Nacional - Série Histórica - Mensal (fixture)",
        format="XLSX",
        url=f"file://{fixture_xlsx}",
        last_modified=None,
    )
    connector = FiscalUniaoConnector(session=None, resource=resource)

    result = run(
        config,
        connector=connector,
        storage_client=storage.Client(project=project),
        bq_client=bq,
        parse_to_long_csv=parse_to_long_csv,
    )

    assert result.status == "ok"
    # 2 fixture months x 3 metrics = 6 Gold rows, including a real negative
    # fiscal_primario month -- proves D10 (allow_negative) works against real
    # BigQuery, not just a fake client.
    assert result.gold_rows == 6
    assert result.provenance_rows == 6

    gold = f"`{project}.{datasets['gold']}.gold_fiscal_uniao`"
    prov = f"`{project}.{datasets['gold']}.metric_provenance`"
    registry_table = f"`{project}.{datasets['control']}.dataset_registry`"

    negative_primario = _scalar(
        bq,
        f"SELECT value AS n FROM {gold} "
        "WHERE metric_id = 'fiscal_primario' AND reference_date = DATE('2026-05-01')",
    )
    assert negative_primario is not None and negative_primario < 0

    lineage = list(
        bq.query(
            f"SELECT p.source, p.bronze_object, r.resource_url "
            f"FROM {prov} p "
            f"JOIN {registry_table} r ON r.dataset_id = p.catalog_dataset_id "
            "WHERE p.metric_id = 'fiscal_primario'"
        ).result()
    )
    assert len(lineage) == 2
    assert all(row["source"].startswith("file://") for row in lineage)
    assert all(row["bronze_object"].startswith("gs://") for row in lineage)
    assert all(row["resource_url"] for row in lineage)


def _scalar(bq, sql: str):  # type: ignore[no-untyped-def]
    rows = list(bq.query(sql).result())
    return rows[0]["n"] if rows else None


def _base_config():  # type: ignore[no-untyped-def]
    from ingestion.pipeline_wide_series import load_wide_series_config

    return load_wide_series_config(_REPO_INGESTION_ROOT / "config" / "fiscal_uniao.yaml")
