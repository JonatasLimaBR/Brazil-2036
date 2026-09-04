from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

from ingestion.contract import ContractViolation, DataContract

CONTRACT_PATH = Path(__file__).parents[1] / "contracts" / "divida_consolidada_estados.yaml"

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


def _contract() -> DataContract:
    return DataContract.load(CONTRACT_PATH)


def _gold_rows(year: int, codes: list[str]) -> list[dict[str, object]]:
    return [
        {
            "state_ibge_code": code,
            "reference_year": year,
            "reference_date": dt.date(year, 12, 31),
            "value": Decimal("1000.00"),
            "unit": "BRL",
        }
        for code in codes
    ]


def test_contract_loads() -> None:
    contract = _contract()
    assert contract.dataset == "divida_consolidada_estados"
    assert contract.version == 1
    assert contract.source_columns == ("UF", "ANO", "VALOR")
    assert contract.expected_entity_count == 27


def test_bronze_schema_ok() -> None:
    assert _contract().check_bronze_schema(["UF", "ANO", "VALOR"]).ok


def test_bronze_schema_missing_column() -> None:
    result = _contract().check_bronze_schema(["UF", "ANO"])
    assert not result.ok
    assert any("missing" in v for v in result.violations)


def test_bronze_schema_unexpected_column() -> None:
    result = _contract().check_bronze_schema(["UF", "ANO", "VALOR", "EXTRA"])
    assert not result.ok


def test_gold_ok_with_full_coverage() -> None:
    rows = _gold_rows(2022, UF_CODES)
    result = _contract().check_gold(
        rows, latest_reference_year=2022, provenance_row_count=len(rows)
    )
    assert result.ok, result.violations


def test_gold_detects_incomplete_entities() -> None:
    rows = _gold_rows(2022, UF_CODES[:-1])
    result = _contract().check_gold(
        rows, latest_reference_year=2022, provenance_row_count=len(rows)
    )
    assert not result.ok
    assert any("expected 27 entities" in v for v in result.violations)


def test_gold_detects_negative_value() -> None:
    rows = _gold_rows(2022, UF_CODES)
    rows[0]["value"] = Decimal("-1")
    result = _contract().check_gold(
        rows, latest_reference_year=2022, provenance_row_count=len(rows)
    )
    assert not result.ok
    assert any("negative" in v for v in result.violations)


def test_gold_detects_provenance_gap() -> None:
    rows = _gold_rows(2022, UF_CODES)
    result = _contract().check_gold(
        rows, latest_reference_year=2022, provenance_row_count=len(rows) - 3
    )
    assert not result.ok
    assert any("provenance coverage" in v for v in result.violations)


def test_gold_raise_if_broken() -> None:
    rows = _gold_rows(2022, UF_CODES[:5])
    result = _contract().check_gold(rows, latest_reference_year=2022, provenance_row_count=5)
    try:
        result.raise_if_broken()
    except ContractViolation as exc:
        assert "gold contract broken" in str(exc)
    else:
        raise AssertionError("expected ContractViolation")
