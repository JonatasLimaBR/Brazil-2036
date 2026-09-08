from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import Config
from api.main import app, get_config, get_repo
from api.models import (
    DebtLabScenarioBase,
    DebtLabScenarioRequest,
    DebtLabScenarioResponse,
    NationalMetricResponse,
    ProvenanceSummary,
    YearlyDeterministic,
    YearlyPercentiles,
)

_CONFIG = Config(
    gcp_project="test",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
    metric_tables={"divida_bruta_pib": "gold_divida_bruta_pib"},
    bq_dataset_control="br2036_control",
)

_BASE = NationalMetricResponse(
    metric_id="divida_bruta_pib",
    value=82.51,
    unit="pct_pib",
    reference_date="2026-07-01",
    data_class="observed",
    provenance=ProvenanceSummary(
        source="https://api.bcb.gov.br/dados/serie/bcdata.sgs.13762/dados",
        reference_date="2026-07-01",
        trust_status="source_only",
    ),
)

_REQUEST_BODY = {
    "horizon_years": 5,
    "juros_nominal": {"mean": 0.10, "std": 0.02},
    "crescimento_nominal_pib": {"mean": 0.06, "std": 0.015},
    "primario_pct_pib": {"mean": 0.01, "std": 0.005},
    "n_iterations": 200,
    "seed": 42,
}


class StubRepo:
    def __init__(
        self, base: NationalMetricResponse | None, scenario: DebtLabScenarioResponse | None = None
    ) -> None:
        self._base = base
        self._scenario = scenario
        self.saved: DebtLabScenarioResponse | None = None

    def debtlab_base(self) -> NationalMetricResponse | None:
        return self._base

    def create_debtlab_scenario(self, scenario: DebtLabScenarioResponse) -> None:
        self.saved = scenario

    def get_debtlab_scenario(self, scenario_id: str) -> DebtLabScenarioResponse | None:
        return self._scenario


def _client(repo: StubRepo) -> TestClient:
    app.dependency_overrides[get_config] = lambda: _CONFIG
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_create_scenario_returns_simulated_result_anchored_to_real_base() -> None:
    repo = StubRepo(_BASE)
    resp = _client(repo).post("/v1/simulations/debtlab", json=_REQUEST_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_class"] == "simulated"
    assert body["base"]["divida_pib_pct"] == 82.51
    assert body["base"]["reference_date"] == "2026-07-01"
    assert body["deterministic_trajectory"][0]["divida_pib_pct"] == 82.51
    assert len(body["deterministic_trajectory"]) == 6
    assert len(body["percentiles"]) == 6


def test_create_scenario_persists_via_repo() -> None:
    repo = StubRepo(_BASE)
    _client(repo).post("/v1/simulations/debtlab", json=_REQUEST_BODY)
    assert repo.saved is not None
    assert repo.saved.data_class == "simulated"


def test_create_scenario_503_when_no_real_base_data() -> None:
    resp = _client(StubRepo(None)).post("/v1/simulations/debtlab", json=_REQUEST_BODY)
    assert resp.status_code == 503


def test_create_scenario_rejects_n_iterations_above_bound() -> None:
    bad = {**_REQUEST_BODY, "n_iterations": 999_999}
    resp = _client(StubRepo(_BASE)).post("/v1/simulations/debtlab", json=bad)
    assert resp.status_code == 422


def test_create_scenario_rejects_horizon_above_bound() -> None:
    bad = {**_REQUEST_BODY, "horizon_years": 999}
    resp = _client(StubRepo(_BASE)).post("/v1/simulations/debtlab", json=bad)
    assert resp.status_code == 422


def test_get_scenario_returns_persisted_result() -> None:
    scenario = DebtLabScenarioResponse(
        scenario_id="abc123",
        created_at="2026-09-07T12:00:00+00:00",
        horizon_years=5,
        base=DebtLabScenarioBase(
            reference_date="2026-07-01", divida_pib_pct=82.51, source="https://bcb/13762"
        ),
        assumptions=DebtLabScenarioRequest(**_REQUEST_BODY),
        engine_version="debtlab-v1",
        seed=42,
        n_iterations=200,
        deterministic_trajectory=[YearlyDeterministic(year_offset=0, divida_pib_pct=82.51)],
        percentiles=[
            YearlyPercentiles(year_offset=0, p10=82.51, p25=82.51, p50=82.51, p75=82.51, p90=82.51)
        ],
    )
    resp = _client(StubRepo(_BASE, scenario)).get("/v1/simulations/debtlab/abc123")
    assert resp.status_code == 200
    assert resp.json()["scenario_id"] == "abc123"


def test_get_scenario_404_when_not_found() -> None:
    resp = _client(StubRepo(_BASE, None)).get("/v1/simulations/debtlab/does-not-exist")
    assert resp.status_code == 404


def test_no_publish_endpoint_exists() -> None:
    # C6/AT6 (DEFINE): no approval/publish action exists for a scenario --
    # POSTing to a "publish" sub-route must not resolve to anything.
    resp = _client(StubRepo(_BASE)).post("/v1/simulations/debtlab/abc123/publish")
    assert resp.status_code in (404, 405)


def test_openapi_has_debtlab_paths() -> None:
    schema = app.openapi()
    assert "/v1/simulations/debtlab" in schema["paths"]
    assert "/v1/simulations/debtlab/{scenario_id}" in schema["paths"]
