from __future__ import annotations

import json

import pytest

from ingestion.connectors.base import ConnectorError, ResourceRef
from ingestion.connectors.bcb_sgs import (
    BcbSgsSeries,
    build_default_connector,
    parse_to_long_csv,
)

_PIB_SERIES = BcbSgsSeries(series_code=4380, metric_id="pib_mensal")
_DIVIDA_SERIES = BcbSgsSeries(series_code=13762, metric_id="divida_bruta_pib")

_SAMPLE_PIB = json.dumps(
    [
        {"data": "01/05/2026", "valor": "1128771.2"},
        {"data": "01/06/2026", "valor": "1137165.3"},
        {"data": "01/07/2026", "valor": "1167869.0"},
    ]
).encode("utf-8")

_SAMPLE_DIVIDA = json.dumps(
    [
        {"data": "01/05/2026", "valor": "81.05"},
        {"data": "01/06/2026", "valor": "81.93"},
        {"data": "01/07/2026", "valor": "82.51"},
    ]
).encode("utf-8")


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self._content = content
        self._status_code = status_code

    def get(self, url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(self._status_code, self._content)


def test_discover_builds_real_sgs_url_for_series_code() -> None:
    connector = build_default_connector(_FakeSession(_SAMPLE_DIVIDA), series=_DIVIDA_SERIES)
    ref = connector.discover()
    assert (
        ref.resource_url == "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13762/dados?formato=json"
    )
    assert ref.resource_format == "json"


def test_download_writes_response_bytes(tmp_path) -> None:
    connector = build_default_connector(_FakeSession(_SAMPLE_PIB), series=_PIB_SERIES)
    dest = str(tmp_path / "resource.json")
    result = connector.download(connector.discover(), dest)
    assert tmp_path.joinpath("resource.json").read_bytes() == _SAMPLE_PIB
    assert result.bytes_downloaded == len(_SAMPLE_PIB)


def test_download_supports_file_scheme_for_tests_without_network(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(_SAMPLE_PIB)
    ref = ResourceRef(
        dataset_id="pib_mensal", resource_url=f"file://{source}", resource_format="json"
    )
    connector = build_default_connector(_FakeSession(b""), series=_PIB_SERIES)
    dest = str(tmp_path / "resource.json")
    result = connector.download(ref, dest)
    assert result.bytes_downloaded == len(_SAMPLE_PIB)
    assert result.http_status == 200


def test_validate_accepts_real_shaped_payload(tmp_path) -> None:
    dest = tmp_path / "resource.json"
    dest.write_bytes(_SAMPLE_DIVIDA)
    connector = build_default_connector(_FakeSession(_SAMPLE_DIVIDA), series=_DIVIDA_SERIES)
    connector.validate(str(dest))


def test_validate_rejects_malformed_payload(tmp_path) -> None:
    dest = tmp_path / "resource.json"
    dest.write_bytes(b'{"not": "a list"}')
    connector = build_default_connector(_FakeSession(b""), series=_PIB_SERIES)
    with pytest.raises(ConnectorError):
        connector.validate(str(dest))


def test_validate_rejects_row_missing_expected_keys(tmp_path) -> None:
    dest = tmp_path / "resource.json"
    dest.write_bytes(json.dumps([{"unexpected": "shape"}]).encode("utf-8"))
    connector = build_default_connector(_FakeSession(b""), series=_PIB_SERIES)
    with pytest.raises(ConnectorError):
        connector.validate(str(dest))


def test_checkpoint_always_proceeds_when_no_prior_hash_recorded() -> None:
    connector = build_default_connector(_FakeSession(_SAMPLE_PIB), series=_PIB_SERIES)
    ref = connector.discover()
    assert connector.checkpoint(ref, "any-hash") is True


def test_parse_to_long_csv_converts_json_rows_to_csv() -> None:
    csv_bytes = parse_to_long_csv(_SAMPLE_DIVIDA, series_code=13762)
    lines = csv_bytes.decode("utf-8").strip().splitlines()
    assert lines[0] == "reference_period,value"
    rows = dict(line.split(",") for line in lines[1:])
    assert rows["2026-07-01"] == "82.51"
    assert rows["2026-05-01"] == "81.05"


def test_parse_to_long_csv_raises_on_unparseable_date() -> None:
    bad = json.dumps([{"data": "not-a-date", "valor": "1.0"}]).encode("utf-8")
    with pytest.raises(ConnectorError):
        parse_to_long_csv(bad, series_code=4380)
