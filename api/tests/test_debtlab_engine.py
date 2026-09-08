from __future__ import annotations

import pytest

from api.simulators.debtlab import Assumptions, project_deterministic


def test_year_zero_is_the_observed_base_unchanged() -> None:
    points = project_deterministic(
        82.51,
        5,
        Assumptions(juros_nominal=0.10, crescimento_nominal_pib=0.06, primario_pct_pib=0.01),
    )
    assert points[0].year_offset == 0
    assert points[0].divida_pib_pct == 82.51


def test_flat_case_juros_equals_crescimento_zero_primario_holds_ratio_constant() -> None:
    # ratio_t = ratio_(t-1) * (1+r)/(1+r) - 0 = ratio_(t-1) -- the formula's
    # simplest sanity case, calculated by hand (DESIGN §6).
    points = project_deterministic(
        50.0, 3, Assumptions(juros_nominal=0.08, crescimento_nominal_pib=0.08, primario_pct_pib=0.0)
    )
    assert [p.divida_pib_pct for p in points] == pytest.approx([50.0, 50.0, 50.0, 50.0])


def test_hand_calculated_two_year_trajectory() -> None:
    # ratio_0 = 80. juros=0.10, crescimento=0.05, primario=0.02 (2% do PIB).
    # ratio_1 = 0.80 * 1.10/1.05 - 0.02 = 0.838095... - 0.02 = 0.818095...
    # ratio_2 = 0.818095... * 1.10/1.05 - 0.02
    points = project_deterministic(
        80.0,
        2,
        Assumptions(juros_nominal=0.10, crescimento_nominal_pib=0.05, primario_pct_pib=0.02),
    )
    ratio_1 = 0.80 * 1.10 / 1.05 - 0.02
    ratio_2 = ratio_1 * 1.10 / 1.05 - 0.02
    assert points[1].divida_pib_pct == pytest.approx(ratio_1 * 100)
    assert points[2].divida_pib_pct == pytest.approx(ratio_2 * 100)


def test_horizon_zero_returns_only_the_base_point() -> None:
    points = project_deterministic(
        60.0, 0, Assumptions(juros_nominal=0.1, crescimento_nominal_pib=0.05, primario_pct_pib=0.0)
    )
    assert len(points) == 1
    assert points[0].divida_pib_pct == 60.0


def test_reproducible_same_input_same_output() -> None:
    assumptions = Assumptions(
        juros_nominal=0.095, crescimento_nominal_pib=0.055, primario_pct_pib=0.015
    )
    first = project_deterministic(82.51, 10, assumptions)
    second = project_deterministic(82.51, 10, assumptions)
    assert first == second
