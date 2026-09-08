from __future__ import annotations

from api.simulators.monte_carlo import AssumptionDistribution, run_monte_carlo


def _distributions() -> dict[str, AssumptionDistribution]:
    return {
        "juros": AssumptionDistribution(mean=0.10, std=0.02),
        "crescimento": AssumptionDistribution(mean=0.06, std=0.015),
        "primario": AssumptionDistribution(mean=0.01, std=0.005),
    }


def test_same_seed_produces_identical_percentiles() -> None:
    kwargs = _distributions()
    first = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=5, n_iterations=500, seed=42, **kwargs
    )
    second = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=5, n_iterations=500, seed=42, **kwargs
    )
    assert first == second


def test_different_seeds_produce_different_percentiles() -> None:
    kwargs = _distributions()
    first = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=5, n_iterations=500, seed=1, **kwargs
    )
    second = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=5, n_iterations=500, seed=2, **kwargs
    )
    assert first != second


def test_percentiles_are_ordered_p10_through_p90() -> None:
    result = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=10, n_iterations=1000, seed=7, **_distributions()
    )
    for year in result:
        assert year.p10 <= year.p25 <= year.p50 <= year.p75 <= year.p90


def test_year_zero_percentiles_all_equal_the_observed_base() -> None:
    # No randomness has been applied yet at year 0 -- every iteration starts
    # from the same real base_ratio_pct (SPEC-016: never fabricate the
    # observed anchor as uncertain).
    result = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=3, n_iterations=200, seed=3, **_distributions()
    )
    year0 = result[0]
    assert year0.p10 == year0.p50 == year0.p90 == 82.51


def test_output_length_matches_horizon_plus_base_year() -> None:
    result = run_monte_carlo(
        base_ratio_pct=82.51, horizon_years=10, n_iterations=200, seed=9, **_distributions()
    )
    assert len(result) == 11
