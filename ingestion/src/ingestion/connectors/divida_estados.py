from __future__ import annotations

import hashlib
from typing import Protocol

from ingestion.connectors.base import (
    ConnectorError,
    DownloadResult,
    ResourceRef,
    retry_with_backoff,
)

EXPECTED_HEADER = "UF;ANO;VALOR"
_BOM = "﻿"


class HttpResponse(Protocol):
    status_code: int
    content: bytes
    headers: dict[str, str]

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponse: ...

    def head(self, url: str, timeout: float, allow_redirects: bool) -> HttpResponse: ...


class DividaEstadosConnector:
    def __init__(
        self,
        *,
        session: HttpSession,
        resource_url: str,
        dataset_id: str = "divida_consolidada_estados",
        resource_format: str = "csv",
        known_hash: str | None = None,
        max_retries: int = 4,
        backoff_seconds: float = 2.0,
        request_timeout: float = 30.0,
    ) -> None:
        self._session = session
        self._resource_url = resource_url
        self._dataset_id = dataset_id
        self._resource_format = resource_format
        self._known_hash = known_hash
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._request_timeout = request_timeout

    def discover(self) -> ResourceRef:
        return ResourceRef(
            dataset_id=self._dataset_id,
            resource_url=self._resource_url,
            resource_format=self._resource_format,
            resource_hash=self._known_hash,
        )

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        response = self._session.head(
            ref.resource_url, timeout=self._request_timeout, allow_redirects=True
        )
        response.raise_for_status()
        headers = {k.lower(): v for k, v in response.headers.items()}
        return {
            "content_type": headers.get("content-type", ""),
            "content_length": headers.get("content-length", ""),
            "last_modified": headers.get("last-modified", ""),
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
        data = response.content
        with open(dest, "wb") as handle:
            handle.write(data)
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
