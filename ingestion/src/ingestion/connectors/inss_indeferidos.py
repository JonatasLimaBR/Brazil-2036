from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Protocol

import openpyxl

from ingestion.ckan import CkanResource
from ingestion.connectors.base import (
    ConnectorError,
    DownloadResult,
    ResourceRef,
    retry_with_backoff,
)

# Positional rename, not a text match: the source workbook repeats the header
# text "Especie" and "APS" for adjacent code/name column pairs, and its accented
# characters are not reliably stable across exports. Column count and order are
# the real contract; the words above them are cosmetic.
NORMALIZED_COLUMNS = (
    "competencia_indeferimento",
    "especie_codigo",
    "especie_nome",
    "motivo_indeferimento",
    "dt_nascimento",
    "sexo",
    "clientela",
    "forma_filiacao",
    "uf",
    "dt_indeferimento",
    "ramo_atividade",
    "aps_codigo",
    "aps_nome",
    "dt_der",
)
_HEADER_ROW_INDEX = 1
_BOM = "﻿"


class HttpResponse(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponse: ...


class InssIndeferidosConnector:
    """One month of Beneficios Indeferidos: an XLSX workbook.

    Row 0 of the sheet is a title, row 1 is the header, data starts at row 2.
    BigQuery `LOAD DATA FROM FILES` does not accept XLSX, so the workbook is
    converted to a semicolon-delimited CSV locally (streaming read via
    openpyxl's read_only mode -- the workbook is not held fully in memory as
    parsed objects) before this connector returns. `content_sha256` describes
    the converted CSV that RAW actually stores, not the original XLSX bytes.
    """

    dataset_id = "inss_beneficios_indeferidos"

    def __init__(
        self,
        *,
        session: HttpSession,
        resource: CkanResource,
        max_retries: int = 4,
        backoff_seconds: float = 2.0,
        request_timeout: float = 120.0,
    ) -> None:
        self._session = session
        self._resource = resource
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._request_timeout = request_timeout

    def discover(self) -> ResourceRef:
        return ResourceRef(
            dataset_id=self.dataset_id,
            resource_url=self._resource.url,
            resource_format="xlsx",
            resource_hash=None,
        )

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {
            "resource_id": self._resource.resource_id,
            "resource_name": self._resource.name,
            "last_modified": self._resource.last_modified or "",
        }

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        errors: list[str] = []

        def _fetch() -> HttpResponse:
            response = self._session.get(ref.resource_url, timeout=self._request_timeout)
            response.raise_for_status()
            return response

        response = retry_with_backoff(
            _fetch,
            max_attempts=self._max_retries,
            backoff_seconds=self._backoff_seconds,
            errors=errors,
        )
        data = _xlsx_to_csv(response.content)
        Path(dest).write_bytes(data)
        return DownloadResult(
            local_path=dest,
            content_sha256=hashlib.sha256(data).hexdigest(),
            http_status=response.status_code,
            bytes_downloaded=len(data),
            attempts=len(errors) + 1,
            attempt_errors=errors,
        )

    def validate(self, local_path: str) -> None:
        with open(local_path, encoding="utf-8") as handle:
            first_line = handle.readline().strip().lstrip(_BOM)
        actual = tuple(first_line.split(";"))
        if actual != NORMALIZED_COLUMNS:
            raise ConnectorError(
                f"unexpected CSV header: {actual!r} (expected {NORMALIZED_COLUMNS!r})"
            )

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        return ref.resource_hash != content_sha256


def _xlsx_to_csv(xlsx_bytes: bytes) -> bytes:
    workbook = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    try:
        sheet = workbook.active
        if sheet is None:
            raise ConnectorError("workbook has no active sheet")
        rows = sheet.iter_rows(values_only=True)
        next(rows, None)  # title row
        header = next(rows, None)
        if header is None or len(header) != len(NORMALIZED_COLUMNS):
            raise ConnectorError(
                f"unexpected header shape: {header!r} (expected {len(NORMALIZED_COLUMNS)} columns)"
            )
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
        writer.writerow(NORMALIZED_COLUMNS)
        for row in rows:
            writer.writerow("" if cell is None else str(cell) for cell in row)
        return buffer.getvalue().encode("utf-8")
    finally:
        workbook.close()
