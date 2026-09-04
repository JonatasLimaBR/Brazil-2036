from __future__ import annotations

import datetime as dt
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ingestion import pipeline_incremental, registry
from ingestion.bigquery_io import BigQueryClient, run_sql
from ingestion.ckan import CkanResource, HttpGet, list_resources
from ingestion.connectors.base import Connector
from ingestion.pipeline_incremental import IncrementalConfig
from ingestion.raw import StorageClient

logger = logging.getLogger("ingestion.backfill")

_PERIOD_PATTERN = re.compile(r"(20\d{2})(0[1-9]|1[0-2])")
_UF_IBGE_PATH = Path(__file__).resolve().parents[1].parent / "reference" / "uf_ibge.csv"


class BackfillError(RuntimeError):
    pass


@dataclass
class ResourceOutcome:
    resource_id: str
    reference_period: dt.date | None
    status: str
    detail: str = ""


@dataclass
class BackfillResult:
    dataset_id: str
    outcomes: list[ResourceOutcome] = field(default_factory=list)

    @property
    def loaded(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "ok")

    @property
    def skipped(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "skipped-already-loaded")

    @property
    def failed(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "failed")


def parse_period_from_url(url: str) -> dt.date:
    match = _PERIOD_PATTERN.search(url)
    if not match:
        raise ValueError(f"could not find a YYYYMM period in resource URL: {url!r}")
    year, month = int(match.group(1)), int(match.group(2))
    return dt.date(year, month, 1)


def loaded_periods(
    bq_client: BigQueryClient, *, project: str, dataset_bronze: str, table: str
) -> set[str]:
    rows = run_sql(
        bq_client,
        f"SELECT partition_id FROM `{project}.{dataset_bronze}`.INFORMATION_SCHEMA.PARTITIONS "
        f"WHERE table_name = '{table}' AND partition_id != '__NULL__'",
    )
    return {str(r["partition_id"]) for r in rows}


def run_backfill(
    *,
    ckan_session: HttpGet,
    config: IncrementalConfig,
    connector_factory: Callable[[CkanResource], Connector],
    storage_client: StorageClient,
    bq_client: BigQueryClient,
) -> BackfillResult:
    result = BackfillResult(dataset_id=config.dataset_id)
    registry.ensure_uf_ibge(
        bq_client,
        project=config.gcp_project,
        dataset_control=config.bq_dataset_control,
        table="uf_ibge",
        csv_path=_UF_IBGE_PATH,
    )
    resources = list_resources(
        ckan_session, base_url=config.ckan_base_url, package_id=config.ckan_package_id
    )
    already = loaded_periods(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
    )

    for resource in resources:
        try:
            period = parse_period_from_url(resource.url)
        except ValueError as exc:
            result.outcomes.append(
                ResourceOutcome(resource.resource_id, None, "skipped-unparseable", str(exc))
            )
            continue

        partition_id = f"{period:%Y%m}01"
        if partition_id in already:
            result.outcomes.append(
                ResourceOutcome(resource.resource_id, period, "skipped-already-loaded")
            )
            continue

        connector = connector_factory(resource)
        try:
            run_result = pipeline_incremental.run(
                config,
                connector=connector,
                storage_client=storage_client,
                bq_client=bq_client,
                reference_period=period,
            )
        except Exception as exc:  # noqa: BLE001 -- 1 resource failing must not abort the backfill
            logger.exception("backfill: resource %s (%s) failed", resource.resource_id, period)
            result.outcomes.append(
                ResourceOutcome(resource.resource_id, period, "failed", str(exc))
            )
            continue

        result.outcomes.append(ResourceOutcome(resource.resource_id, period, run_result.status))

    return result
