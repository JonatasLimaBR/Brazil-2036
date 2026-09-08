from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from api.simulators.debtlab import Assumptions, project_deterministic

# SPEC-016: "Never present a percentile scenario as observed fact." These
# percentiles are always returned alongside data_class=simulated -- enforced
# by the caller (main.py), not here.
_PERCENTILES = (10, 25, 50, 75, 90)


@dataclass(frozen=True)
class AssumptionDistribution:
    mean: float
    std: float


@dataclass(frozen=True)
class YearPercentiles:
    year_offset: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


def run_monte_carlo(
    *,
    base_ratio_pct: float,
    horizon_years: int,
    juros: AssumptionDistribution,
    crescimento: AssumptionDistribution,
    primario: AssumptionDistribution,
    n_iterations: int,
    seed: int,
) -> list[YearPercentiles]:
    """SPEC-016: explicit distributions (normal, mean +/- std per premise),
    seed fixable for reproducibility. Independent sampling per premise --
    this is Monte Carlo inside one simulator (DebtLab), not the correlated
    multi-simulator SIM-019 (out of scope, DEFINE §6)."""
    rng = np.random.default_rng(seed)
    juros_samples = rng.normal(juros.mean, juros.std, n_iterations)
    crescimento_samples = rng.normal(crescimento.mean, crescimento.std, n_iterations)
    primario_samples = rng.normal(primario.mean, primario.std, n_iterations)

    trajectories = np.empty((n_iterations, horizon_years + 1))
    for i in range(n_iterations):
        points = project_deterministic(
            base_ratio_pct,
            horizon_years,
            Assumptions(
                juros_nominal=float(juros_samples[i]),
                crescimento_nominal_pib=float(crescimento_samples[i]),
                primario_pct_pib=float(primario_samples[i]),
            ),
        )
        trajectories[i] = [p.divida_pib_pct for p in points]

    computed = np.percentile(trajectories, _PERCENTILES, axis=0)
    return [
        YearPercentiles(
            year_offset=year,
            p10=float(computed[0][year]),
            p25=float(computed[1][year]),
            p50=float(computed[2][year]),
            p75=float(computed[3][year]),
            p90=float(computed[4][year]),
        )
        for year in range(horizon_years + 1)
    ]
