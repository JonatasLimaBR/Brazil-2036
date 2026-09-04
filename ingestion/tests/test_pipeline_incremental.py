from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from _fakes import FakeBigQuery

from ingestion.connectors.base import DownloadResult, ResourceRef
from ingestion.pipeline_incremental import IncrementalConfig, Quarantined, run

CONTRACT_PATH = Path(__file__).parent / "fixtures" / "inss_emitidos_contract.yaml"

CONTRACT_YAML = """
dataset: inss_beneficios_emitidos
version: 1
source_columns:
  - uf
  - vl_liquido
keys:
  - state_ibge_code
required_fields:
  state_ibge_code: {type: STRING, nullable: false}
quality_rules: []
"""

SAMPLE = "uf;vl_liquido\r\nSAO PAULO;100,00\r\n"


class FakeConnector:
    def __init__(self, *, hash_changed: bool = True) -> None:
        self._hash_changed = hash_changed

    def discover(self) -> ResourceRef:
        return ResourceRef("inss_beneficios_emitidos", "https://s3/x.zip", "zip", None)

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {}

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        Path(dest).write_bytes(SAMPLE.encode())
        return DownloadResult(dest, "deadbeef", 200, len(SAMPLE), 1, [])

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
            def blob(self, blob_name: str) -> FakeBlob:
                return FakeBlob(store, blob_name)

        return _B()


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
        contract_path=CONTRACT_PATH,
        gcp_project="brasil2036-dev",
        raw_bucket="brasil2036-dev-raw",
        raw_prefix="inss",
        bq_dataset_control="br2036_control",
        bq_dataset_bronze="br2036_bronze",
        bq_dataset_silver="br2036_silver",
        bq_dataset_gold="br2036_gold",
        bronze_table="inss_beneficios_emitidos_raw",
        bronze_columns=("uf", "vl_liquido"),
        field_delimiter=";",
        silver_model="inss_beneficios_emitidos",
        gold_model="gold_inss_beneficios_emitidos",
        ckan_base_url="https://dadosabertos.inss.gov.br",
        ckan_package_id="inss-beneficios-emitidos",
    )


def _responder(columns: list[str]):
    def respond(sql: str) -> list[dict[str, object]]:
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return [{"column_name": c} for c in columns]
        if "COUNT(*)" in sql and "br2036_bronze" in sql:
            return [{"f0_": 1}]
        if "COUNT(*)" in sql and "metric_provenance" in sql:
            return [{"n": 1}]
        if "SELECT * FROM" in sql and "gold_inss_beneficios_emitidos" in sql:
            return [
                {
                    "state_ibge_code": "35",
                    "reference_date": dt.date(2026, 6, 1),
                    "value": 100,
                }
            ]
        return []

    return respond


@pytest.fixture(autouse=True)
def _write_contract(tmp_path_factory) -> None:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(CONTRACT_YAML, encoding="utf-8")
    yield
    CONTRACT_PATH.unlink(missing_ok=True)


def test_incremental_pipeline_happy_path() -> None:
    client = FakeBigQuery(_responder(["uf", "vl_liquido"]))
    result = run(
        _config(),
        connector=FakeConnector(),
        storage_client=FakeStorage(),
        bq_client=client,
        reference_period=dt.date(2026, 6, 1),
    )
    assert result.status == "ok"
    assert result.provenance_rows == 1
    assert any("MERGE" in q for q in client.queries)
    assert any("_reference_period" in q for q in client.queries)


def test_incremental_pipeline_noop_when_hash_unchanged() -> None:
    result = run(
        _config(),
        connector=FakeConnector(hash_changed=False),
        storage_client=FakeStorage(),
        bq_client=FakeBigQuery(_responder(["uf", "vl_liquido"])),
        reference_period=dt.date(2026, 6, 1),
    )
    assert result.status == "no-op"


def test_incremental_pipeline_quarantines_on_schema_drift() -> None:
    client = FakeBigQuery(_responder(["uf"]))
    with pytest.raises(Quarantined):
        run(
            _config(),
            connector=FakeConnector(),
            storage_client=FakeStorage(),
            bq_client=client,
            reference_period=dt.date(2026, 6, 1),
        )


def test_incremental_pipeline_two_periods_accumulate_not_overwrite() -> None:
    client = FakeBigQuery(_responder(["uf", "vl_liquido"]))
    for period in (dt.date(2026, 5, 1), dt.date(2026, 6, 1)):
        run(
            _config(),
            connector=FakeConnector(),
            storage_client=FakeStorage(),
            bq_client=client,
            reference_period=period,
        )
    delete_queries = [q for q in client.queries if q.startswith("DELETE FROM")]
    assert any("2026-05-01" in q for q in delete_queries)
    assert any("2026-06-01" in q for q in delete_queries)
    # No query *statement* replaces the whole table (comments mentioning the
    # phrase, e.g. explaining why, are fine -- only a literal leading
    # CREATE OR REPLACE would silently erase already-loaded months).
    assert not any(q.strip().upper().startswith("CREATE OR REPLACE") for q in client.queries)
