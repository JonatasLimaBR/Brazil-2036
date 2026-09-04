from __future__ import annotations

from pathlib import Path

from _fakes import FakeBigQuery

from ingestion.registry import (
    ensure_uf_ibge,
    load_uf_ibge_rows,
    upsert_dataset_registry,
)

UF_IBGE_CSV = Path(__file__).parents[1] / "reference" / "uf_ibge.csv"


def test_uf_ibge_csv_has_27_rows() -> None:
    rows = load_uf_ibge_rows(UF_IBGE_CSV)
    assert len(rows) == 27
    codes = {r["state_ibge_code"] for r in rows}
    assert "53" in codes  # Distrito Federal
    assert "35" in codes  # São Paulo
    assert all(len(c) == 2 for c in codes)


def test_ensure_uf_ibge_uses_create_or_replace_with_structs() -> None:
    client = FakeBigQuery()
    count = ensure_uf_ibge(
        client,
        project="p",
        dataset_control="br2036_control",
        table="uf_ibge",
        csv_path=UF_IBGE_CSV,
    )
    assert count == 27
    assert len(client.queries) == 1
    sql = client.queries[0]
    assert "CREATE OR REPLACE TABLE `p.br2036_control.uf_ibge`" in sql
    assert "FROM UNNEST([" in sql
    assert "STRUCT('RO' AS uf, '11' AS state_ibge_code" in sql
    assert "'RONDONIA' AS state_name_normalized" in sql
    assert "'SAO PAULO' AS state_name_normalized" in sql
    assert "INSERT" not in sql and "DELETE" not in sql


def test_upsert_dataset_registry_merges_scoped_by_dataset_id() -> None:
    # MERGE, not CREATE OR REPLACE: the table is shared across every dataset this
    # project ingests, so a full-table replace would erase every other dataset's row.
    client = FakeBigQuery()
    upsert_dataset_registry(
        client,
        project="p",
        dataset_control="br2036_control",
        table="dataset_registry",
        entry={
            "dataset_id": "divida_consolidada_estados",
            "resource_url": "https://x/y.csv",
            "resource_format": "csv",
            "organization": "COREM / STN",
            "license": "ODbL",
            "update_frequency": "annual",
            "br2036_domain": "fiscal",
            "br2036_module": "M02",
        },
    )
    assert len(client.queries) == 2
    create_sql, merge_sql = client.queries
    assert "CREATE TABLE IF NOT EXISTS `p.br2036_control.dataset_registry`" in create_sql
    assert "CREATE OR REPLACE" not in create_sql
    assert "MERGE `p.br2036_control.dataset_registry` T USING" in merge_sql
    assert "'divida_consolidada_estados' AS dataset_id" in merge_sql
    assert "'ODbL' AS license" in merge_sql
    assert "ON T.dataset_id = S.dataset_id" in merge_sql
    assert "WHEN MATCHED THEN UPDATE SET" in merge_sql
    assert "WHEN NOT MATCHED THEN INSERT" in merge_sql
    assert "CREATE OR REPLACE" not in merge_sql
