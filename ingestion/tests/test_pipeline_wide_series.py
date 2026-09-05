from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from _fakes import FakeBigQuery

from ingestion.connectors.base import DownloadResult, ResourceRef
from ingestion.pipeline_wide_series import Quarantined, WideSeriesConfig, run

CONTRACT_PATH = Path(__file__).parent / "fixtures" / "fiscal_uniao_contract.yaml"

CONTRACT_YAML = """
dataset: fiscal_uniao
version: 1
source_columns:
  - metric_id
  - reference_period
  - value_millions
keys:
  - state_ibge_code
  - metric_id
  - reference_date
required_fields:
  state_ibge_code: {type: STRING, nullable: false}
quality_rules: []
"""

SAMPLE_XLSX_BYTES = b"fake-xlsx-bytes"
SAMPLE_CSV = (
    b"metric_id,reference_period,value_millions\n"
    b"fiscal_receita,2026-06-01,226305.45\n"
    b"fiscal_despesa,2026-06-01,215522.02\n"
    b"fiscal_primario,2026-06-01,-1234.56\n"
)


class FakeConnector:
    def __init__(self, *, hash_changed: bool = True) -> None:
        self._hash_changed = hash_changed

    def discover(self) -> ResourceRef:
        return ResourceRef("fiscal_uniao", "https://tesouro/rtn.xlsx", "xlsx", None)

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {}

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        Path(dest).write_bytes(SAMPLE_XLSX_BYTES)
        return DownloadResult(dest, "deadbeef", 200, len(SAMPLE_XLSX_BYTES), 1, [])

    def validate(self, local_path: str) -> None:
        return None

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        return self._hash_changed


class FakeBlob:
    def __init__(self, store: dict[str, bytes], name: str) -> None:
        self._store, self._name = store, name

    def exists(self) -> bool:
        return self._name in self._store

    def upload_from_string(self, data, *, content_type: str, if_generation_match: int) -> None:
        self._store[self._name] = data if isinstance(data, bytes) else data.encode()


class FakeStorage:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def bucket(self, name: str):
        store = self.store

        class _B:
            def blob(self, blob_name: str):
                return FakeBlob(store, blob_name)

        return _B()


def _config() -> WideSeriesConfig:
    return WideSeriesConfig(
        dataset_id="fiscal_uniao",
        br2036_domain="fiscal",
        br2036_module="M02",
        catalog_url="https://tesourotransparente.gov.br/ckan/dataset/resultado-do-tesouro-nacional",
        organization="Tesouro Nacional / CESEF",
        license="ODbL",
        metric_ids=("fiscal_receita", "fiscal_despesa", "fiscal_primario"),
        unit="BRL",
        contract_path=CONTRACT_PATH,
        gcp_project="brasil2036-dev",
        raw_bucket="brasil2036-dev-raw",
        raw_prefix="fiscal",
        bq_dataset_control="br2036_control",
        bq_dataset_bronze="br2036_bronze",
        bq_dataset_silver="br2036_silver",
        bq_dataset_gold="br2036_gold",
        bronze_table="fiscal_uniao_raw",
        bronze_columns=("metric_id", "reference_period", "value_millions"),
        field_delimiter=",",
        silver_model="fiscal_uniao",
        gold_model="gold_fiscal_uniao",
        ckan_base_url="https://tesourotransparente.gov.br/ckan",
        ckan_package_id="ab56485b-9c40-4efb-8563-9ce3e1973c4b",
        allow_negative_metric_ids=("fiscal_primario",),
    )


_PERIOD = dt.date(2026, 6, 1)
_GOLD_ROWS = {
    "fiscal_receita": {"state_ibge_code": "BR", "reference_date": _PERIOD, "value": 226305.45},
    "fiscal_despesa": {"state_ibge_code": "BR", "reference_date": _PERIOD, "value": 215522.02},
    "fiscal_primario": {"state_ibge_code": "BR", "reference_date": _PERIOD, "value": -1234.56},
}


def _responder(columns: list[str]):
    def respond(sql: str) -> list[dict[str, object]]:
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return [{"column_name": c} for c in columns]
        if "COUNT(*)" in sql and "metric_provenance" in sql:
            return [{"n": 1}]
        for metric_id, row in _GOLD_ROWS.items():
            if "SELECT * FROM" in sql and f"metric_id = '{metric_id}'" in sql:
                return [row]
        return []

    return respond


@pytest.fixture(autouse=True)
def _write_contract() -> None:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(CONTRACT_YAML, encoding="utf-8")
    yield
    CONTRACT_PATH.unlink(missing_ok=True)


def test_wide_series_pipeline_happy_path_accepts_negative_primary_result() -> None:
    client = FakeBigQuery(_responder(["metric_id", "reference_period", "value_millions"]))
    result = run(
        _config(),
        connector=FakeConnector(),
        storage_client=FakeStorage(),
        bq_client=client,
        parse_to_long_csv=lambda _payload: SAMPLE_CSV,
    )
    assert result.status == "ok"
    assert result.gold_rows == 3
    assert result.provenance_rows == 3


def test_wide_series_pipeline_writes_two_raw_objects_original_and_csv() -> None:
    storage = FakeStorage()
    run(
        _config(),
        connector=FakeConnector(),
        storage_client=storage,
        bq_client=FakeBigQuery(_responder(["metric_id", "reference_period", "value_millions"])),
        parse_to_long_csv=lambda _payload: SAMPLE_CSV,
    )
    suffixes = {name.rsplit(".", 1)[-1] for name in storage.store if not name.endswith(".json")}
    assert suffixes == {"xlsx", "csv"}


def test_wide_series_pipeline_noop_when_hash_unchanged() -> None:
    result = run(
        _config(),
        connector=FakeConnector(hash_changed=False),
        storage_client=FakeStorage(),
        bq_client=FakeBigQuery(_responder(["metric_id", "reference_period", "value_millions"])),
        parse_to_long_csv=lambda _payload: SAMPLE_CSV,
    )
    assert result.status == "no-op"


def test_wide_series_pipeline_quarantines_on_schema_drift() -> None:
    client = FakeBigQuery(_responder(["metric_id"]))
    with pytest.raises(Quarantined):
        run(
            _config(),
            connector=FakeConnector(),
            storage_client=FakeStorage(),
            bq_client=client,
            parse_to_long_csv=lambda _payload: SAMPLE_CSV,
        )


def test_wide_series_pipeline_rebuilds_whole_table_not_partition() -> None:
    client = FakeBigQuery(_responder(["metric_id", "reference_period", "value_millions"]))
    run(
        _config(),
        connector=FakeConnector(),
        storage_client=FakeStorage(),
        bq_client=client,
        parse_to_long_csv=lambda _payload: SAMPLE_CSV,
    )
    assert any(q.strip().upper().startswith("CREATE OR REPLACE") for q in client.queries)
