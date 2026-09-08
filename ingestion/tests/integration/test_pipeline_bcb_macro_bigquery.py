from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_REPO_INGESTION_ROOT = Path(__file__).resolve().parents[2]
_LAYERS = ("control", "bronze", "silver", "gold")


@dataclass(frozen=True)
class _Case:
    dataset_id: str
    series_code: int
    gold_table: str
    expected_reference_date: str
    expected_value: float


# One real, confirmed value per series (MACRO_TWIN_EXPANSION DESIGN 0.1 /
# DEBTLAB_SIMULATOR DESIGN 0.1) -- pib_mensal's expected value is in reais
# (fixture publishes R$ millions, Silver converts x1e6, same as production).
_CASES = (
    _Case("pib_mensal", 4380, "gold_pib_mensal", "2026-07-01", 1167869000000.0),
    _Case("divida_bruta_pib", 13762, "gold_divida_bruta_pib", "2026-07-01", 82.51),
    _Case("ipca_mensal", 433, "gold_ipca_mensal", "2026-07-01", 0.07),
    _Case("selic_mensal", 4390, "gold_selic_mensal", "2026-09-01", 0.21),
    _Case("cambio_usd_brl", 3695, "gold_cambio_usd_brl", "2026-08-01", 5.1810),
)


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


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.dataset_id)
def test_bcb_series_pipeline_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, run_id: str, bq, datasets: dict[str, str], case: _Case
) -> None:
    from google.cloud import storage

    from ingestion.connectors.base import ResourceRef
    from ingestion.connectors.bcb_sgs import (
        BcbSgsSeries,
        build_default_connector,
        parse_to_long_csv,
    )
    from ingestion.pipeline_wide_series import run

    fixture_json = _FIXTURE_DIR / f"{case.dataset_id}_sample.json"
    config = replace(
        _base_config(case.dataset_id),
        gcp_project=project,
        raw_bucket=os.environ.get("RAW_BUCKET", f"{project}-raw"),
        raw_prefix=f"citest/{run_id}",
        bq_dataset_control=datasets["control"],
        bq_dataset_bronze=datasets["bronze"],
        bq_dataset_silver=datasets["silver"],
        bq_dataset_gold=datasets["gold"],
    )
    series = BcbSgsSeries(series_code=case.series_code, metric_id=case.dataset_id)
    connector = build_default_connector(session=None, series=series)
    # discover() would build the real BCB URL; the integration test replaces
    # it with a fixture via file:// (same principle as fiscal_uniao's
    # integration test) so CI never depends on the live BCB API.
    ref = ResourceRef(
        dataset_id=case.dataset_id,
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

    gold = f"`{project}.{datasets['gold']}.{case.gold_table}`"
    date_lit = case.expected_reference_date
    latest = _scalar(bq, f"SELECT value AS n FROM {gold} WHERE reference_date = DATE('{date_lit}')")
    assert latest is not None and float(latest) == pytest.approx(case.expected_value)

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


def _base_config(dataset_id: str):  # type: ignore[no-untyped-def]
    from ingestion.pipeline_wide_series import load_wide_series_config

    return load_wide_series_config(_REPO_INGESTION_ROOT / "config" / f"{dataset_id}.yaml")
