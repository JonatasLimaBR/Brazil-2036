from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from ingestion.connectors.base import (
    ConnectorError,
    DownloadResult,
    ResourceRef,
    retry_with_backoff,
)

# BCB SGS (Sistema Gerenciador de Series Temporais) -- public JSON API, no
# auth. Confirmed real by direct call during /design: series 4380 (PIB
# mensal, valores correntes, R$ milhoes) and 13762 (Divida Bruta do Governo
# Geral, % PIB, metodologia 2008+) both return live monthly data through
# 07/2026. `dados` (no date range) returns the full published history in one
# response -- small payload (one number per month), no pagination needed.
_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
_FILE_SCHEME = "file://"
_CSV_HEADER = ("reference_period", "value")


class HttpResponse(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponse: ...


@dataclass(frozen=True)
class BcbSgsSeries:
    series_code: int
    metric_id: str


class BcbSgsConnector:
    """Fetches one BCB SGS time series in full (Connector protocol).

    One instance per series: pib_mensal (4380) and divida_bruta_pib (13762)
    are two separate instances of this same class, not two classes -- the
    API shape is identical, only the series code/metric_id differ (DESIGN
    D1). Each keeps its own Bronze/Silver/Gold tables (BUILD_REPORT
    Autonomous Decision): a shared table per BCB dataset would force either
    a fabricated combined "resource" or provenance rows citing the wrong
    series URL for one of the two metrics.
    """

    def __init__(
        self,
        *,
        session: HttpSession,
        series: BcbSgsSeries,
        max_retries: int = 4,
        backoff_seconds: float = 2.0,
        request_timeout: float = 30.0,
    ) -> None:
        self._session = session
        self._series = series
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._request_timeout = request_timeout

    @property
    def dataset_id(self) -> str:
        return self._series.metric_id

    def discover(self) -> ResourceRef:
        url = _BASE_URL.format(code=self._series.series_code) + "?formato=json"
        return ResourceRef(
            dataset_id=self.dataset_id, resource_url=url, resource_format="json", resource_hash=None
        )

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {
            "series_code": str(self._series.series_code),
            "metric_id": self._series.metric_id,
        }

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        # file:// lets integration tests exercise the real pipeline against
        # real BigQuery without depending on the live BCB API being reachable
        # from CI (same principle as FiscalUniaoConnector.download).
        if ref.resource_url.startswith(_FILE_SCHEME):
            data = Path(ref.resource_url[len(_FILE_SCHEME) :]).read_bytes()
            Path(dest).write_bytes(data)
            return DownloadResult(
                local_path=dest,
                content_sha256=hashlib.sha256(data).hexdigest(),
                http_status=200,
                bytes_downloaded=len(data),
                attempts=1,
                attempt_errors=[],
            )

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
        with open(local_path, "rb") as handle:
            _parse_series(handle.read(), series_code=self._series.series_code)

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        return ref.resource_hash != content_sha256


def build_default_connector(session: HttpSession, *, series: BcbSgsSeries) -> BcbSgsConnector:
    return BcbSgsConnector(session=session, series=series)


def parse_to_long_csv(json_bytes: bytes, *, series_code: int) -> bytes:
    """Turns the BCB SGS JSON array into the (reference_period, value) CSV
    Bronze can LOAD DATA from. metric_id and state_ibge_code ('BR' sentinel,
    same convention as fiscal_uniao) are added by the Silver SQL, not here --
    each connector instance covers exactly one metric_id, known at
    SQL-authoring time.
    """
    series = _parse_series(json_bytes, series_code=series_code)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADER)
    for period, value in series:
        writer.writerow((period.isoformat(), str(value)))
    return buffer.getvalue().encode("utf-8")


def _parse_series(json_bytes: bytes, *, series_code: int) -> list[tuple[dt.date, Decimal]]:
    try:
        rows = json.loads(json_bytes)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"BCB SGS {series_code}: response is not valid JSON") from exc
    if not isinstance(rows, list) or not rows:
        raise ConnectorError(f"BCB SGS {series_code}: empty or malformed payload")

    series: list[tuple[dt.date, Decimal]] = []
    for row in rows:
        if not isinstance(row, dict) or "data" not in row or "valor" not in row:
            raise ConnectorError(f"BCB SGS {series_code}: unexpected row shape {row!r}")
        try:
            period = dt.datetime.strptime(row["data"], "%d/%m/%Y").date().replace(day=1)
            value = Decimal(str(row["valor"]))
        except (ValueError, ArithmeticError) as exc:
            raise ConnectorError(f"BCB SGS {series_code}: unparseable row {row!r}") from exc
        series.append((period, value))
    return series
