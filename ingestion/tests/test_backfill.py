from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from _fakes import FakeBigQuery

from ingestion import pipeline_incremental
from ingestion.backfill import parse_period_from_url, run_backfill
from ingestion.ckan import CkanResource
from ingestion.pipeline_incremental import IncrementalConfig, IncrementalRunResult


def _config() -> IncrementalConfig:
    return IncrementalConfig(
        dataset_id="inss_beneficios_emitidos",
        br2036_domain="inss",
        br2036_module="M03",
        catalog_url="https://dados.gov.br/dataset/inss-beneficios-emitidos",
        organization="INSS",
        license="cc-by",
        metric_id="inss_beneficios_emitidos",
        unit="BRL",
        contract_path=Path("contracts/inss_beneficios_emitidos.yaml"),
        gcp_project="p",
        raw_bucket="p-raw",
        raw_prefix="inss",
        bq_dataset_control="br2036_control",
        bq_dataset_bronze="br2036_bronze",
        bq_dataset_silver="br2036_silver",
        bq_dataset_gold="br2036_gold",
        bronze_table="inss_beneficios_emitidos_raw",
        bronze_columns=("uf",),
        field_delimiter=";",
        silver_model="inss_beneficios_emitidos",
        gold_model="gold_inss_beneficios_emitidos",
        ckan_base_url="https://dadosabertos.inss.gov.br",
        ckan_package_id="inss-beneficios-emitidos",
    )


def test_parse_period_from_url_matches_yyyymm() -> None:
    assert parse_period_from_url("https://s3/D.SDA.PDA.003.EMI.202306.CSV.ZIP") == dt.date(
        2023, 6, 1
    )
    assert parse_period_from_url(
        "https://s3/D.DLK.FRM.000.DADOSABERTOS.EMITIDOS_202607.zip"
    ) == dt.date(2026, 7, 1)


def test_parse_period_from_url_raises_when_absent() -> None:
    with pytest.raises(ValueError, match="YYYYMM"):
        parse_period_from_url("https://s3/no-date-here.zip")


class _FakeCkanSession:
    def __init__(self, resources: list[CkanResource]) -> None:
        self._resources = resources

    def get(self, url: str, timeout: float):  # noqa: ANN001, ANN201
        class _R:
            status_code = 200

            def raise_for_status(self_inner) -> None:  # noqa: ANN001
                return None

            def json(self_inner) -> dict:  # noqa: ANN001
                return {
                    "success": True,
                    "result": {
                        "resources": [
                            {
                                "id": r.resource_id,
                                "name": r.name,
                                "format": r.format,
                                "url": r.url,
                                "last_modified": r.last_modified,
                            }
                            for r in self._resources
                        ]
                    },
                }

        return _R()


def _resource(period: str, resource_id: str) -> CkanResource:
    return CkanResource(
        resource_id=resource_id,
        name=f"Beneficios Emitidos {period}",
        format="CSV",
        url=f"https://s3/D.SDA.PDA.003.EMI.{period}.CSV.ZIP",
        last_modified=None,
    )


def test_run_backfill_skips_already_loaded_and_resumes(monkeypatch) -> None:
    resources = [_resource("202605", "r1"), _resource("202606", "r2")]
    session = _FakeCkanSession(resources)

    def _partitions_responder(sql: str) -> list[dict[str, object]]:
        if "INFORMATION_SCHEMA.PARTITIONS" in sql:
            return [{"partition_id": "20260501"}]
        return []

    client = FakeBigQuery(_partitions_responder)
    calls: list[dt.date] = []

    def _fake_run(config, *, connector, storage_client, bq_client, reference_period, sql_dir=None):
        calls.append(reference_period)
        return IncrementalRunResult(
            run_id="r", status="ok", reference_period=reference_period, bronze_rows=1
        )

    monkeypatch.setattr(pipeline_incremental, "run", _fake_run)

    result = run_backfill(
        ckan_session=session,
        config=_config(),
        connector_factory=lambda r: object(),  # type: ignore[return-value]
        storage_client=object(),  # type: ignore[arg-type]
        bq_client=client,
    )

    assert calls == [dt.date(2026, 6, 1)]
    assert result.skipped == 1
    assert result.loaded == 1
    assert result.failed == 0


def test_run_backfill_isolates_a_single_resource_failure(monkeypatch) -> None:
    resources = [_resource("202605", "r1"), _resource("202606", "r2")]
    session = _FakeCkanSession(resources)
    client = FakeBigQuery(lambda sql: [])
    calls: list[dt.date] = []

    def _fake_run(config, *, connector, storage_client, bq_client, reference_period, sql_dir=None):
        calls.append(reference_period)
        if reference_period == dt.date(2026, 5, 1):
            raise RuntimeError("boom")
        return IncrementalRunResult(
            run_id="r", status="ok", reference_period=reference_period, bronze_rows=1
        )

    monkeypatch.setattr(pipeline_incremental, "run", _fake_run)

    result = run_backfill(
        ckan_session=session,
        config=_config(),
        connector_factory=lambda r: object(),  # type: ignore[return-value]
        storage_client=object(),  # type: ignore[arg-type]
        bq_client=client,
    )

    assert calls == [dt.date(2026, 5, 1), dt.date(2026, 6, 1)]
    assert result.failed == 1
    assert result.loaded == 1
