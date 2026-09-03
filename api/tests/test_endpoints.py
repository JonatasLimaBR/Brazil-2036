from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import Config
from api.main import app, get_config, get_repo
from api.models import MetricResponse, ProvenanceResponse, ProvenanceSummary

_CONFIG = Config(
    gcp_project="test",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
)

_METRIC = MetricResponse(
    metric_id="divida_consolidada",
    state_ibge_code="35",
    value=332702923995.99,
    unit="BRL",
    reference_year=2022,
    reference_date="2022-12-31",
    data_class="observed",
    provenance=ProvenanceSummary(
        source="https://tesouro/x.csv",
        reference_date="2022-12-31",
        trust_status="source_only",
    ),
)

_PROV = ProvenanceResponse(
    metric_id="divida_consolidada",
    state_ibge_code="35",
    reference_year=2022,
    reference_date="2022-12-31",
    gold_object="g",
    silver_transform="s",
    silver_transform_version="v",
    bronze_object="b",
    source_resource_url="https://tesouro/x.csv",
    catalog_dataset_id="divida_consolidada_estados",
    producing_organization="COREM / STN",
    trust_status="source_only",
)


class StubRepo:
    def __init__(self, metric: MetricResponse | None, prov: ProvenanceResponse | None) -> None:
        self._metric = metric
        self._prov = prov

    def latest_metric(self, metric_id: str, state_ibge_code: str) -> MetricResponse | None:
        return self._metric

    def provenance(self, metric_id: str, state_ibge_code: str) -> ProvenanceResponse | None:
        return self._prov


def _client(repo: StubRepo) -> TestClient:
    app.dependency_overrides[get_config] = lambda: _CONFIG
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_metric_ok() -> None:
    resp = _client(StubRepo(_METRIC, _PROV)).get("/v1/metrics/divida_consolidada")
    assert resp.status_code == 200
    body = resp.json()
    assert body["value"] == 332702923995.99
    assert body["reference_year"] == 2022
    assert body["data_class"] == "observed"
    assert body["provenance"]["source"] == "https://tesouro/x.csv"


def test_metric_404() -> None:
    resp = _client(StubRepo(None, None)).get("/v1/metrics/divida_consolidada?state_ibge_code=99")
    assert resp.status_code == 404


def test_provenance_ok_spec007_fields() -> None:
    resp = _client(StubRepo(_METRIC, _PROV)).get("/v1/provenance/divida_consolidada")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "gold_object",
        "silver_transform",
        "silver_transform_version",
        "bronze_object",
        "source_resource_url",
        "catalog_dataset_id",
        "producing_organization",
        "trust_status",
    ):
        assert key in body


def test_provenance_404() -> None:
    resp = _client(StubRepo(_METRIC, None)).get("/v1/provenance/divida_consolidada")
    assert resp.status_code == 404


def test_openapi_has_both_paths() -> None:
    schema = app.openapi()
    assert "/v1/metrics/{metric_id}" in schema["paths"]
    assert "/v1/provenance/{metric_id}" in schema["paths"]
