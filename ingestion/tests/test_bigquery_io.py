from __future__ import annotations

from typing import Any

import pytest
from _fakes import FakeBigQuery
from google.api_core.exceptions import BadRequest

from ingestion.bigquery_io import DEFAULT_MAX_BYTES_BILLED, run_sql, scalar


class _RejectingFakeBigQuery:
    """Simulates BigQuery's real bytes-billed enforcement (found by an
    independent /verify-spec review: no existing test actually exercised the
    failure path AT4/S3 require -- every other test only checks the cap
    *value* reaches job_config, never that exceeding it is enforced).

    Real BigQuery estimates a query's bytes before running it and raises
    BadRequest before incurring cost when the estimate exceeds
    maximum_bytes_billed. This fake models exactly that contract for a query
    whose estimated size is known ahead of time.
    """

    def __init__(self, estimated_bytes: int) -> None:
        self._estimated_bytes = estimated_bytes

    def query(self, query: str, job_config: Any = None) -> Any:
        cap = getattr(job_config, "maximum_bytes_billed", None)
        if cap is not None and self._estimated_bytes > cap:
            raise BadRequest(
                f"Query exceeded limit for bytes billed: {cap}. "
                f"{self._estimated_bytes} or higher required."
            )
        raise AssertionError("test should never reach a successful query")


def test_run_sql_applies_default_cap_by_default() -> None:
    client = FakeBigQuery()
    run_sql(client, "SELECT 1")
    assert len(client.job_configs) == 1
    job_config = client.job_configs[0]
    assert job_config is not None
    assert job_config.maximum_bytes_billed == DEFAULT_MAX_BYTES_BILLED


def test_run_sql_maximum_bytes_billed_none_disables_cap() -> None:
    client = FakeBigQuery()
    run_sql(client, "LOAD DATA OVERWRITE t FROM FILES (...)", maximum_bytes_billed=None)
    assert client.job_configs == [None]


def test_run_sql_accepts_custom_cap() -> None:
    client = FakeBigQuery()
    run_sql(client, "SELECT 1", maximum_bytes_billed=42)
    assert client.job_configs[0].maximum_bytes_billed == 42


def test_scalar_applies_default_cap_by_default() -> None:
    client = FakeBigQuery(lambda _sql: [{"n": 1}])
    scalar(client, "SELECT COUNT(*) AS n FROM t")
    assert client.job_configs[0].maximum_bytes_billed == DEFAULT_MAX_BYTES_BILLED


def test_scalar_maximum_bytes_billed_none_disables_cap() -> None:
    client = FakeBigQuery(lambda _sql: [{"n": 1}])
    scalar(client, "SELECT COUNT(*) AS n FROM t", maximum_bytes_billed=None)
    assert client.job_configs == [None]


def test_run_sql_propagates_bigquery_rejection_above_the_cap() -> None:
    # AT4/S3 (DEFINE): a query BigQuery estimates above the cap must fail
    # clearly, not hang or return a silent partial result. A tiny artificial
    # cap against a fake that models BigQuery's real pre-execution estimate
    # check proves run_sql neither swallows nor masks that failure.
    client = _RejectingFakeBigQuery(estimated_bytes=10_000_000)
    with pytest.raises(BadRequest, match="exceeded limit for bytes billed"):
        run_sql(client, "SELECT * FROM huge_table", maximum_bytes_billed=1)


def test_scalar_propagates_bigquery_rejection_above_the_cap() -> None:
    client = _RejectingFakeBigQuery(estimated_bytes=10_000_000)
    with pytest.raises(BadRequest, match="exceeded limit for bytes billed"):
        scalar(client, "SELECT COUNT(*) FROM huge_table", maximum_bytes_billed=1)
