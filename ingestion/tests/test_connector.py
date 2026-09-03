from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ingestion.connectors.base import ConnectorError
from ingestion.connectors.divida_estados import DividaEstadosConnector

RESOURCE_URL = "https://example.test/divida.csv"
SAMPLE_CSV = b"UF;ANO;VALOR\r\nAC;2015;4.245.948.557,36\r\nAL;2015;11.252.027.857,87\r\n"


class FakeResponse:
    def __init__(self, *, status_code: int = 200, content: bytes = b"", fail: bool = False) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"Content-Type": "text/csv", "Content-Length": str(len(content))}
        self._fail = fail

    def raise_for_status(self) -> None:
        if self._fail or self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses
        self.calls = 0

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.calls += 1
        return self._responses[min(self.calls - 1, len(self._responses) - 1)]

    def head(self, url: str, timeout: float, allow_redirects: bool) -> FakeResponse:
        return self._responses[0]


def _connector(session: FakeSession, known_hash: str | None = None) -> DividaEstadosConnector:
    return DividaEstadosConnector(
        session=session,
        resource_url=RESOURCE_URL,
        known_hash=known_hash,
        max_retries=3,
        backoff_seconds=0.0,
    )


def test_download_computes_sha256_and_writes(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(content=SAMPLE_CSV)])
    dest = tmp_path / "out.csv"
    result = _connector(session).download(_connector(session).discover(), str(dest))
    assert dest.read_bytes() == SAMPLE_CSV
    assert result.content_sha256 == hashlib.sha256(SAMPLE_CSV).hexdigest()
    assert result.attempts == 1


def test_download_retries_then_succeeds(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(fail=True), FakeResponse(content=SAMPLE_CSV)])
    dest = tmp_path / "out.csv"
    conn = _connector(session)
    result = conn.download(conn.discover(), str(dest))
    assert result.bytes_downloaded == len(SAMPLE_CSV)
    assert result.attempts == 2
    assert len(result.attempt_errors) == 1


def test_download_exhausts_retries(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(fail=True)])
    conn = _connector(session)
    with pytest.raises(ConnectorError):
        conn.download(conn.discover(), str(tmp_path / "out.csv"))


def test_validate_accepts_expected_header(tmp_path: Path) -> None:
    path = tmp_path / "ok.csv"
    path.write_bytes(SAMPLE_CSV)
    _connector(FakeSession([FakeResponse()])).validate(str(path))


def test_validate_rejects_wrong_header(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("estado;ano;valor\n", encoding="utf-8")
    with pytest.raises(ConnectorError):
        _connector(FakeSession([FakeResponse()])).validate(str(path))


def test_checkpoint_detects_change() -> None:
    conn = _connector(FakeSession([FakeResponse()]), known_hash="oldhash")
    ref = conn.discover()
    assert conn.checkpoint(ref, "newhash") is True
    assert conn.checkpoint(ref, "oldhash") is False
