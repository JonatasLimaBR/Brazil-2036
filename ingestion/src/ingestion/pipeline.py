from __future__ import annotations

import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ingestion import bronze, provenance, registry
from ingestion.bigquery_io import BigQueryClient, run_sql, scalar
from ingestion.config import Config
from ingestion.connectors.base import Connector
from ingestion.connectors.divida_estados import DividaEstadosConnector
from ingestion.contract import DataContract
from ingestion.raw import StorageClient, write_raw
from ingestion.sql_render import render_file

logger = logging.getLogger("ingestion.pipeline")

_SQL_DIR = Path(__file__).resolve().parents[1].parent / "sql"


class PipelineError(RuntimeError):
    pass


class Quarantined(PipelineError):
    pass


@dataclass
class RunResult:
    run_id: str
    status: str
    reference_year: int | None = None
    gold_rows: int = 0
    provenance_rows: int = 0
    notes: list[str] = field(default_factory=list)


def run(
    config: Config,
    *,
    connector: Connector,
    storage_client: StorageClient,
    bq_client: BigQueryClient,
    sql_dir: Path | None = None,
) -> RunResult:
    run_id = uuid.uuid4().hex
    result = RunResult(run_id=run_id, status="started")
    sql_dir = sql_dir or _SQL_DIR
    contract = DataContract.load(config.contract_path)

    registry.ensure_uf_ibge(
        bq_client,
        project=config.gcp_project,
        dataset_control=config.bq_dataset_control,
        table=config.uf_ibge_table,
        csv_path=config.uf_ibge_path,
    )
    registry.upsert_dataset_registry(
        bq_client,
        project=config.gcp_project,
        dataset_control=config.bq_dataset_control,
        table=config.registry_table,
        entry={
            "dataset_id": config.dataset_id,
            "resource_url": config.resource_url,
            "source_url": config.catalog_url,
            "resource_format": config.resource_format,
            "organization": "COREM / STN",
            "license": "ODbL",
            "update_frequency": "annual",
            "br2036_domain": config.br2036_domain,
            "br2036_module": config.br2036_module,
        },
    )

    ref = connector.discover()
    with tempfile.TemporaryDirectory() as tmp:
        local = str(Path(tmp) / "resource.csv")
        download = connector.download(ref, local)
        connector.validate(local)
        payload = Path(local).read_bytes()

    if not connector.checkpoint(ref, download.content_sha256):
        result.status = "no-op"
        result.notes.append("resource hash unchanged since last run")
        return result

    raw_object = write_raw(
        storage_client,
        bucket_name=config.raw_bucket,
        prefix=config.raw_prefix,
        data=payload,
        source_uri=config.resource_url,
        http_status=download.http_status,
    )

    load = bronze.load(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
        raw_uri=raw_object.uri,
        source_uri=config.resource_url,
        row_hash=raw_object.content_sha256,
    )

    observed = bronze.source_columns(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
    )
    bronze_check = contract.check_bronze_schema(observed)
    if not bronze_check.ok:
        result.status = "quarantined"
        result.notes.extend(bronze_check.violations)
        raise Quarantined(
            f"run {run_id}: bronze schema drift, nothing promoted: {bronze_check.violations}"
        )

    placeholders = config.placeholders()
    run_sql(bq_client, render_file(sql_dir / "silver" / "debt_state.sql", placeholders))

    silver_fqtn = (
        f"`{config.gcp_project}.{config.bq_dataset_silver}.{config.silver_table}`"
    )
    silver_count = scalar(bq_client, f"SELECT COUNT(*) FROM {silver_fqtn}")
    if int(silver_count or 0) != load.rows_loaded:
        raise PipelineError(
            f"run {run_id}: territorial mapping lost rows "
            f"(bronze {load.rows_loaded} -> silver {silver_count})"
        )

    run_sql(
        bq_client,
        render_file(sql_dir / "gold" / "gold_debt_state_current.sql", placeholders),
    )

    gold_fqtn = f"`{config.gcp_project}.{config.bq_dataset_gold}.{config.gold_table}`"
    reference_year = int(
        scalar(bq_client, f"SELECT MAX(reference_year) FROM {gold_fqtn}") or 0
    )
    result.reference_year = reference_year

    gold_rows = run_sql(
        bq_client,
        f"SELECT metric_id, state_ibge_code, reference_year, reference_date, value, unit "
        f"FROM {gold_fqtn} WHERE reference_year = {reference_year}",
    )
    result.gold_rows = len(gold_rows)

    result.provenance_rows = provenance.write_from_gold(
        bq_client,
        project=config.gcp_project,
        dataset_gold=config.bq_dataset_gold,
        gold_table=config.gold_table,
        provenance_table=config.provenance_table,
        reference_year=reference_year,
        source_url=config.resource_url,
        silver_transform="sql/silver/debt_state.sql",
        silver_transform_version=run_id,
        bronze_object=raw_object.uri,
        catalog_dataset_id=config.dataset_id,
        producing_organization="COREM / STN",
        run_id=run_id,
    )

    gold_check = contract.check_gold(
        gold_rows,
        latest_reference_year=reference_year,
        provenance_row_count=result.provenance_rows,
    )
    gold_check.raise_if_broken()

    result.status = "ok"
    return result


def build_default_connector(config: Config) -> DividaEstadosConnector:
    import requests

    from ingestion.connectors.divida_estados import HttpSession

    return DividaEstadosConnector(
        session=cast("HttpSession", requests.Session()),
        resource_url=config.resource_url,
        dataset_id=config.dataset_id,
        resource_format=config.resource_format,
        max_retries=config.download_max_retries,
        backoff_seconds=config.download_backoff_seconds,
    )
