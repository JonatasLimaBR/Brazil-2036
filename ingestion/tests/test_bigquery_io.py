from __future__ import annotations

from _fakes import FakeBigQuery

from ingestion.bigquery_io import DEFAULT_MAX_BYTES_BILLED, run_sql, scalar


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
