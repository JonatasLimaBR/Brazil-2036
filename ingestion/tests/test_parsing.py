from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from ingestion.parsing import (
    ParseError,
    parse_brl_number,
    parse_year,
    reference_date_for_year,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.245.948.557,36", Decimal("4245948557.36")),
        ("11.252.027.857,87", Decimal("11252027857.87")),
        ("0,00", Decimal("0.00")),
        ("1.000,50", Decimal("1000.50")),
        (" 3.670.558.893,30 ", Decimal("3670558893.30")),
    ],
)
def test_parse_brl_number(raw: str, expected: Decimal) -> None:
    assert parse_brl_number(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1,2,3", "R$ 10"])
def test_parse_brl_number_rejects_garbage(raw: str) -> None:
    with pytest.raises(ParseError):
        parse_brl_number(raw)


def test_parse_year() -> None:
    assert parse_year("2022") == 2022


@pytest.mark.parametrize("raw", ["22", "20222", "abcd", ""])
def test_parse_year_rejects_bad(raw: str) -> None:
    with pytest.raises(ParseError):
        parse_year(raw)


def test_reference_date_for_year() -> None:
    assert reference_date_for_year(2022) == dt.date(2022, 12, 31)
