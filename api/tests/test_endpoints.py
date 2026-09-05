from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import Config
from api.main import app, get_config, get_repo
from api.models import (
    MetricResponse,
    NationalMetricResponse,
    ProvenanceResponse,
    ProvenanceSummary,
)

_CONFIG = Config(
    gcp_project="test",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
    metric_tables={
        "inss_beneficios_emitidos": "gold_inss_beneficios_emitidos",
        "fiscal_receita": "gold_fiscal_uniao",
        "fiscal_despesa": "gold_fiscal_uniao",
        "fiscal_primario": "gold_fiscal_uniao",
    },
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


_NATIONAL = NationalMetricResponse(
    metric_id="inss_beneficios_emitidos",
    value=123456.78,
    unit="BRL",
    reference_date="2026-06-01",
    data_class="observed",
    provenance=ProvenanceSummary(
        source="https://s3/inss_emitidos_202606.zip",
        reference_date="2026-06-01",
        trust_status="source_only",
    ),
)


class StubRepo:
    def __init__(
        self,
        metric: MetricResponse | None,
        prov: ProvenanceResponse | None,
        national: NationalMetricResponse | None = None,
    ) -> None:
        self._metric = metric
        self._prov = prov
        self._national = national

    def latest_metric(self, metric_id: str, state_ibge_code: str) -> MetricResponse | None:
        return self._metric

    def provenance(self, metric_id: str, state_ibge_code: str) -> ProvenanceResponse | None:
        return self._prov

    def latest_national_total(
        self, metric_id: str, gold_table: str
    ) -> NationalMetricResponse | None:
        return self._national


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


def test_national_metric_ok() -> None:
    resp = _client(StubRepo(None, None, _NATIONAL)).get(
        "/v1/metrics/inss_beneficios_emitidos/national"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["value"] == 123456.78
    assert body["reference_date"] == "2026-06-01"
    assert body["data_class"] == "observed"
    assert body["provenance"]["source"] == "https://s3/inss_emitidos_202606.zip"


def test_national_metric_unknown_metric_404() -> None:
    resp = _client(StubRepo(None, None, _NATIONAL)).get("/v1/metrics/unknown_metric/national")
    assert resp.status_code == 404


def test_national_metric_no_data_404() -> None:
    resp = _client(StubRepo(None, None, None)).get("/v1/metrics/inss_beneficios_emitidos/national")
    assert resp.status_code == 404


def test_debt_route_unaffected_by_national_route() -> None:
    # C9 (DEFINE): the national route is additive and must not change the
    # debt dataset's existing per-state response shape or behavior.
    resp = _client(StubRepo(_METRIC, _PROV, _NATIONAL)).get("/v1/metrics/divida_consolidada")
    assert resp.status_code == 200
    assert resp.json()["state_ibge_code"] == "35"


def test_national_metric_accepts_negative_value_for_fiscal_primario() -> None:
    # fiscal_primario is legitimately negative in a primary deficit -- the
    # route must serve it as-is, not clamp or reject it.
    negative = NationalMetricResponse(
        metric_id="fiscal_primario",
        value=-1234.56,
        unit="BRL",
        reference_date="2026-05-01",
        data_class="observed",
        provenance=ProvenanceSummary(
            source="https://tesouro/rtn.xlsx",
            reference_date="2026-05-01",
            trust_status="source_only",
        ),
    )
    resp = _client(StubRepo(None, None, negative)).get("/v1/metrics/fiscal_primario/national")
    assert resp.status_code == 200
    assert resp.json()["value"] == -1234.56


def test_openapi_has_all_paths() -> None:
    schema = app.openapi()
    assert "/v1/metrics/{metric_id}" in schema["paths"]
    assert "/v1/metrics/{metric_id}/national" in schema["paths"]
    assert "/v1/provenance/{metric_id}" in schema["paths"]
