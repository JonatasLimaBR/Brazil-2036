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
        status_code = response.status_code
        # Ativos runs up to ~1.2 GB compressed -- holding the compressed and
        # extracted copies alive together nearly doubles peak memory for no
        # reason once extraction is done (same real constraint as Emitidos).
        payload = response.content
        del response
        raw = (
            _extract_single_csv(payload, source=ref.resource_url)
            if ref.resource_format == "zip"
            else payload
        )
        del payload
        data = _normalize_header_delimiter(raw)
        del raw
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


_SAMPLE_SIZE = 65536


def _detect_encoding(data: bytes) -> str:
    # Confirmed live on a sibling dataset (Emitidos, 2023-06): the oldest real
    # INSS exports are not UTF-8 -- legacy cp1252, common in older Brazilian
    # government files; more recent months are UTF-8. Detected from a small
    # sample, not a full-file decode: Mantidos files run up to ~1.2 GB
    # compressed, and a full decode/re-encode to normalize encoding
    # reliably MemoryErrors on a file that size in a plain Python process
    # (confirmed live on Emitidos, same risk here). "ISO-8859-1" (BigQuery's
    # only non-UTF-8 CSV encoding option) is passed straight to LOAD DATA.
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


def _normalize_header_delimiter(raw: bytes) -> bytes:
    # Operates on the header line only (bytes, split on the first b"\n") --
    # the multi-GB body is never decoded or copied, only the header is
    # comma-vs-semicolon normalized and only that line is re-encoded.
    lines = raw.split(b"\n", 1)
    if len(lines) != 2:
        return raw
    header_bytes, rest = lines
    header = _decode_sample(header_bytes).strip().lstrip(_BOM)
    if "," in header and ";" not in header:
        header = header.replace(",", ";")
    return header.encode("utf-8") + b"\n" + rest
