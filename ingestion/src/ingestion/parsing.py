from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation

FISCAL_YEAR_END_MONTH = 12
FISCAL_YEAR_END_DAY = 31


class ParseError(ValueError):
    pass


def parse_brl_number(raw: str) -> Decimal:
    text = raw.strip()
    if not text:
        raise ParseError("empty numeric value")
    normalized = text.replace(".", "").replace(",", ".")
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ParseError(f"not a pt-BR number: {raw!r}") from exc
    return value


def parse_year(raw: str) -> int:
    text = raw.strip()
    if not text.isdigit() or len(text) != 4:
        raise ParseError(f"not a 4-digit year: {raw!r}")
    return int(text)


def reference_date_for_year(year: int) -> dt.date:
    return dt.date(year, FISCAL_YEAR_END_MONTH, FISCAL_YEAR_END_DAY)
