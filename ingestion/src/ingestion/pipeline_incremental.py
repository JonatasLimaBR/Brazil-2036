from __future__ import annotations

import datetime as dt
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ingestion import bronze, provenance, registry
from ingestion.bigquery_io import BigQueryClient, run_sql
from ingestion.connectors.base import Connector
from ingestion.contract import DataContract
from ingestion.raw import StorageClient, write_raw
from ingestion.sql_render import render_file

_GOLD_KEY_FIELDS = ("state_ibge_code", "reference_date")
_GOLD_VALUE_FIELD = "value"

_REPO_INGESTION_ROOT = Path(__file__).resolve().parents[1].parent
_SQL_DIR = _REPO_INGESTION_ROOT / "sql"


class IncrementalPipelineError(RuntimeError):
    pass


class Quarantined(IncrementalPipelineError):
    pass


@dataclass(frozen=True)
class IncrementalConfig:
    dataset_id: str
    br2036_domain: str
    br2036_module: str
    catalog_url: str
    organization: str
    license: str
    metric_id: str
    unit: str
    contract_path: Path
    gcp_project: str
    raw_bucket: str
    raw_prefix: str
    bq_dataset_control: str
    bq_dataset_bronze: str
    bq_dataset_silver: str
    bq_dataset_gold: str
    bronze_table: str
    bronze_columns: tuple[str, ...]
    field_delimiter: str
    silver_model: str
    gold_model: str
    ckan_base_url: str
    ckan_package_id: str
    file_ext: str = "csv"


def load_incremental_config(path: str | Path) -> IncrementalConfig:
    config_path = Path(path)
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    base_dir = config_path.parent
    contract_path = (base_dir / raw["contract_path"]).resolve()
    if not contract_path.exists():
        contract_path = (_REPO_INGESTION_ROOT / raw["contract_path"]).resolve()

    def _env(name: str, default: str) -> str:
        return os.environ.get(name, default)

    return IncrementalConfig(
        dataset_id=raw["dataset_id"],
        br2036_domain=raw["br2036_domain"],
        br2036_module=raw["br2036_module"],
        catalog_url=raw.get("catalog_url", ""),
        organization=raw["organization"],
        license=raw["license"],
        metric_id=raw["metric_id"],
        unit=raw["unit"],
        contract_path=contract_path,
        gcp_project=_env("GCP_PROJECT", raw.get("gcp_project", "")),
        raw_bucket=_env("RAW_BUCKET", raw.get("raw_bucket", "")),
        raw_prefix=raw["raw_prefix"],
        bq_dataset_control=_env("BQ_DATASET_CONTROL", raw["bq_dataset_control"]),
        bq_dataset_bronze=_env("BQ_DATASET_BRONZE", raw["bq_dataset_bronze"]),
        bq_dataset_silver=_env("BQ_DATASET_SILVER", raw["bq_dataset_silver"]),
        bq_dataset_gold=_env("BQ_DATASET_GOLD", raw["bq_dataset_gold"]),
        bronze_table=raw["bronze_table"],
        bronze_columns=tuple(raw["bronze_columns"]),
        field_delimiter=raw["field_delimiter"],
        silver_model=raw["silver_model"],
        gold_model=raw["gold_model"],
        ckan_base_url=raw["ckan_base_url"],
        ckan_package_id=raw["ckan_package_id"],
        file_ext=raw.get("file_ext", "csv"),
    )


@dataclass
class IncrementalRunResult:
    run_id: str
    status: str
    reference_period: dt.date
    bronze_rows: int = 0
    provenance_rows: int = 0
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


