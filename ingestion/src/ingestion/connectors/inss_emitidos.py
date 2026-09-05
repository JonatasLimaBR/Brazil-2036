from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Protocol

from ingestion.ckan import CkanResource
from ingestion.connectors.base import (
    ConnectorError,
    DownloadResult,
    ResourceRef,
    retry_with_backoff,
)

EXPECTED_HEADER = (
    "despacho;sexo_recebedor;clientela;tipo_beneficio;uf;meio_pagamento;banco;"
    "municipio;municipio_resid;vl_liquido;ramo_atividade;Dt_Inicio_Validade;"
    "especie;especie_codigo_nome"
)
_BOM = "﻿"
_FILE_SCHEME = "file://"


class HttpResponse(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponse: ...


class InssEmitidosConnector:
    """One month of Beneficios Emitidos: a ZIP containing exactly one CSV."""

    dataset_id = "inss_beneficios_emitidos"

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
            resource_format="zip",
            resource_hash=None,
        )

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {
            "resource_id": self._resource.resource_id,
            "resource_name": self._resource.name,
            "last_modified": self._resource.last_modified or "",
        }

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        if ref.resource_url.startswith(_FILE_SCHEME):
            return self._download_file(ref, dest)
        return self._download_http(ref, dest)

    def _download_file(self, ref: ResourceRef, dest: str) -> DownloadResult:
        # Test/CI fixture path: the fixture is already a plain CSV (not
        # zipped), matching the same file:// convention DividaEstadosConnector
        # uses for the debt dataset's fixture.
        source = Path(ref.resource_url[len(_FILE_SCHEME) :])
        data = source.read_bytes()
        Path(dest).write_bytes(data)
        return DownloadResult(
            local_path=dest,
            content_sha256=hashlib.sha256(data).hexdigest(),
            http_status=200,
            bytes_downloaded=len(data),
            attempts=1,
            attempt_errors=[],
        )

    def _download_http(self, ref: ResourceRef, dest: str) -> DownloadResult:
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
        status_code = response.status_code
        # Files run up to ~7+ GB decompressed; holding the compressed ZIP
        # bytes alive alongside the extracted CSV nearly doubles peak memory
        # for no reason once extraction is done, and this is a real
        # constraint, not a hypothetical one (confirmed live: a full-file
        # decode on top of this combination MemoryError'd on a 16 GB machine).
        zip_bytes = response.content
        del response
        data = _extract_single_csv(zip_bytes, source=ref.resource_url)
        del zip_bytes
        encoding = _detect_encoding(data)
        Path(dest).write_bytes(data)
        return DownloadResult(
            local_path=dest,
            content_sha256=hashlib.sha256(data).hexdigest(),
            http_status=status_code,
            bytes_downloaded=len(data),
            attempts=len(errors) + 1,
            attempt_errors=errors,
            source_encoding=encoding,
        )

    def validate(self, local_path: str) -> None:
        with open(local_path, "rb") as handle:
            first_line_bytes = handle.readline()
        first_line = _decode_sample(first_line_bytes).strip().lstrip(_BOM)
        if first_line != EXPECTED_HEADER:
            raise ConnectorError(
                f"unexpected CSV header: {first_line!r} (expected {EXPECTED_HEADER!r})"
            )

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        return ref.resource_hash != content_sha256


def _extract_single_csv(zip_bytes: bytes, *, source: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise ConnectorError(
                f"expected exactly 1 file inside ZIP from {source!r}, found {names}"
            )
        return archive.read(names[0])


_SAMPLE_SIZE = 65536


def _detect_encoding(data: bytes) -> str:
    # Confirmed live: the oldest real Emitidos file (2023-06) is not UTF-8 --
    # legacy cp1252, common in older Brazilian government exports; more recent
    # months are UTF-8. Detected from a small sample, not a full-file decode:
    # a 7+ GB file's decode (even just to validate, encoding kept or not)
    # reliably MemoryErrors in a plain Python process (confirmed live).
    # "ISO-8859-1" (BigQuery's only non-UTF-8 CSV encoding option) is passed
    # straight to LOAD DATA so BigQuery's server-side loader decodes it
    # instead of this process re-encoding gigabytes in memory.
    try:
        data[:_SAMPLE_SIZE].decode("utf-8")
        return "UTF-8"
    except UnicodeDecodeError:
        return "ISO-8859-1"


def _decode_sample(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")
