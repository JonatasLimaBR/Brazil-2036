from __future__ import annotations

import io
import zipfile

import pytest

from ingestion.ckan import CkanResource
from ingestion.connectors.base import ConnectorError
from ingestion.connectors.inss_emitidos import EXPECTED_HEADER as EMITIDOS_HEADER
from ingestion.connectors.inss_emitidos import InssEmitidosConnector
from ingestion.connectors.inss_indeferidos import NORMALIZED_COLUMNS as INDEFERIDOS_COLUMNS
from ingestion.connectors.inss_indeferidos import InssIndeferidosConnector
from ingestion.connectors.inss_mantidos import EXPECTED_COLUMNS as MANTIDOS_COLUMNS
from ingestion.connectors.inss_mantidos import InssMantidosConnector


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def get(self, url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(200, self._content)


def _zip_of(name: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(name, content)
    return buf.getvalue()


def _resource(url: str) -> CkanResource:
    return CkanResource(resource_id="r1", name="test", format="ZIP", url=url, last_modified=None)


def test_emitidos_download_extracts_single_csv_from_zip(tmp_path) -> None:
    csv_body = (
        EMITIDOS_HEADER
        + "\r\nDESPACHO;M;URBANA;NORMAL;SAO PAULO;X;Y;Z;Z;100,00;W;01/01/2026;41;X\r\n"
    ).encode()
    zip_bytes = _zip_of("D.SDA.PDA.003.EMI.202606.CSV", csv_body)
    connector = InssEmitidosConnector(
        session=_FakeSession(zip_bytes),
        resource=_resource("https://s3/emitidos.zip"),
    )
    ref = connector.discover()
    assert ref.resource_format == "zip"
    dest = str(tmp_path / "out.csv")
    result = connector.download(ref, dest)
    assert result.bytes_downloaded == len(csv_body)
    connector.validate(dest)
    assert connector.checkpoint(ref, result.content_sha256) is True


def test_emitidos_download_rejects_zip_with_multiple_files() -> None:
    zip_bytes = _zip_of("a.csv", b"x")
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "a") as archive:
        archive.writestr("b.csv", b"y")
    connector = InssEmitidosConnector(
        session=_FakeSession(buf.getvalue()),
        resource=_resource("https://s3/emitidos.zip"),
    )
    with pytest.raises(ConnectorError):
        connector.download(connector.discover(), "/tmp/wont-be-written.csv")


def test_emitidos_validate_rejects_wrong_header(tmp_path) -> None:
    connector = InssEmitidosConnector(
        session=_FakeSession(b""), resource=_resource("https://s3/x.zip")
    )
    bad = tmp_path / "bad.csv"
    bad.write_text("wrong;header\n", encoding="utf-8")
    with pytest.raises(ConnectorError):
        connector.validate(str(bad))


def test_mantidos_normalizes_comma_header_to_semicolon_and_reads_zip(tmp_path) -> None:
    header = ",".join(MANTIDOS_COLUMNS)
    row = (
        "AUXILIO;ZERADO;URBANO;M;X;Y;SUSPENSO;1-A;SAO PAULO;FILHO;"
        "1/1/1990;1/1/2020;1/1/2019;1/1/2018;X;NORMAL;100.00"
    )
    body = f"{header}\n{row}\n"
    zip_bytes = _zip_of("mantidos.csv", body.encode())
    connector = InssMantidosConnector(
        session=_FakeSession(zip_bytes),
        resource=_resource("https://s3/mantidos.zip"),
    )
    ref = connector.discover()
    dest = str(tmp_path / "out.csv")
    connector.download(ref, dest)
    connector.validate(dest)
    written = (tmp_path / "out.csv").read_text(encoding="utf-8")
    assert written.splitlines()[0] == ";".join(MANTIDOS_COLUMNS)


def test_mantidos_reads_plain_csv_not_zipped(tmp_path) -> None:
    header = ",".join(MANTIDOS_COLUMNS)
    row = (
        "AUXILIO;ZERADO;URBANO;M;X;Y;ATIVO;1-A;PARANA;FILHO;"
        "1/1/1990;;1/1/2019;1/1/2018;X;NORMAL;100.00"
    )
    body = f"{header}\n{row}\n"
    connector = InssMantidosConnector(
        session=_FakeSession(body.encode()),
        resource=_resource("https://s3/D.DLK.FRM.000.DADOSABERTOS.MANTIDOS_ATIVOS_202607.CSV"),
    )
    ref = connector.discover()
    assert ref.resource_format == "csv"
    dest = str(tmp_path / "out.csv")
    connector.download(ref, dest)
    connector.validate(dest)


def test_indeferidos_converts_xlsx_to_normalized_csv(tmp_path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["DADOS ABERTOS - TITLE"] + [None] * (len(INDEFERIDOS_COLUMNS) - 1))
    sheet.append(list(INDEFERIDOS_COLUMNS))
    sheet.append(
        [
            202607,
            36,
            "Auxilio",
            "Motivo",
            None,
            "Masculino",
            "Urbano",
            "Empregado",
            "Alagoas",
            None,
            "Comerciario",
            1,
            "APS 1",
            None,
        ]
    )
    buf = io.BytesIO()
    wb.save(buf)

    connector = InssIndeferidosConnector(
        session=_FakeSession(buf.getvalue()),
        resource=_resource("https://s3/indeferidos.xlsx"),
    )
    ref = connector.discover()
    assert ref.resource_format == "xlsx"
    dest = str(tmp_path / "out.csv")
    result = connector.download(ref, dest)
    assert result.bytes_downloaded > 0
    connector.validate(dest)
    lines = (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ";".join(INDEFERIDOS_COLUMNS)
    assert "Alagoas" in lines[1]


def test_indeferidos_rejects_wrong_column_count(tmp_path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["title"])
    sheet.append(["only", "two"])
    buf = io.BytesIO()
    wb.save(buf)
    connector = InssIndeferidosConnector(
        session=_FakeSession(buf.getvalue()),
        resource=_resource("https://s3/indeferidos.xlsx"),
    )
    with pytest.raises(ConnectorError):
        connector.download(connector.discover(), str(tmp_path / "out.csv"))
