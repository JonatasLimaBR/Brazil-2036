from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.bigquery_repo import BigQueryRepo
from api.config import Config
from api.main import app, get_config, get_repo
from api.models import DebtLabScenarioResponse, NationalMetricResponse

CONFIG = Config(
    gcp_project="brasil2036-dev",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
    metric_tables={"selic_mensal": "gold_selic_mensal", "pib_mensal": "gold_pib_mensal"},
)

# avg_m=1.0%, std_m=0.1% -> juros_mean=(1.01)^12-1, juros_std=0.001*sqrt(12) -- computed by hand.
_SELIC_ROW = {
    "avg_m": 1.0,
    "std_m": 0.1,
    "start_d": "2025-10-01",
    "end_d": "2026-09-01",
    "n": 12,
}
_PIB_ROW = {
    "avg_yoy": 0.05,
    "std_yoy": 0.02,
    "start_d": "2025-08-01",
    "end_d": "2026-07-01",
    "n": 12,
}


def _run_query_full(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "selic_mensal" in sql:
        return [dict(_SELIC_ROW)]
    if "pib_mensal" in sql:
        return [dict(_PIB_ROW)]
    raise AssertionError(f"unexpected query: {sql}")


def _run_query_insufficient(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "selic_mensal" in sql:
        return [{**_SELIC_ROW, "n": 3}]
    if "pib_mensal" in sql:
        return [dict(_PIB_ROW)]
    raise AssertionError(f"unexpected query: {sql}")


def test_suggested_assumptions_computes_annualized_selic_and_yoy_pib() -> None:
    repo = BigQueryRepo(CONFIG, _run_query_full)
    result = repo.suggested_assumptions()
    assert result is not None
    assert result.juros_nominal.mean == pytest.approx(0.12682503013196977)
    assert result.juros_nominal.std == pytest.approx(0.0034641016151377543)
    assert result.juros_nominal.window_months == 12
    assert result.juros_nominal.source_metric_id == "selic_mensal"
    assert result.crescimento_nominal_pib.mean == pytest.approx(0.05)
    assert result.crescimento_nominal_pib.std == pytest.approx(0.02)
    assert result.data_class == "estimated"


def test_suggested_assumptions_none_when_fewer_than_12_real_months() -> None:
    # Never completes the window with a fabricated value (DESIGN §0.3).
    repo = BigQueryRepo(CONFIG, _run_query_insufficient)
    assert repo.suggested_assumptions() is None


def test_suggested_assumptions_none_when_metric_tables_missing_entries() -> None:
    bare_config = Config(
        gcp_project="brasil2036-dev",
        bq_dataset_gold="br2036_gold",
        gold_table="gold_debt_state_current",
        provenance_table="metric_provenance",
        default_metric_id="divida_consolidada",
        default_state_ibge_code="35",
    )
    repo = BigQueryRepo(bare_config, _run_query_full)
    assert repo.suggested_assumptions() is None


class _StubRepo:
    def __init__(self, suggestion: object | None) -> None:
        self._suggestion = suggestion

    def suggested_assumptions(self):  # type: ignore[no-untyped-def]
        return self._suggestion

    def get_debtlab_scenario(self, scenario_id: str) -> DebtLabScenarioResponse | None:
        # Route-ordering regression guard: if suggested-assumptions were ever
        # swallowed by the /{scenario_id} route, this stub would be called
        # with scenario_id="suggested-assumptions" instead -- assert it never is.
        raise AssertionError(
            f"get_debtlab_scenario called with {scenario_id!r} -- "
            "suggested-assumptions route was shadowed by /{scenario_id}"
        )

    def debtlab_base(self) -> NationalMetricResponse | None:
        raise AssertionError("debtlab_base should not be called by the suggestion route")


def _client(repo: _StubRepo) -> TestClient:
    app.dependency_overrides[get_config] = lambda: CONFIG
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_endpoint_returns_suggestion_not_shadowed_by_scenario_route() -> None:
    repo = BigQueryRepo(CONFIG, _run_query_full)
    suggestion = repo.suggested_assumptions()
    resp = _client(_StubRepo(suggestion)).get("/v1/simulations/debtlab/suggested-assumptions")
    assert resp.status_code == 200
    body = resp.json()
    assert "juros_nominal" in body
    assert "crescimento_nominal_pib" in body
    assert body["data_class"] == "estimated"


def test_endpoint_503_when_insufficient_real_data() -> None:
    resp = _client(_StubRepo(None)).get("/v1/simulations/debtlab/suggested-assumptions")
    assert resp.status_code == 503


def test_openapi_has_suggested_assumptions_path() -> None:
    schema = app.openapi()
    assert "/v1/simulations/debtlab/suggested-assumptions" in schema["paths"]
