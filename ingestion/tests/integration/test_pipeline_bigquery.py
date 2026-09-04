from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.integration

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
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

    names = {layer: f"citest_{run_id}_{layer}" for layer in _LAYERS}
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


def test_pipeline_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, run_id: str, bq, datasets: dict[str, str]
) -> None:
    from google.cloud import bigquery, storage

    from ingestion.config import load_config
    from ingestion.connectors.divida_estados import DividaEstadosConnector
    from ingestion.pipeline import run

    fixture_csv = _FIXTURE_DIR / "divida_sample.csv"
    config = replace(
        load_config(),
        gcp_project=project,
        raw_bucket=os.environ.get("RAW_BUCKET", f"{project}-raw"),
        raw_prefix=f"citest/{run_id}",
        contract_path=(_FIXTURE_DIR / "contract_fixture.yaml"),
        resource_url=f"file://{fixture_csv}",
        bq_dataset_control=datasets["control"],
        bq_dataset_bronze=datasets["bronze"],
        bq_dataset_silver=datasets["silver"],
        bq_dataset_gold=datasets["gold"],
    )
    connector = DividaEstadosConnector(
        session=requests.Session(),
        resource_url=config.resource_url,
        dataset_id=config.dataset_id,
        resource_format=config.resource_format,
    )

    result = run(
        config,
        connector=connector,
        storage_client=storage.Client(project=project),
        bq_client=bq,
    )

    assert result.status == "ok"
    assert result.reference_year == 2022
    assert result.gold_rows == 3
    assert result.provenance_rows == 3

    gold = f"`{project}.{datasets['gold']}.{config.gold_table}`"
    prov = f"`{project}.{datasets['gold']}.{config.provenance_table}`"
    registry = f"`{project}.{datasets['control']}.{config.registry_table}`"
    lineage = list(
        bq.query(
            f"SELECT g.state_ibge_code, p.source, p.bronze_object, r.resource_url "
            f"FROM {gold} g "
            f"JOIN {prov} p USING (state_ibge_code, reference_year) "
            f"JOIN {registry} r ON r.dataset_id = @ds "
            "WHERE g.reference_year = 2022",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("ds", "STRING", config.dataset_id)]
            ),
        ).result()
    )
    assert len(lineage) == 3
    assert all(row["source"].startswith("file://") for row in lineage)
    assert all(row["bronze_object"].startswith("gs://") for row in lineage)
    assert all(row["resource_url"] for row in lineage)
