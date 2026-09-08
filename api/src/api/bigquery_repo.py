from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from api.config import Config
from api.models import (
    DataClass,
    DebtLabScenarioBase,
    DebtLabScenarioRequest,
    DebtLabScenarioResponse,
    MetricResponse,
    NationalMetricResponse,
    ProvenanceResponse,
    ProvenanceSummary,
    YearlyDeterministic,
    YearlyPercentiles,
)


class RunQuery(Protocol):
    """Callable[[str, Mapping[str, Any]], list[dict[str, Any]]] plus an
    optional per-call maximum_bytes_billed override (DESIGN D5) -- a bare
    Callable alias can't express a defaulted keyword-only parameter, so this
    is a Protocol instead. Every existing 2-positional-arg call site keeps
    working unchanged; only debtlab's DDL/INSERT calls pass the override.
    """

    def __call__(
        self,
        sql: str,
        params: Mapping[str, Any],
        *,
        maximum_bytes_billed: int | None = ...,
    ) -> list[dict[str, Any]]: ...


_TRUST_STATUS = "source_only"

# br2036_control, not Gold (ADR-059) -- operational bookkeeping for
# simulator runs, same role as dataset_registry/metric_provenance.
_DEBTLAB_SCENARIOS_SCHEMA = (
    "scenario_id STRING, created_at TIMESTAMP, horizon_years INT64, "
    "base_reference_date DATE, base_divida_pib_pct FLOAT64, base_source STRING, "
    "assumptions_json STRING, engine_version STRING, seed INT64, n_iterations INT64, "
    "deterministic_trajectory_json STRING, percentiles_json STRING, data_class STRING"
)


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

    def provenance(self, metric_id: str, state_ibge_code: str) -> ProvenanceResponse | None:
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

    def latest_national_total(
        self, metric_id: str, gold_table: str
    ) -> NationalMetricResponse | None:
        # National aggregate (PRD-005 M03): sums value across every UF and
        # especie for the metric's most recent month. Additive to
        # latest_metric/gold_table above -- gold_table is resolved by the
        # caller from Config.metric_tables, one physical Gold table per
        # metric_id, so this never touches the debt route's table.
        #
        # NotFound is caught, not left to propagate: a metric_tables entry can
        # exist (e.g. Mantidos) before its backfill has ever run, so the Gold
        # table itself may not exist yet. Without this, that case 500s instead
        # of 404ing like every other "no data for this metric" case (found by
        # an independent /verify-spec review hitting the live endpoint).
        from google.api_core.exceptions import NotFound

        gold = f"`{self._config.gcp_project}.{self._config.bq_dataset_gold}.{gold_table}`"
        try:
            rows = self._run_query(
                "SELECT SUM(value) AS value, ANY_VALUE(unit) AS unit, "
                "CAST(MAX(reference_date) AS STRING) AS reference_date "
                f"FROM {gold} WHERE metric_id = @metric_id "
                f"AND reference_date = (SELECT MAX(reference_date) FROM {gold} "
                "WHERE metric_id = @metric_id)",
                {"metric_id": metric_id},
            )
        except NotFound:
            return None
        if not rows or rows[0]["value"] is None:
            return None
        row = rows[0]
        summary = self._national_provenance_summary(metric_id, row["reference_date"])
        if summary is None:
            return None
        return NationalMetricResponse(
            metric_id=metric_id,
            value=float(row["value"]),
            unit=row["unit"],
            reference_date=row["reference_date"],
            data_class=DataClass.observed,
            provenance=summary,
        )

    def debtlab_base(self) -> NationalMetricResponse | None:
        """Real, observed divida/PIB anchor for a new DebtLab scenario
        (ADR-059) -- reuses latest_national_total as-is, since
        divida_bruta_pib is served through the exact same generic
        /national route (config.metric_tables), zero new read code."""
        metric_id = self._config.debtlab_base_metric_id
        gold_table = self._config.metric_tables.get(metric_id)
        if gold_table is None:
            return None
        return self.latest_national_total(metric_id, gold_table)

    def create_debtlab_scenario(self, scenario: DebtLabScenarioResponse) -> None:
        control = self._config.debtlab_scenarios_fqtn
        # DDL/INSERT here, not a SELECT to be bounded by bytes scanned --
        # same rationale as bronze.py's LOAD DATA (ADR-057, DESIGN D5).
        self._run_query(
            f"CREATE TABLE IF NOT EXISTS {control} ({_DEBTLAB_SCENARIOS_SCHEMA})",
            {},
            maximum_bytes_billed=None,
        )
        self._run_query(
            f"INSERT INTO {control} "
            "(scenario_id, created_at, horizon_years, base_reference_date, "
            "base_divida_pib_pct, base_source, assumptions_json, engine_version, "
            "seed, n_iterations, deterministic_trajectory_json, percentiles_json, data_class) "
            "VALUES (@scenario_id, TIMESTAMP(@created_at), @horizon_years, "
            "DATE(@base_reference_date), @base_divida_pib_pct, @base_source, "
            "@assumptions_json, @engine_version, @seed, @n_iterations, "
            "@deterministic_trajectory_json, @percentiles_json, @data_class)",
            {
                "scenario_id": scenario.scenario_id,
                "created_at": scenario.created_at,
                "horizon_years": scenario.horizon_years,
                "base_reference_date": scenario.base.reference_date,
                "base_divida_pib_pct": scenario.base.divida_pib_pct,
                "base_source": scenario.base.source,
                "assumptions_json": scenario.assumptions.model_dump_json(),
                "engine_version": scenario.engine_version,
                "seed": scenario.seed,
                "n_iterations": scenario.n_iterations,
                "deterministic_trajectory_json": json.dumps(
                    [p.model_dump() for p in scenario.deterministic_trajectory]
                ),
                "percentiles_json": json.dumps([p.model_dump() for p in scenario.percentiles]),
                "data_class": scenario.data_class.value,
            },
            maximum_bytes_billed=None,
        )

    def get_debtlab_scenario(self, scenario_id: str) -> DebtLabScenarioResponse | None:
        control = self._config.debtlab_scenarios_fqtn
        rows = self._run_query(
            # FORMAT_TIMESTAMP with an explicit ISO 8601 pattern, not
            # CAST(... AS STRING): BigQuery's default STRING cast for
            # TIMESTAMP ("2026-09-08 13:34:21.515409+00") uses a space
            # separator and a 2-digit UTC offset, which doesn't match the
            # POST response's Python isoformat() ("...T...+00:00") --
            # cosmetic (same instant either way) but a literal string
            # comparison of the two responses would fail (found by an
            # independent /verify-spec review).
            "SELECT scenario_id, "
            "FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%E6S+00:00', created_at) AS created_at, "
            "horizon_years, "
            "CAST(base_reference_date AS STRING) AS base_reference_date, base_divida_pib_pct, "
            "base_source, assumptions_json, engine_version, seed, n_iterations, "
            "deterministic_trajectory_json, percentiles_json, data_class "
            f"FROM {control} WHERE scenario_id = @scenario_id",
            {"scenario_id": scenario_id},
        )
        if not rows:
            return None
        row = rows[0]
        return DebtLabScenarioResponse(
            scenario_id=row["scenario_id"],
            created_at=row["created_at"],
            horizon_years=int(row["horizon_years"]),
            base=DebtLabScenarioBase(
                reference_date=row["base_reference_date"],
                divida_pib_pct=float(row["base_divida_pib_pct"]),
                source=row["base_source"],
            ),
            assumptions=DebtLabScenarioRequest(**json.loads(row["assumptions_json"])),
            engine_version=row["engine_version"],
            seed=int(row["seed"]),
            n_iterations=int(row["n_iterations"]),
            deterministic_trajectory=[
                YearlyDeterministic(**p) for p in json.loads(row["deterministic_trajectory_json"])
            ],
            percentiles=[YearlyPercentiles(**p) for p in json.loads(row["percentiles_json"])],
            data_class=DataClass(row["data_class"]),
        )

    def _national_provenance_summary(
        self, metric_id: str, reference_date: str
    ) -> ProvenanceSummary | None:
        prov = self._config.provenance_fqtn
        rows = self._run_query(
            f"SELECT ANY_VALUE(source) AS source FROM {prov} "
            "WHERE metric_id = @metric_id AND reference_date = DATE(@ref_date)",
            {"metric_id": metric_id, "ref_date": reference_date},
        )
        if not rows or not rows[0]["source"]:
            return None
        return ProvenanceSummary(
            source=rows[0]["source"],
            reference_date=reference_date,
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


# 1 GiB -- same value and rationale as ingestion/src/ingestion/bigquery_io.py
# (ADR-057): generous for every table this project serves today, but catches
# a gross mistake before it becomes real cost. Duplicated, not imported: api/
# and ingestion/ are independently deployed packages with no shared library
# today, and introducing one for a single constant would be over-engineering
# for this feature's scope (DESIGN D2).
DEFAULT_MAX_BYTES_BILLED = 1_073_741_824


def _bq_param_type(value: Any) -> str:
    # bool is an int subclass in Python -- checked first so a bool value
    # never gets misclassified as INT64.
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    return "STRING"


def build_bigquery_run_query(project: str) -> RunQuery:
    from google.cloud import bigquery

    client = bigquery.Client(project=project)

    def run_query(
        sql: str,
        params: Mapping[str, Any],
        *,
        maximum_bytes_billed: int | None = DEFAULT_MAX_BYTES_BILLED,
    ) -> list[dict[str, Any]]:
        job_params = [
            bigquery.ScalarQueryParameter(name, _bq_param_type(value), value)
            for name, value in params.items()
        ]
        # maximum_bytes_billed=None must be omitted from QueryJobConfig, not
        # passed through literally -- the BigQuery client serializes an
        # explicit None as the string "None", which the REST API rejects for
        # an INT64 field (confirmed live in production: BadRequest on the
        # first real debtlab_scenarios INSERT). Same fix already applied on
        # the ingestion side (bigquery_io.py::run_sql) -- this call site just
        # hadn't needed maximum_bytes_billed=None before this feature.
        job_config_kwargs: dict[str, Any] = {"query_parameters": job_params}
        if maximum_bytes_billed is not None:
            job_config_kwargs["maximum_bytes_billed"] = maximum_bytes_billed
        job_config = bigquery.QueryJobConfig(**job_config_kwargs)
        return [dict(row) for row in client.query(sql, job_config=job_config).result()]

    return run_query
