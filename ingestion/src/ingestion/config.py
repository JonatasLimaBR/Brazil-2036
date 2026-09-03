from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPO_INGESTION_ROOT = _PACKAGE_ROOT.parents[1]


@dataclass(frozen=True)
class Config:
    dataset_id: str
    br2036_domain: str
    br2036_module: str
    resource_url: str
    resource_format: str
    catalog_url: str
    metric_id: str
    unit: str
    data_class: str
    contract_path: Path
    uf_ibge_path: Path
    gcp_project: str
    raw_bucket: str
    raw_prefix: str
    bq_dataset_control: str
    bq_dataset_bronze: str
    bq_dataset_silver: str
    bq_dataset_gold: str
    bronze_table: str
    silver_table: str
    gold_table: str
    provenance_table: str
    uf_ibge_table: str
    registry_table: str
    download_max_retries: int
    download_backoff_seconds: float

    def placeholders(self) -> dict[str, str]:
        return {
            "project": self.gcp_project,
            "bq_dataset_control": self.bq_dataset_control,
            "bq_dataset_bronze": self.bq_dataset_bronze,
            "bq_dataset_silver": self.bq_dataset_silver,
            "bq_dataset_gold": self.bq_dataset_gold,
            "bronze_table": self.bronze_table,
            "silver_table": self.silver_table,
            "gold_table": self.gold_table,
            "uf_ibge_table": self.uf_ibge_table,
            "metric_id": self.metric_id,
            "unit": self.unit,
            "data_class": self.data_class,
        }


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(path) if path else _PACKAGE_ROOT / "config.yaml"
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    base_dir = config_path.parent
    contract_path = (base_dir / raw["contract_path"]).resolve()
    if not contract_path.exists():
        contract_path = (_REPO_INGESTION_ROOT / raw["contract_path"]).resolve()
    uf_ibge_path = (base_dir / raw["uf_ibge_path"]).resolve()
    if not uf_ibge_path.exists():
        uf_ibge_path = (_REPO_INGESTION_ROOT / raw["uf_ibge_path"]).resolve()

    return Config(
        dataset_id=raw["dataset_id"],
        br2036_domain=raw["br2036_domain"],
        br2036_module=raw["br2036_module"],
        resource_url=raw["resource_url"],
        resource_format=raw["resource_format"],
        catalog_url=raw.get("catalog_url", ""),
        metric_id=raw["metric_id"],
        unit=raw["unit"],
        data_class=raw["data_class"],
        contract_path=contract_path,
        uf_ibge_path=uf_ibge_path,
        gcp_project=os.environ.get("GCP_PROJECT", raw.get("gcp_project", "")),
        raw_bucket=os.environ.get("RAW_BUCKET", raw.get("raw_bucket", "")),
        raw_prefix=raw["raw_prefix"],
        bq_dataset_control=raw["bq_dataset_control"],
        bq_dataset_bronze=raw["bq_dataset_bronze"],
        bq_dataset_silver=raw["bq_dataset_silver"],
        bq_dataset_gold=raw["bq_dataset_gold"],
        bronze_table=raw["bronze_table"],
        silver_table=raw["silver_table"],
        gold_table=raw["gold_table"],
        provenance_table=raw["provenance_table"],
        uf_ibge_table=raw["uf_ibge_table"],
        registry_table=raw["registry_table"],
        download_max_retries=int(raw["download_max_retries"]),
        download_backoff_seconds=float(raw["download_backoff_seconds"]),
    )
