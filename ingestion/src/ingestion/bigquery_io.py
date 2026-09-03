from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol


class QueryJob(Protocol):
    def result(self) -> Iterable[Mapping[str, Any]]: ...


class LoadJob(Protocol):
    def result(self) -> Any: ...

    @property
    def output_rows(self) -> int: ...


class BigQueryClient(Protocol):
    def query(self, query: str) -> QueryJob: ...

    def load_table_from_uri(
        self, source_uris: str, destination: str, job_config: Any
    ) -> LoadJob: ...

    def insert_rows_json(
        self, table: str, rows: Sequence[Mapping[str, Any]]
    ) -> Sequence[Mapping[str, Any]]: ...


def run_sql(client: BigQueryClient, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in client.query(sql).result()]


def scalar(client: BigQueryClient, sql: str) -> Any:
    rows = run_sql(client, sql)
    if not rows:
        return None
    return next(iter(rows[0].values()))


def insert_rows(
    client: BigQueryClient, table: str, rows: Sequence[Mapping[str, Any]]
) -> None:
    errors = client.insert_rows_json(table, rows)
    if errors:
        raise BigQueryWriteError(f"insert into {table} failed: {errors}")


class BigQueryWriteError(RuntimeError):
    pass
