from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path

import pytest
from _fakes import UF_CODES, FakeBigQuery

from ingestion.config import load_config
from ingestion.connectors.base import DownloadResult, ResourceRef
from ingestion.pipeline import Quarantined, run

SAMPLE = b"UF;ANO;VALOR\r\nAC;2015;4.245.948.557,36\r\n"


class FakeConnector:
    def __init__(self, *, hash_changed: bool = True) -> None:
        self._hash_changed = hash_changed

    def discover(self) -> ResourceRef:
        return ResourceRef("divida_consolidada_estados", "https://x/y.csv", "csv", None)

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {}

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        Path(dest).write_bytes(SAMPLE)
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


def _gold_rows(year: int = 2022) -> list[dict[str, object]]:
    return [
        {
            "metric_id": "divida_consolidada",
            "state_ibge_code": code,
            "reference_year": year,
            "reference_date": dt.date(year, 12, 31),
            "value": 1000,
            "unit": "BRL",
        }
        for code in UF_CODES
    ]


def _responder(columns: list[str]):
    def respond(sql: str) -> list[dict[str, object]]:
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return [{"column_name": c} for c in columns]
        if "MAX(reference_year)" in sql:
            return [{"y": 2022}]
        if "_row_hash=" in sql and "COUNT(*)" in sql:
            return [{"n": 27}]
        if "br2036_silver" in sql and "COUNT(*)" in sql:
            return [{"c": 27}]
        if "SELECT metric_id, state_ibge_code, reference_year" in sql:
            return _gold_rows()
        return []

    return respond


def _config():
    cfg = load_config()
    return dataclasses.replace(cfg, gcp_project="brasil2036-dev", raw_bucket="brasil2036-dev-raw")


def test_pipeline_happy_path() -> None:
    client = FakeBigQuery(_responder(["UF", "ANO", "VALOR", "_source_uri", "_row_hash"]))
    result = run(
        _config(),
        connector=FakeConnector(),
        storage_client=FakeStorage(),
        bq_client=client,
    )
    assert result.status == "ok"
    assert result.reference_year == 2022
    assert result.gold_rows == 27
    assert result.provenance_rows == 27
    assert any("br2036_silver.debt_state" in q for q in client.queries)
    assert any("gold_debt_state_current" in q for q in client.queries)


def test_pipeline_noop_when_hash_unchanged() -> None:
    result = run(
        _config(),
        connector=FakeConnector(hash_changed=False),
        storage_client=FakeStorage(),
        bq_client=FakeBigQuery(_responder(["UF", "ANO", "VALOR"])),
    )
    assert result.status == "no-op"
    assert result.gold_rows == 0


def test_pipeline_quarantines_on_schema_drift() -> None:
    client = FakeBigQuery(_responder(["UF", "ANO"]))
    with pytest.raises(Quarantined):
        run(
            _config(),
            connector=FakeConnector(),
            storage_client=FakeStorage(),
            bq_client=client,
        )
