from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from google.cloud import bigquery

# 1 GiB — generous for every table this project has today (the largest,
# INSS Indeferidos, is ~15k rows), but catches a gross mistake (e.g. a JOIN
# missing a partition filter) before it becomes real cost. See ADR-057.
# Does not apply to LOAD DATA (bronze.py opts out explicitly): batch loading
# is billed as a load, not as bytes processed, so this cap is a mismatched
# control there and could reject a legitimately large source file.
DEFAULT_MAX_BYTES_BILLED = 1_073_741_824


class QueryJob(Protocol):
    def result(self) -> Iterable[Mapping[str, Any]]: ...


class BigQueryClient(Protocol):
    def query(self, query: str, job_config: bigquery.QueryJobConfig | None = None) -> QueryJob: ...


def run_sql(
    client: BigQueryClient,
    sql: str,
    *,
    maximum_bytes_billed: int | None = DEFAULT_MAX_BYTES_BILLED,
) -> list[dict[str, Any]]:
    job_config = None
    if maximum_bytes_billed is not None:
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=maximum_bytes_billed)
    return [dict(row) for row in client.query(sql, job_config).result()]


def scalar(
    client: BigQueryClient,
    sql: str,
    *,
    maximum_bytes_billed: int | None = DEFAULT_MAX_BYTES_BILLED,
) -> Any:
    rows = run_sql(client, sql, maximum_bytes_billed=maximum_bytes_billed)
    if not rows:
        return None
    return next(iter(rows[0].values()))


def sql_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{escaped}'"
