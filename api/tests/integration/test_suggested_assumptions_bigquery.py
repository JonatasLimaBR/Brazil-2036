from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

# api/ never had a real-BigQuery integration test before this feature -- a
# real SQL syntax bug (BigQuery rejected the pib_mensal query's ORDER BY
# placement: "references column reference_date which is neither grouped nor
# aggregated") shipped past every mock-based unit test and only surfaced on
# the first live call in production (MACRO_TWIN_EXPANSION Achado #4). Mocks
# never parse real SQL; this test does, against the real Gold tables already
# populated by selic_mensal/pib_mensal (DEBTLAB_SIMULATOR, this feature's
# PR1) -- read-only, no side effects, no isolated dataset needed.


@pytest.fixture(scope="module")
def project() -> str:
    value = os.environ.get("GCP_PROJECT")
    if not value:
        pytest.skip("GCP_PROJECT not set; integration test needs a real GCP project")
    return value


def test_suggested_assumptions_against_real_bigquery(project: str) -> None:
    from api.bigquery_repo import BigQueryRepo, build_bigquery_run_query
    from api.config import Config

    config = Config(
        gcp_project=project,
        bq_dataset_gold="br2036_gold",
        gold_table="gold_debt_state_current",
        provenance_table="metric_provenance",
        default_metric_id="divida_consolidada",
        default_state_ibge_code="35",
        metric_tables={"selic_mensal": "gold_selic_mensal", "pib_mensal": "gold_pib_mensal"},
    )
    repo = BigQueryRepo(config, build_bigquery_run_query(project))

    result = repo.suggested_assumptions()

    assert result is not None
    # Sane ranges, not exact values -- both series keep accumulating real
    # months, so the trailing-12-month window shifts over time.
    assert -0.5 < result.juros_nominal.mean < 0.5
    assert result.juros_nominal.std >= 0
    assert result.juros_nominal.window_months == 12
    assert -0.5 < result.crescimento_nominal_pib.mean < 0.5
    assert result.crescimento_nominal_pib.std >= 0
    assert result.crescimento_nominal_pib.window_months == 12
    assert result.data_class == "estimated"
