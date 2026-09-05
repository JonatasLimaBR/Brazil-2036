from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    gcp_project: str
    bq_dataset_gold: str
    gold_table: str
    provenance_table: str
    default_metric_id: str
    default_state_ibge_code: str
    # metric_id -> Gold table name, for metrics served by the national-total
    # route (INSS: PRD-005/SPEC-011) instead of the per-state debt route.
    # Additive: does not affect gold_table/default_metric_id above.
    metric_tables: Mapping[str, str] = field(default_factory=dict)

    @property
    def gold_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.gold_table}`"

    @property
    def provenance_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.provenance_table}`"


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(path) if path else _PACKAGE_ROOT / "config.yaml"
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return Config(
        gcp_project=os.environ.get("GCP_PROJECT", raw.get("gcp_project", "")),
        bq_dataset_gold=raw["bq_dataset_gold"],
        gold_table=raw["gold_table"],
        provenance_table=raw["provenance_table"],
        default_metric_id=raw["default_metric_id"],
        default_state_ibge_code=str(raw["default_state_ibge_code"]),
        metric_tables=dict(raw.get("metric_tables", {})),
    )
