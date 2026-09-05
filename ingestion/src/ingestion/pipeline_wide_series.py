from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Callable
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


class WideSeriesPipelineError(RuntimeError):
    pass


class Quarantined(WideSeriesPipelineError):
    pass


@dataclass(frozen=True)
class WideSeriesConfig:
    dataset_id: str
    br2036_domain: str
    br2036_module: str
    catalog_url: str
    organization: str
    license: str
    metric_ids: tuple[str, ...]
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
    allow_negative_metric_ids: tuple[str, ...] = ()


def load_wide_series_config(path: str | Path) -> WideSeriesConfig:
    config_path = Path(path)
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    base_dir = config_path.parent
    contract_path = (base_dir / raw["contract_path"]).resolve()
    if not contract_path.exists():
        contract_path = (_REPO_INGESTION_ROOT / raw["contract_path"]).resolve()

    def _env(name: str, default: str) -> str:
        return os.environ.get(name, default)

    return WideSeriesConfig(
        dataset_id=raw["dataset_id"],
        br2036_domain=raw["br2036_domain"],
        br2036_module=raw["br2036_module"],
        catalog_url=raw.get("catalog_url", ""),
        organization=raw["organization"],
        license=raw["license"],
        metric_ids=tuple(raw["metric_ids"]),
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
        allow_negative_metric_ids=tuple(raw.get("allow_negative_metric_ids", ())),
    )


@dataclass
class WideSeriesRunResult:
    run_id: str
    status: str
    gold_rows: int = 0
    provenance_rows: int = 0
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


def run(
    config: WideSeriesConfig,
    *,
    connector: Connector,
    storage_client: StorageClient,
    bq_client: BigQueryClient,
    parse_to_long_csv: Callable[[bytes], bytes],
    sql_dir: Path | None = None,
) -> WideSeriesRunResult:
    # Unlike pipeline.py (1 file = the entire, never-changing history) and
    # pipeline_incremental.py (1 call = 1 new resource for 1 period), this
    # source republishes its FULL history in the same file every run. So Bronze
    # is a whole-table CREATE OR REPLACE (safe: this table belongs only to this
    # dataset, not shared) rather than a partitioned accumulation, and Gold /
    # provenance are rewritten in full for each metric_id every run rather than
    # for one period at a time.
    run_id = uuid.uuid4().hex
    result = WideSeriesRunResult(run_id=run_id, status="started")
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
        local = str(Path(tmp) / f"resource.{ref.resource_format}")
        download = connector.download(ref, local)
        connector.validate(local)
        original_payload = Path(local).read_bytes()

    if not connector.checkpoint(ref, download.content_sha256):
        result.status = "no-op"
        result.notes = ["resource hash unchanged since last run"]
        return result

    # D6: RAW keeps the original artifact exactly as published, unmodified.
    raw_original = write_raw(
        storage_client,
        bucket_name=config.raw_bucket,
        prefix=f"{config.raw_prefix}/{config.dataset_id}",
        data=original_payload,
        source_uri=ref.resource_url,
        http_status=download.http_status,
        file_ext=ref.resource_format,
    )

    # Bronze cannot LOAD DATA directly from XLSX, so the pivoted long-format
    # CSV is written to RAW as a second, separately content-addressed object --
    # the artifact Bronze actually reads -- rather than replacing the original
    # (the deviation accepted for INSS Indeferidos, W1).
    long_csv = parse_to_long_csv(original_payload)
    raw_csv = write_raw(
        storage_client,
        bucket_name=config.raw_bucket,
        prefix=f"{config.raw_prefix}/{config.dataset_id}",
        data=long_csv,
        source_uri=ref.resource_url,
        http_status=download.http_status,
        file_ext="csv",
    )

    load = bronze.load(
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
        raw_uri=raw_csv.uri,
        source_uri=ref.resource_url,
        row_hash=raw_original.content_sha256,
        columns=config.bronze_columns,
        field_delimiter=config.field_delimiter,
    )
    result.notes = [f"bronze rows loaded: {load.rows_loaded}"]

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
        "unit": config.unit,
    }
    run_sql(bq_client, render_file(sql_dir / "silver" / f"{config.silver_model}.sql", placeholders))
    run_sql(bq_client, render_file(sql_dir / "gold" / f"{config.gold_model}.sql", placeholders))

    gold_fqtn = f"`{config.gcp_project}.{config.bq_dataset_gold}.{config.gold_model}`"
    total_gold_rows = 0
    total_provenance_rows = 0
    for metric_id in config.metric_ids:
        metric_rows = run_sql(
            bq_client,
            f"SELECT * FROM {gold_fqtn} WHERE metric_id = '{metric_id}'",
        )
        provenance_rows = provenance.write_from_gold(
            bq_client,
            project=config.gcp_project,
            dataset_gold=config.bq_dataset_gold,
            gold_table=config.gold_model,
            provenance_table="metric_provenance",
            metric_id=metric_id,
            reference_date=None,
            source_url=ref.resource_url,
            silver_transform=f"sql/silver/{config.silver_model}.sql",
            silver_transform_version=run_id,
            bronze_object=raw_csv.uri,
            catalog_dataset_id=config.dataset_id,
            producing_organization=config.organization,
            run_id=run_id,
        )
        gold_check = contract.check_gold_period(
            metric_rows,
            key_fields=_GOLD_KEY_FIELDS,
            value_field=_GOLD_VALUE_FIELD,
            provenance_row_count=provenance_rows,
            allow_negative=metric_id in config.allow_negative_metric_ids,
        )
        gold_check.raise_if_broken()
        total_gold_rows += len(metric_rows)
        total_provenance_rows += provenance_rows

    result.gold_rows = total_gold_rows
    result.provenance_rows = total_provenance_rows
    result.status = "ok"
    return result
