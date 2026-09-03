from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ContractResult:
    stage: str
    ok: bool
    violations: list[str] = field(default_factory=list)

    def raise_if_broken(self) -> None:
        if not self.ok:
            joined = "; ".join(self.violations)
            raise ContractViolation(f"{self.stage} contract broken: {joined}")


class ContractViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class DataContract:
    dataset: str
    version: int
    source_columns: tuple[str, ...]
    keys: tuple[str, ...]
    required_fields: Mapping[str, Mapping[str, Any]]
    expected_entity_count: int

    @classmethod
    def load(cls, path: str | Path) -> DataContract:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        count = _expected_entity_count(raw.get("quality_rules", []))
        return cls(
            dataset=raw["dataset"],
            version=int(raw["version"]),
            source_columns=tuple(raw["source_columns"]),
            keys=tuple(raw["keys"]),
            required_fields=raw["required_fields"],
            expected_entity_count=count,
        )

    def check_bronze_schema(self, columns: Sequence[str]) -> ContractResult:
        violations: list[str] = []
        actual = list(columns)
        missing = [c for c in self.source_columns if c not in actual]
        if missing:
            violations.append(f"missing source columns: {missing}")
        unexpected = [c for c in actual if c not in self.source_columns]
        if unexpected:
            violations.append(f"unexpected source columns: {unexpected}")
        return ContractResult("bronze", not violations, violations)

    def check_gold(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        latest_reference_year: int,
        provenance_row_count: int,
    ) -> ContractResult:
        violations: list[str] = []
        current = [r for r in rows if r.get("reference_year") == latest_reference_year]

        distinct_entities = {r.get("state_ibge_code") for r in current}
        if len(distinct_entities) != self.expected_entity_count:
            violations.append(
                f"expected {self.expected_entity_count} entities for {latest_reference_year}, "
                f"got {len(distinct_entities)}"
            )

        for key in ("state_ibge_code", "reference_year", "reference_date", "value"):
            if any(r.get(key) in (None, "") for r in current):
                violations.append(f"null values in required field {key!r}")

        if any(_as_decimal(r.get("value")) < 0 for r in current):
            violations.append("negative value found")

        if provenance_row_count != len(current):
            violations.append(
                f"provenance coverage mismatch: {provenance_row_count} provenance rows "
                f"for {len(current)} metric rows"
            )

        return ContractResult("gold", not violations, violations)


def _expected_entity_count(quality_rules: Sequence[Mapping[str, Any]]) -> int:
    for rule in quality_rules:
        expr = str(rule.get("expr", ""))
        if "count(distinct state_ibge_code)" in expr and "=" in expr:
            return int(expr.rsplit("=", 1)[1].strip())
    return 27


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
