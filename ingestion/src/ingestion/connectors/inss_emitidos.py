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
        data = _extract_single_csv(response.content, source=ref.resource_url)
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
