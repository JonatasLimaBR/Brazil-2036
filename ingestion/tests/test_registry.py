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


def test_ensure_uf_ibge_creates_truncates_inserts() -> None:
    client = FakeBigQuery()
    count = ensure_uf_ibge(
        client,
        project="p",
        dataset_control="br2036_control",
        table="uf_ibge",
        csv_path=UF_IBGE_CSV,
    )
    assert count == 27
    assert any("CREATE TABLE IF NOT EXISTS" in q for q in client.queries)
    assert any("TRUNCATE TABLE" in q for q in client.queries)
    table, rows = client.inserted[0]
    assert table == "p.br2036_control.uf_ibge"
    assert len(rows) == 27


def test_upsert_dataset_registry_deletes_then_inserts_one() -> None:
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
    assert any("DELETE FROM" in q and "divida_consolidada_estados" in q for q in client.queries)
    table, rows = client.inserted[0]
    assert table == "p.br2036_control.dataset_registry"
    assert rows[0]["active"] is True
    assert rows[0]["license"] == "ODbL"
