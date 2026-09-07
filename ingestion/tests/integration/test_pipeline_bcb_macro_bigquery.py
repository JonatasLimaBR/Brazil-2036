from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import replace
from functools import partial
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

    names = {layer: f"citest_{run_id}_bcbmacro_{layer}" for layer in _LAYERS}
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


def test_divida_bruta_pib_pipeline_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, run_id: str, bq, datasets: dict[str, str]
) -> None:
    from google.cloud import storage

    from ingestion.connectors.base import ResourceRef
    from ingestion.connectors.bcb_sgs import (
        BcbSgsSeries,
        build_default_connector,
        parse_to_long_csv,
    )
    from ingestion.pipeline_wide_series import run

    fixture_json = _FIXTURE_DIR / "divida_bruta_pib_sample.json"
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
    series = BcbSgsSeries(series_code=13762, metric_id="divida_bruta_pib")
    connector = build_default_connector(session=None, series=series)
    # discover() would build the real BCB URL; the integration test replaces
    # it with a fixture via file:// (same principle as fiscal_uniao's
    # integration test) so CI never depends on the live BCB API.
    ref = ResourceRef(
        dataset_id="divida_bruta_pib",
        resource_url=f"file://{fixture_json}",
        resource_format="json",
    )

    result = run(
        config,
        connector=_FixedRefConnector(connector, ref),
        storage_client=storage.Client(project=project),
        bq_client=bq,
        parse_to_long_csv=partial(parse_to_long_csv, series_code=series.series_code),
    )

    assert result.status == "ok"
    assert result.gold_rows == 3
    assert result.provenance_rows == 3

    gold = f"`{project}.{datasets['gold']}.gold_divida_bruta_pib`"
    latest = _scalar(
        bq,
        f"SELECT value AS n FROM {gold} WHERE reference_date = DATE('2026-07-01')",
    )
    assert latest is not None and float(latest) == pytest.approx(82.51)

    entity_count = _scalar(bq, f"SELECT COUNT(*) AS n FROM {gold}")
    assert entity_count == 3


class _FixedRefConnector:
    """Wraps a real Connector but returns a fixed ResourceRef from discover()
    -- lets the integration test point at a local fixture without a live
    network call, while still exercising the real download/validate/
    checkpoint methods."""

    def __init__(self, inner, ref: object) -> None:  # type: ignore[no-untyped-def]
        self._inner = inner
        self._ref = ref

    def discover(self):  # type: ignore[no-untyped-def]
        return self._ref

    def metadata(self, ref):  # type: ignore[no-untyped-def]
        return self._inner.metadata(ref)

    def download(self, ref, dest):  # type: ignore[no-untyped-def]
        return self._inner.download(ref, dest)

    def validate(self, local_path):  # type: ignore[no-untyped-def]
        return self._inner.validate(local_path)

    def checkpoint(self, ref, content_sha256):  # type: ignore[no-untyped-def]
        return self._inner.checkpoint(ref, content_sha256)


def _scalar(bq, sql: str):  # type: ignore[no-untyped-def]
    rows = list(bq.query(sql).result())
    return rows[0]["n"] if rows else None


def _base_config():  # type: ignore[no-untyped-def]
    from ingestion.pipeline_wide_series import load_wide_series_config

    return load_wide_series_config(_REPO_INGESTION_ROOT / "config" / "divida_bruta_pib.yaml")
