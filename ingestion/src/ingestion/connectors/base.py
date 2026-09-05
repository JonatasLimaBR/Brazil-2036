from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ResourceRef:
    dataset_id: str
    resource_url: str
    resource_format: str
    resource_hash: str | None = None


@dataclass
class DownloadResult:
    local_path: str
    content_sha256: str
    http_status: int
    bytes_downloaded: int
    attempts: int
    attempt_errors: list[str] = field(default_factory=list)
    # BigQuery LOAD DATA encoding for this file's content ("UTF-8" or
    # "ISO-8859-1"). Detected cheaply from a small sample, not by decoding the
    # whole payload: some real INSS exports run into the multi-GB range, and a
    # full-file decode/re-encode to normalize legacy cp1252 to UTF-8 in Python
    # memory reliably MemoryErrors on files that size (confirmed live). Bytes
    # in cp1252's 0x80-0x9F range are rare enough in Portuguese text that
    # ISO-8859-1 (BigQuery's only non-UTF-8 CSV option) is an acceptable
    # stand-in and lets BigQuery's server-side loader do the decode instead.
    source_encoding: str = "UTF-8"


@runtime_checkable
class Connector(Protocol):
    def discover(self) -> ResourceRef: ...

    def metadata(self, ref: ResourceRef) -> dict[str, str]: ...

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult: ...

    def validate(self, local_path: str) -> None: ...

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool: ...


class ConnectorError(RuntimeError):
    pass


def retry_with_backoff[T](
    operation: Callable[[], T],
    *,
    max_attempts: int,
    backoff_seconds: float,
    errors: list[str],
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
            if attempt < max_attempts:
                sleep(backoff_seconds * attempt)
    raise ConnectorError(
        f"operation failed after {max_attempts} attempts: {last_exc}"
    ) from last_exc
