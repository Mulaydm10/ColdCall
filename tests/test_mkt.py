"""Tests for the deterministic stability math.

The MKT tests deliberately do not hard-code a number copied from a textbook. A fixture
copied from a PDF proves only that the copying was done correctly; if the constant is
mistyped, the test enshrines the typo. Instead each property that *defines* MKT is asserted
directly, and the optimised implementation is cross-checked against a naive one written
independently in the test file. Between them, an implementation that is wrong has nowhere
to hide: it must satisfy the Arrhenius identity, the ordering relation, the weighting
behaviour, and agree digit-for-digit with a different algorithm.
"""

from __future__ import annotations

import math

import pytest

from coldcall.mkt import (
    DEFAULT_ACTIVATION_ENERGY_J_PER_MOL,
    GAS_CONSTANT_J_PER_MOL_K,
    Reading,
    excursion_summary,
    mean_kinetic_temperature,
    stability_budget,
)


def naive_mkt(celsius: list[float], weights: list[float] | None = None) -> float:
    """A second, independent implementation: direct summation, no log-sum-exp.

    Deliberately the obvious translation of the formula. It is less numerically careful
    than the shipped version, which is the point — if the two agree to 12 decimal places
    the clever version has not broken the arithmetic while optimising it.
    """
    w = weights if weights is not None else [1.0] * len(celsius)
    dh_over_r = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL / GAS_CONSTANT_J_PER_MOL_K
    numerator = sum(
        wi * math.exp(-dh_over_r / (c + 273.15)) for c, wi in zip(celsius, w, strict=True)
    )
    return dh_over_r / -math.log(numerator / sum(w)) - 273.15


@pytest.mark.smoke
def test_smoke_module_imports_and_computes() -> None:
    """The green baseline ADR-0002 requires: the toolchain runs and the package works."""
    assert mean_kinetic_temperature([5.0]) == pytest.approx(5.0)


class TestMeanKineticTemperature:
    @pytest.mark.usp
    def test_activation_energy_default_puts_dh_over_r_at_about_10000(self) -> None:
        """The whole reason 83144 J/mol is the conventional value.

        The ratio is 9 999.91 K with the CODATA gas constant, and exactly 10 000 K if R is
        rounded to 8.3144 — which is why published worked examples come out in round
        numbers. The tolerance here is deliberately loose enough to permit either reading of
        R and tight enough to catch a genuinely wrong constant.
        """
        ratio = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL / GAS_CONSTANT_J_PER_MOL_K
        assert ratio == pytest.approx(10000.0, rel=1e-4)

    def test_constant_series_returns_that_temperature_exactly(self) -> None:
        for temp in (-20.0, 2.0, 5.0, 8.0, 25.0, 40.0):
            assert mean_kinetic_temperature([temp] * 24) == pytest.approx(temp, abs=1e-9)

    @pytest.mark.usp
    def test_mkt_exceeds_arithmetic_mean_whenever_temperature_varies(self) -> None:
        """Jensen's inequality, and the entire justification for using MKT at all.

        A shipment that swung is more degraded than one held at the same average, so any
        implementation returning the plain mean for a varying series is wrong.
        """
        varying = [2.0, 8.0, 2.0, 8.0, 2.0, 8.0]
        assert mean_kinetic_temperature(varying) > sum(varying) / len(varying)

    def test_agrees_with_an_independent_naive_implementation(self) -> None:
        series = [21.0, 24.5, 30.0, 18.2, 27.7, 22.1]
        assert mean_kinetic_temperature(series) == pytest.approx(naive_mkt(series), rel=1e-12)

    def test_agrees_with_naive_implementation_when_weighted(self) -> None:
        celsius = [4.0, 12.0, 6.5, 30.0]
        minutes = [600.0, 30.0, 240.0, 5.0]
        readings = [Reading(c, m) for c, m in zip(celsius, minutes, strict=True)]
        assert mean_kinetic_temperature(readings) == pytest.approx(
            naive_mkt(celsius, minutes), rel=1e-12
        )

    def test_duration_actually_weights_the_result(self) -> None:
        """A five-minute spike must not count as much as a ten-hour hold."""
        brief_spike = [Reading(5.0, 600.0), Reading(30.0, 5.0)]
        long_spike = [Reading(5.0, 600.0), Reading(30.0, 600.0)]
        assert mean_kinetic_temperature(brief_spike) < mean_kinetic_temperature(long_spike)

    def test_stays_precise_for_deep_frozen_series(self) -> None:
        """The log-sum-exp path exists for this case; naive summation degrades here."""
        deep = [-70.0, -68.5, -71.2, -69.9]
        assert mean_kinetic_temperature(deep) == pytest.approx(naive_mkt(deep), rel=1e-10)
        assert mean_kinetic_temperature(deep) > sum(deep) / len(deep)

    def test_single_reading_is_that_reading(self) -> None:
        assert mean_kinetic_temperature([7.3]) == pytest.approx(7.3, abs=1e-9)

    def test_scaling_all_durations_changes_nothing(self) -> None:
        """Only the ratio of durations can matter, never the unit they are expressed in."""
        in_minutes = [Reading(4.0, 60.0), Reading(11.0, 30.0)]
        in_hours = [Reading(4.0, 1.0), Reading(11.0, 0.5)]
        assert mean_kinetic_temperature(in_minutes) == pytest.approx(
            mean_kinetic_temperature(in_hours), rel=1e-12
        )


