from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

Rows = list[dict[str, Any]]


class _FakeQueryJob:
    def __init__(self, rows: Rows) -> None:
        self._rows = rows

    def result(self) -> Rows:
        return self._rows


class FakeBigQuery:
    def __init__(self, responder: Callable[[str], Rows] | None = None) -> None:
        self.queries: list[str] = []
        self.inserted: list[tuple[str, Rows]] = []
        self._responder = responder or (lambda _sql: [])

    def query(self, query: str) -> _FakeQueryJob:
        self.queries.append(query)
        return _FakeQueryJob(self._responder(query))

    def insert_rows_json(self, table: str, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        self.inserted.append((table, list(rows)))
        return []

    def load_table_from_uri(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("load_table_from_uri should not be used")


UF_CODES = [
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "31",
    "32",
    "33",
    "35",
    "41",
    "42",
    "43",
    "50",
    "51",
    "52",
    "53",
]
