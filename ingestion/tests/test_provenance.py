from __future__ import annotations

import datetime as dt
from decimal import Decimal

from _fakes import UF_CODES, FakeBigQuery

from ingestion.provenance import build_rows, write


def _gold_rows() -> list[dict[str, object]]:
    return [
        {
            "metric_id": "divida_consolidada",
            "state_ibge_code": code,
            "reference_year": 2022,
            "reference_date": dt.date(2022, 12, 31),
            "value": Decimal("1000.00"),
            "unit": "BRL",
        }
        for code in UF_CODES
    ]


def test_build_rows_shape() -> None:
    rows = build_rows(
        _gold_rows(),
        source_url="https://x/y.csv",
        gold_object="p.br2036_gold.gold_debt_state_current",
        silver_transform="sql/silver/debt_state.sql",
        silver_transform_version="run123",
        bronze_object="gs://p-raw/divida_estados/abc.csv",
        catalog_dataset_id="divida_consolidada_estados",
        producing_organization="COREM / STN",
        run_id="run123",
        created_at="2026-09-03T00:00:00+00:00",
    )
    assert len(rows) == 27
    first = rows[0]
    assert first["scenario"] == "observed"
    assert first["model"] == "none"
    assert first["confidence"] == 1.0
    assert first["source"] == "https://x/y.csv"
    assert isinstance(first["assumptions"], list) and first["assumptions"]
    assert first["reference_date"] == "2022-12-31"


def test_write_deletes_year_then_inserts() -> None:
    client = FakeBigQuery()
    rows = build_rows(
        _gold_rows(),
        source_url="u",
        gold_object="g",
        silver_transform="s",
        silver_transform_version="v",
        bronze_object="b",
        catalog_dataset_id="d",
        producing_organization="o",
        run_id="r",
        created_at="t",
    )
    n = write(
        client,
        project="p",
        dataset_gold="br2036_gold",
        table="metric_provenance",
        rows=rows,
        reference_year=2022,
    )
    assert n == 27
    assert any("DELETE FROM" in q and "reference_year = 2022" in q for q in client.queries)
    table, inserted = client.inserted[0]
    assert table == "p.br2036_gold.metric_provenance"
    assert len(inserted) == 27
