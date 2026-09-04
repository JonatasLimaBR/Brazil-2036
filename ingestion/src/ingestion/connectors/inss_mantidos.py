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

EXPECTED_COLUMNS = (
    "especie_beneficio",
    "cid10",
    "clientela",
    "sexo",
    "forma_filiacao",
    "motivo_cessacao_suspensao",
    "grupo_situacao",
    "municipio_titular",
    "uf",
    "vinculo_dependente",
    "dt_nascimento_titular",
    "dt_cessacao_beneficio",
    "dt_despacho_beneficio",
    "dt_inicio_beneficio",
    "ramo_atividade",
    "tipo_beneficio",
    "valor_renda_mensal",
)
_BOM = "﻿"


class HttpResponse(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponse: ...


class InssMantidosConnector:
    """One month of Beneficios Mantidos (Ativos/Suspensos/Cessados).

    The source publishes the header row comma-delimited but every data row
    semicolon-delimited -- a quirk confirmed against a real file, not assumed.
    The connector normalizes the whole output to semicolon-delimited so it
    loads with the same `field_delimiter=';'` convention as every other
    Bronze table in this project. The maintenance status (ativo/suspenso/
    cessado) is read from the `grupo_situacao` column in the data itself,
    not passed in by the caller -- the source already self-describes it.
    """

    dataset_id = "inss_beneficios_mantidos"

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
        fmt = "zip" if self._resource.url.lower().endswith(".zip") else "csv"
        return ResourceRef(
            dataset_id=self.dataset_id,
            resource_url=self._resource.url,
            resource_format=fmt,
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
        raw = (
            _extract_single_csv(response.content, source=ref.resource_url)
            if ref.resource_format == "zip"
            else response.content
        )
        data = _normalize_header_delimiter(raw)
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
        if actual != EXPECTED_COLUMNS:
            raise ConnectorError(
                f"unexpected CSV header: {actual!r} (expected {EXPECTED_COLUMNS!r})"
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


def _normalize_header_delimiter(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    lines = text.split("\n", 1)
    if len(lines) != 2:
        return raw
    header, rest = lines
    header = header.strip().lstrip(_BOM)
    if "," in header and ";" not in header:
        header = header.replace(",", ";")
    return f"{header}\n{rest}".encode()
