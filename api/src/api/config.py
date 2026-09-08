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
    # DebtLab scenario persistence (ADR-059): br2036_control, not Gold -- this
    # is operational bookkeeping, never a quantitative-truth table.
    bq_dataset_control: str = ""
    debtlab_scenarios_table: str = "debtlab_scenarios"
    debtlab_base_metric_id: str = "divida_bruta_pib"
    # RAG_PROVENANCE_QA (ADR-061): retrieval + answer synthesis config.
    # similarity_threshold=0.45 is empirically calibrated (BUILD_REPORT), not
    # an arbitrary default -- live cosine distances against the real 11-note
    # corpus: genuinely relevant questions scored 0.30-0.42, genuinely
    # irrelevant ones scored 0.53-0.57, so 0.45 sits in the real gap.
    rag_corpus_table: str = "rag_knowledge_corpus"
    rag_embedding_model: str = "rag_embedding_model"
    rag_generative_model: str = "gemini-2.5-flash"
    rag_similarity_threshold: float = 0.45
    rag_top_k: int = 5
    # api-web.yml only sets GCP_PROJECT on the deployed service, not
    # GCP_REGION (the project has one region today) -- a plain config.yaml
    # default, same pattern as debtlab_base_metric_id above, not an env var
    # nothing sets.
    gcp_region: str = "southamerica-east1"

    @property
    def gold_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.gold_table}`"

    @property
    def provenance_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.provenance_table}`"

    @property
    def debtlab_scenarios_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_control}.{self.debtlab_scenarios_table}`"

    @property
    def rag_corpus_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.rag_corpus_table}`"

    @property
    def rag_embedding_model_fqtn(self) -> str:
        return f"`{self.gcp_project}.{self.bq_dataset_gold}.{self.rag_embedding_model}`"


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
        bq_dataset_control=raw.get("bq_dataset_control", ""),
        debtlab_scenarios_table=raw.get("debtlab_scenarios_table", "debtlab_scenarios"),
        debtlab_base_metric_id=raw.get("debtlab_base_metric_id", "divida_bruta_pib"),
        rag_corpus_table=raw.get("rag_corpus_table", "rag_knowledge_corpus"),
        rag_embedding_model=raw.get("rag_embedding_model", "rag_embedding_model"),
        rag_generative_model=raw.get("rag_generative_model", "gemini-2.5-flash"),
        rag_similarity_threshold=float(raw.get("rag_similarity_threshold", 0.45)),
        rag_top_k=int(raw.get("rag_top_k", 5)),
        gcp_region=raw.get("gcp_region", "southamerica-east1"),
    )
