from __future__ import annotations

import datetime as dt
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

    names = {layer: f"citest_{run_id}_inss_{layer}" for layer in _LAYERS}
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


def test_inss_emitidos_pipeline_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, run_id: str, bq, datasets: dict[str, str]
) -> None:
    from google.cloud import storage

    from ingestion import registry
    from ingestion.ckan import CkanResource
    from ingestion.connectors.inss_emitidos import InssEmitidosConnector
    from ingestion.pipeline_incremental import run

    registry.ensure_uf_ibge(
        bq,
        project=project,
        dataset_control=datasets["control"],
        table="uf_ibge",
        csv_path=_REPO_INGESTION_ROOT / "reference" / "uf_ibge.csv",
    )

    fixture_csv = _FIXTURE_DIR / "inss_emitidos_sample.csv"
    config = replace(
        _base_config(),
        gcp_project=project,
        raw_bucket=os.environ.get("RAW_BUCKET", f"{project}-raw"),
        raw_prefix=f"citest/{run_id}",
        contract_path=(_FIXTURE_DIR / "inss_emitidos_contract_fixture.yaml"),
        bq_dataset_control=datasets["control"],
        bq_dataset_bronze=datasets["bronze"],
        bq_dataset_silver=datasets["silver"],
        bq_dataset_gold=datasets["gold"],
    )
    resource = CkanResource(
        resource_id="fixture",
        name="Beneficios Emitidos junho 2026 (fixture)",
        format="CSV",
        url=f"file://{fixture_csv}",
        last_modified=None,
    )
    connector = InssEmitidosConnector(session=None, resource=resource)  # type: ignore[arg-type]

    result = run(
        config,
        connector=connector,
        storage_client=storage.Client(project=project),
        bq_client=bq,
        reference_period=dt.date(2026, 6, 1),
    )

    assert result.status == "ok"
    assert result.bronze_rows == 5
    # Grain is UF x especie x month, not just UF: the 5 fixture rows span 3
    # states but 5 distinct (state, especie) pairs, so Gold -- and provenance,
    # 1 row per Gold row -- has 5 rows, not 3.
    assert result.provenance_rows == 5

    gold = f"`{project}.{datasets['gold']}.gold_inss_beneficios_emitidos`"
    prov = f"`{project}.{datasets['gold']}.metric_provenance`"
    registry_table = f"`{project}.{datasets['control']}.dataset_registry`"

    gold_count = _scalar(
        bq, f"SELECT COUNT(*) AS n FROM {gold} WHERE reference_date = DATE('2026-06-01')"
    )
    assert gold_count == 5

    # Join provenance -> registry only (not provenance -> gold): Gold's grain
    # includes especie, which provenance does not carry as its own column, so
    # a gold-to-provenance join on (state, date, metric) alone would fan out
    # for any state with more than one especie in the fixture.
    lineage = list(
        bq.query(
            f"SELECT p.source, p.bronze_object, r.resource_url "
            f"FROM {prov} p "
            f"JOIN {registry_table} r ON r.dataset_id = p.catalog_dataset_id "
            "WHERE p.reference_date = DATE('2026-06-01') "
            "AND p.metric_id = 'inss_beneficios_emitidos'"
        ).result()
    )
    assert len(lineage) == 5
    assert all(row["source"].startswith("file://") for row in lineage)
    assert all(row["bronze_object"].startswith("gs://") for row in lineage)
    assert all(row["resource_url"] for row in lineage)


def _scalar(bq, sql: str):  # type: ignore[no-untyped-def]
    rows = list(bq.query(sql).result())
    return rows[0]["n"] if rows else None


def _base_config():  # type: ignore[no-untyped-def]
    from ingestion.pipeline_incremental import load_incremental_config

    return load_incremental_config(_REPO_INGESTION_ROOT / "config" / "inss_emitidos.yaml")