def run(
    config: IncrementalConfig,
    *,
    connector: Connector,
    storage_client: StorageClient,
    bq_client: BigQueryClient,
    reference_period: dt.date,
    sql_dir: Path | None = None,
) -> IncrementalRunResult:
    run_id = uuid.uuid4().hex
    result = IncrementalRunResult(
        run_id=run_id, status="started", reference_period=reference_period
    )
    sql_dir = sql_dir or _SQL_DIR
    contract = DataContract.load(config.contract_path)

    ref = connector.discover()
    registry.upsert_dataset_registry(
        bq_client,
        project=config.gcp_project,
        dataset_control=config.bq_dataset_control,
        table="dataset_registry",
        entry={
            "dataset_id": config.dataset_id,
            "resource_url": ref.resource_url,
            "source_url": config.catalog_url,
            "resource_format": ref.resource_format,
            "organization": config.organization,
            "license": config.license,
            "update_frequency": "monthly",
            "br2036_domain": config.br2036_domain,
            "br2036_module": config.br2036_module,
        },
    )

    with tempfile.TemporaryDirectory() as tmp:
        local = str(Path(tmp) / f"resource.{config.file_ext}")
        download = connector.download(ref, local)
        connector.validate(local)
        payload = Path(local).read_bytes()

    if not connector.checkpoint(ref, download.content_sha256):
        result.status = "no-op"
        result.notes = ["resource hash unchanged since last run"]
        return result

    raw_object = write_raw(
        storage_client,
        bucket_name=config.raw_bucket,
        prefix=f"{config.raw_prefix}/{config.dataset_id}",
        data=payload,
        source_uri=ref.resource_url,
        http_status=download.http_status,
        file_ext=config.file_ext,
    )

    load = bronze.load_partition(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
        columns=config.bronze_columns,
        field_delimiter=config.field_delimiter,
        reference_period=reference_period,
        raw_uri=raw_object.uri,
        source_uri=ref.resource_url,
        row_hash=raw_object.content_sha256,
    )
    result.bronze_rows = load.rows_loaded

    observed_columns = bronze.source_columns(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
    )
    bronze_check = contract.check_bronze_schema(observed_columns)
    if not bronze_check.ok:
        result.status = "quarantined"
        result.notes = list(bronze_check.violations)
        raise Quarantined(
            f"run {run_id}: bronze schema drift, nothing promoted: {bronze_check.violations}"
        )

    placeholders = {
        "project": config.gcp_project,
        "bq_dataset_control": config.bq_dataset_control,
        "bq_dataset_bronze": config.bq_dataset_bronze,
        "bq_dataset_silver": config.bq_dataset_silver,
        "bq_dataset_gold": config.bq_dataset_gold,
        "bronze_table": config.bronze_table,
        "metric_id": config.metric_id,
        "unit": config.unit,
        "reference_period": reference_period.isoformat(),
    }
    run_sql(bq_client, render_file(sql_dir / "silver" / f"{config.silver_model}.sql", placeholders))
    run_sql(bq_client, render_file(sql_dir / "gold" / f"{config.gold_model}.sql", placeholders))

    result.provenance_rows = provenance.write_from_gold(
        bq_client,
        project=config.gcp_project,
        dataset_gold=config.bq_dataset_gold,
        gold_table=config.gold_model,
        provenance_table="metric_provenance",
        metric_id=config.metric_id,
        reference_date=reference_period,
        source_url=ref.resource_url,
        silver_transform=f"sql/silver/{config.silver_model}.sql",
        silver_transform_version=run_id,
        bronze_object=raw_object.uri,
        catalog_dataset_id=config.dataset_id,
        producing_organization=config.organization,
        run_id=run_id,
    )

    period_lit = reference_period.isoformat()
    gold_fqtn = f"`{config.gcp_project}.{config.bq_dataset_gold}.{config.gold_model}`"
    gold_rows = run_sql(
        bq_client,
        f"SELECT * FROM {gold_fqtn} WHERE reference_date = DATE('{period_lit}')",
    )
    gold_check = contract.check_gold_period(
        gold_rows,
        key_fields=_GOLD_KEY_FIELDS,
        value_field=_GOLD_VALUE_FIELD,
        provenance_row_count=result.provenance_rows,
    )
    gold_check.raise_if_broken()

    result.status = "ok"
    return result
