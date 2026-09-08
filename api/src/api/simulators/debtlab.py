from __future__ import annotations

from dataclasses import dataclass

# SPEC-010: "Core dynamics follow registered formula/version. No LLM
# arithmetic path may replace the engine." Bump this string whenever the
# formula itself changes -- it is persisted with every scenario (ADR-059).
ENGINE_VERSION = "debtlab-v1"


@dataclass(frozen=True)
class Assumptions:
    """One point-estimate scenario. juros_nominal, crescimento_nominal_pib
    and primario_pct_pib are all fractions (0.10 = 10%), not percentages."""

    juros_nominal: float
    crescimento_nominal_pib: float
    primario_pct_pib: float


@dataclass(frozen=True)
class YearPoint:
    year_offset: int
    divida_pib_pct: float


def project_deterministic(
    base_ratio_pct: float, horizon_years: int, assumptions: Assumptions
) -> list[YearPoint]:
    """Standard debt/GDP sustainability dynamics (DESIGN D2):

        ratio_t = ratio_(t-1) * (1 + juros) / (1 + crescimento) - primario_%pib_t

    base_ratio_pct and the returned divida_pib_pct are percentages (82.51,
    not 0.8251) -- matches the unit the real BCB SGS series (13762) already
    publishes, so the base year's point is the observed value unchanged.
    """
    ratio = base_ratio_pct / 100
    points = [YearPoint(year_offset=0, divida_pib_pct=base_ratio_pct)]
    for year in range(1, horizon_years + 1):
        ratio = (
            ratio * (1 + assumptions.juros_nominal) / (1 + assumptions.crescimento_nominal_pib)
            - assumptions.primario_pct_pib
        )
        points.append(YearPoint(year_offset=year, divida_pib_pct=ratio * 100))
    return points