class TestInputValidation:
    def test_empty_series_is_an_error_not_a_zero(self) -> None:
        with pytest.raises(ValueError, match="empty temperature series"):
            mean_kinetic_temperature([])

    def test_reading_below_absolute_zero_is_rejected_as_a_sensor_fault(self) -> None:
        with pytest.raises(ValueError, match="absolute zero"):
            Reading(-300.0)

    def test_non_positive_duration_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive finite"):
            Reading(5.0, 0.0)

    def test_nan_temperature_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Reading(float("nan"))

    def test_non_positive_activation_energy_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="activation energy"):
            mean_kinetic_temperature([5.0], activation_energy_j_per_mol=0.0)

    def test_booleans_are_not_silently_treated_as_temperatures(self) -> None:
        with pytest.raises(TypeError):
            mean_kinetic_temperature([True, False])


class TestExcursionSummary:
    def test_clean_shipment_reports_no_excursion(self) -> None:
        summary = excursion_summary([Reading(5.0, 60.0)] * 24, 2.0, 8.0)
        assert summary.in_range
        assert summary.minutes_out_of_range == 0
        assert summary.peak_above_c == 0
        assert summary.peak_below_c == 0

    def test_warm_and_cold_time_are_tracked_separately_never_netted(self) -> None:
        """A freeze must not be cancelled out by an overheat; both are real events."""
        summary = excursion_summary(
            [Reading(5.0, 100.0), Reading(12.0, 30.0), Reading(-2.0, 20.0)], 2.0, 8.0
        )
        assert summary.minutes_above == 30
        assert summary.minutes_below == 20
        assert summary.minutes_out_of_range == 50
        assert summary.peak_above_c == pytest.approx(4.0)
        assert summary.peak_below_c == pytest.approx(4.0)

    def test_boundary_readings_count_as_in_range(self) -> None:
        """Exactly 2 °C and exactly 8 °C are inside a 2-8 °C label, not outside it."""
        summary = excursion_summary([Reading(2.0, 10.0), Reading(8.0, 10.0)], 2.0, 8.0)
        assert summary.in_range

    def test_inverted_limits_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be below"):
            excursion_summary([Reading(5.0)], 8.0, 2.0)


class TestStabilityBudget:
    def test_clean_shipment_releases(self) -> None:
        budget = stability_budget([Reading(5.0, 60.0)] * 48, 2.0, 8.0)
        assert budget.verdict == "release"
        assert budget.excursion.in_range
        assert budget.budget_consumed_fraction == 0.0

    def test_any_freeze_quarantines_regardless_of_budget(self) -> None:
        """Rule 1: for a refrigerated biologic a freeze is not a budget item."""
        budget = stability_budget(
            [Reading(5.0, 600.0), Reading(-0.5, 5.0)],
            2.0,
            8.0,
            allowed_excursion_minutes=10_000.0,
        )
        assert budget.verdict == "quarantine"
        assert any("freeze event" in r for r in budget.reasons)

    def test_freeze_can_be_waived_for_products_where_it_is_not_disqualifying(self) -> None:
        budget = stability_budget(
            [Reading(5.0, 600.0), Reading(1.0, 5.0)],
            2.0,
            8.0,
            allowed_excursion_minutes=60.0,
            freeze_is_disqualifying=False,
        )
        assert budget.verdict == "review"

    def test_excursion_inside_allowance_asks_for_review_rather_than_releasing(self) -> None:
        """Rule 4: inside budget but not clean is a human's call, not the agent's."""
        budget = stability_budget(
            [Reading(5.0, 600.0), Reading(9.0, 20.0)], 2.0, 8.0, allowed_excursion_minutes=60.0
        )
        assert budget.verdict == "review"
        assert budget.excursion_minutes_remaining == pytest.approx(40.0)

    def test_excursion_beyond_allowance_quarantines(self) -> None:
        budget = stability_budget(
            [Reading(5.0, 600.0), Reading(9.0, 90.0)], 2.0, 8.0, allowed_excursion_minutes=60.0
        )
        assert budget.verdict == "quarantine"
        assert budget.excursion_minutes_remaining == 0.0
        assert budget.budget_consumed_fraction > 1.0

    def test_mkt_above_label_quarantines_even_with_budget_left(self) -> None:
        """Rule 2: above the labelled maximum there is no budget left to spend."""
        budget = stability_budget(
            [Reading(20.0, 600.0)], 2.0, 8.0, allowed_excursion_minutes=100_000.0
        )
        assert budget.verdict == "quarantine"
        assert any("MKT" in r for r in budget.reasons)

    def test_default_allowance_is_zero_so_nothing_is_assumed(self) -> None:
        """Assuming an allowance nobody granted is the dangerous direction to be wrong in."""
        budget = stability_budget([Reading(5.0, 600.0), Reading(8.5, 1.0)], 2.0, 8.0)
        assert budget.allowed_excursion_minutes == 0.0
        assert budget.verdict == "quarantine"

    def test_verdict_carries_the_inputs_needed_to_re_derive_it(self) -> None:
        """An auditor must be able to recompute the number without trusting the agent."""
        budget = stability_budget([Reading(5.0, 60.0)] * 10, 2.0, 8.0)
        assert budget.activation_energy_j_per_mol == DEFAULT_ACTIVATION_ENERGY_J_PER_MOL
        assert budget.label_lower_c == 2.0
        assert budget.label_upper_c == 8.0
        assert budget.excursion.minutes_total == pytest.approx(600.0)
        assert budget.reasons

    def test_negative_allowance_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            stability_budget([Reading(5.0)], 2.0, 8.0, allowed_excursion_minutes=-1.0)
