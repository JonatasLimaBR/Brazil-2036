from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from api.bigquery_repo import BigQueryRepo
from api.config import Config

CONFIG = Config(
    gcp_project="brasil2036-dev",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
)

_GOLD_ROW = {
    "state_ibge_code": "35",
    "value": 332702923995.99,
    "unit": "BRL",
    "reference_year": 2022,
    "reference_date": "2022-12-31",
    "data_class": "observed",
}
_PROV_ROW = {
    "metric_id": "divida_consolidada",
    "state_ibge_code": "35",
    "reference_year": 2022,
    "reference_date": "2022-12-31",
    "gold_object": "brasil2036-dev.br2036_gold.gold_debt_state_current",
    "silver_transform": "sql/silver/debt_state.sql",
    "silver_transform_version": "d0ab403d",
    "bronze_object": "gs://brasil2036-dev-raw/divida_estados/abc.csv",
    "source_resource_url": "https://tesouro/x.csv",
    "catalog_dataset_id": "divida_consolidada_estados",
    "producing_organization": "COREM / STN",
    "source": "https://tesouro/x.csv",
}


def _run_query(present: bool = True):
    def run(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        if not present:
            return []
        if "SELECT source," in sql and "reference_year = @year" in sql:
            return [{"source": _PROV_ROW["source"], "reference_date": "2022-12-31"}]
        if "source AS source_resource_url" in sql:
            return [dict(_PROV_ROW)]
        if "MAX(reference_year)" in sql and "data_class" in sql:
            return [dict(_GOLD_ROW)]
        return []

    return run


def test_latest_metric_maps_row_and_embeds_provenance() -> None:
    repo = BigQueryRepo(CONFIG, _run_query())
    result = repo.latest_metric("divida_consolidada", "35")
    assert result is not None
    assert result.value == 332702923995.99
    assert result.reference_year == 2022
    assert result.reference_date == "2022-12-31"
    assert result.data_class.value == "observed"
    assert result.provenance.source == "https://tesouro/x.csv"
    assert result.provenance.trust_status == "source_only"


def test_latest_metric_missing_returns_none() -> None:
    repo = BigQueryRepo(CONFIG, _run_query(present=False))
    assert repo.latest_metric("divida_consolidada", "99") is None


def test_provenance_full_chain() -> None:
    repo = BigQueryRepo(CONFIG, _run_query())
    result = repo.provenance("divida_consolidada", "35")
    assert result is not None
    assert result.source_resource_url == "https://tesouro/x.csv"
    assert result.producing_organization == "COREM / STN"
    assert result.silver_transform_version == "d0ab403d"
    assert result.trust_status == "source_only"


def test_provenance_missing_returns_none() -> None:
    repo = BigQueryRepo(CONFIG, _run_query(present=False))
    assert repo.provenance("divida_consolidada", "99") is None


def _national_run_query(present: bool = True):
    def run(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        if not present:
            return []
        if "SUM(value) AS value" in sql:
            return [{"value": 123456.78, "unit": "BRL", "reference_date": "2026-06-01"}]
        if "ANY_VALUE(source) AS source" in sql:
            return [{"source": "https://s3/inss_emitidos_202606.zip"}]
        return []

    return run


def test_latest_national_total_sums_across_uf_and_especie() -> None:
    repo = BigQueryRepo(CONFIG, _national_run_query())
    result = repo.latest_national_total("inss_beneficios_emitidos", "gold_inss_beneficios_emitidos")
    assert result is not None
    assert result.value == 123456.78
    assert result.unit == "BRL"
    assert result.reference_date == "2026-06-01"
    assert result.data_class.value == "observed"
    assert result.provenance.source == "https://s3/inss_emitidos_202606.zip"


def test_latest_national_total_missing_returns_none() -> None:
    repo = BigQueryRepo(CONFIG, _national_run_query(present=False))
    assert repo.latest_national_total("inss_beneficios_emitidos", "gold_inss_x") is None


def test_latest_national_total_returns_none_when_gold_table_does_not_exist_yet() -> None:
    # A metric_tables entry can exist before its backfill has ever run (e.g.
    # Mantidos), so the Gold table itself may not exist. Found by an
    # independent /verify-spec review hitting the live endpoint and getting a
    # 500 instead of the documented 404.
    from google.api_core.exceptions import NotFound

    def run(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        raise NotFound("gold_inss_beneficios_mantidos not found")

    repo = BigQueryRepo(CONFIG, run)
    assert (
        repo.latest_national_total("inss_beneficios_mantidos", "gold_inss_beneficios_mantidos")
        is None
    )
