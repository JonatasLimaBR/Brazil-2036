from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol


class QueryJob(Protocol):
    def result(self) -> Iterable[Mapping[str, Any]]: ...


class BigQueryClient(Protocol):
    def query(self, query: str) -> QueryJob: ...


def run_sql(client: BigQueryClient, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in client.query(sql).result()]


def scalar(client: BigQueryClient, sql: str) -> Any:
    rows = run_sql(client, sql)
    if not rows:
        return None
    return next(iter(rows[0].values()))


def sql_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{escaped}'"
