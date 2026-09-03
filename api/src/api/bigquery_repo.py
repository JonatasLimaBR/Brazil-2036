from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from api.config import Config
from api.models import (
    DataClass,
    MetricResponse,
    ProvenanceResponse,
    ProvenanceSummary,
)

RunQuery = Callable[[str, Mapping[str, Any]], list[dict[str, Any]]]

_TRUST_STATUS = "source_only"


class BigQueryRepo:
    def __init__(self, config: Config, run_query: RunQuery) -> None:
        self._config = config
        self._run_query = run_query

    def latest_metric(self, metric_id: str, state_ibge_code: str) -> MetricResponse | None:
        gold = self._config.gold_fqtn
        rows = self._run_query(
            "SELECT state_ibge_code, value, unit, reference_year, "
            "CAST(reference_date AS STRING) AS reference_date, data_class "
            f"FROM {gold} "
            "WHERE metric_id = @metric_id AND state_ibge_code = @state "
            f"AND reference_year = (SELECT MAX(reference_year) FROM {gold} "
            "WHERE metric_id = @metric_id)",
            {"metric_id": metric_id, "state": state_ibge_code},
        )
        if not rows:
            return None
        row = rows[0]
        summary = self._provenance_summary(metric_id, state_ibge_code, row["reference_year"])
        if summary is None:
            return None
        return MetricResponse(
            metric_id=metric_id,
            state_ibge_code=row["state_ibge_code"],
            value=float(row["value"]),
            unit=row["unit"],
            reference_year=int(row["reference_year"]),
            reference_date=row["reference_date"],
            data_class=DataClass(row["data_class"]),
            provenance=summary,
        )

    def provenance(
        self, metric_id: str, state_ibge_code: str
    ) -> ProvenanceResponse | None:
        prov = self._config.provenance_fqtn
        rows = self._run_query(
            "SELECT metric_id, state_ibge_code, reference_year, "
            "CAST(reference_date AS STRING) AS reference_date, gold_object, "
            "silver_transform, silver_transform_version, bronze_object, "
            "source AS source_resource_url, catalog_dataset_id, producing_organization "
            f"FROM {prov} "
            "WHERE metric_id = @metric_id AND state_ibge_code = @state "
            f"AND reference_year = (SELECT MAX(reference_year) FROM {prov} "
            "WHERE metric_id = @metric_id)",
            {"metric_id": metric_id, "state": state_ibge_code},
        )
        if not rows:
            return None
        row = rows[0]
        return ProvenanceResponse(
            metric_id=row["metric_id"],
            state_ibge_code=row["state_ibge_code"],
            reference_year=int(row["reference_year"]),
            reference_date=row["reference_date"],
            gold_object=row["gold_object"],
            silver_transform=row["silver_transform"],
            silver_transform_version=row["silver_transform_version"],
            bronze_object=row["bronze_object"],
            source_resource_url=row["source_resource_url"],
            catalog_dataset_id=row["catalog_dataset_id"],
            producing_organization=row["producing_organization"],
            trust_status=_TRUST_STATUS,
        )

    def _provenance_summary(
        self, metric_id: str, state_ibge_code: str, reference_year: int
    ) -> ProvenanceSummary | None:
        prov = self._config.provenance_fqtn
        rows = self._run_query(
            f"SELECT source, CAST(reference_date AS STRING) AS reference_date FROM {prov} "
            "WHERE metric_id = @metric_id AND state_ibge_code = @state "
            "AND reference_year = @year",
            {"metric_id": metric_id, "state": state_ibge_code, "year": reference_year},
        )
        if not rows:
            return None
        return ProvenanceSummary(
            source=rows[0]["source"],
            reference_date=rows[0]["reference_date"],
            trust_status=_TRUST_STATUS,
        )


def build_bigquery_run_query(project: str) -> RunQuery:
    from google.cloud import bigquery

    client = bigquery.Client(project=project)

    def run_query(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        job_params = [
            bigquery.ScalarQueryParameter(
                name,
                "INT64" if isinstance(value, int) else "STRING",
                value,
            )
            for name, value in params.items()
        ]
        job_config = bigquery.QueryJobConfig(query_parameters=job_params)
        return [dict(row) for row in client.query(sql, job_config=job_config).result()]

    return run_query
