"""The independent recomputation, and proof that it would catch a wrong primary.

A cross-check nobody has ever seen fail is indistinguishable from a cross-check that cannot
fail. So the tests here do not only confirm agreement on good input — they tamper with the
primary result and assert that the disagreement is caught, named, and blocks presentation.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from coldcall.crosscheck import (
    AGREEMENT_TOLERANCE_C,
    cross_check,
    recompute_mkt_directly,
)
from coldcall.disposition import (
    DESTROY,
    QUARANTINE_RETEST,
    RELEASE,
    DispositionPolicy,
    disposition,
)
from coldcall.mkt import DEFAULT_ACTIVATION_ENERGY_J_PER_MOL, Reading, mean_kinetic_temperature

CRT_LOWER, CRT_UPPER = 20.0, 25.0


def policy(hours: float = 6.0, **kwargs) -> DispositionPolicy:
    return DispositionPolicy(allowed_excursion_hours=hours, **kwargs)


class TestIndependentMKT:
    """The checker must reach the same answer by a genuinely different route."""

    @pytest.mark.usp
    def test_a_constant_series_is_exactly_that_temperature(self):
        """The one case with an analytic answer: MKT of a constant series is the constant."""
        assert recompute_mkt_directly(
            [Reading(22.0, 60.0)] * 5, DEFAULT_ACTIVATION_ENERGY_J_PER_MOL
        ) == pytest.approx(22.0, abs=1e-9)

    @pytest.mark.parametrize(
        "temps",
        [
            [22.0, 27.0, 23.0],
            [4.0, 5.0, 6.0, 30.0],
            [20.1, 24.9, 25.1, 19.9],
            [-10.0, 0.0, 10.0],
        ],
    )
    def test_it_matches_the_primary_implementation(self, temps):
        """Two numerical routes — log-sum-exp and direct summation — one definition."""
        series = [Reading(t, 30.0) for t in temps]
        primary = mean_kinetic_temperature(series)
        independent = recompute_mkt_directly(series, DEFAULT_ACTIVATION_ENERGY_J_PER_MOL)
        assert independent == pytest.approx(primary, abs=AGREEMENT_TOLERANCE_C)

    def test_it_respects_duration_weighting(self):
        """A reading held ten times as long must count ten times as much, both ways."""
        series = [Reading(20.0, 600.0), Reading(30.0, 60.0)]
        assert recompute_mkt_directly(
            series, DEFAULT_ACTIVATION_ENERGY_J_PER_MOL
        ) == pytest.approx(mean_kinetic_temperature(series), abs=AGREEMENT_TOLERANCE_C)

    def test_underflow_is_reported_not_papered_over(self):
        """Direct summation is the numerically weaker route, which is why it is the checker.

        At extreme cold the exponentials underflow to zero and the textbook form cannot
        produce an answer at all. Saying so is right; returning a number would be worse than
        having no cross-check.
        """
        with pytest.raises(ArithmeticError, match="underflow"):
            recompute_mkt_directly([Reading(-272.0, 60.0)], DEFAULT_ACTIVATION_ENERGY_J_PER_MOL)


class TestAgreementOnGoodInput:
    def test_a_clean_release_agrees(self):
        readings = [Reading(22.0, 60.0)] * 10
        result = disposition(readings, CRT_LOWER, CRT_UPPER, policy())
        check = cross_check(result, readings, policy())
        assert result.verdict == RELEASE
        assert check.agrees
        assert not check.blocks_presentation
        assert check.disagreements == ()

    def test_the_demo_shape_agrees(self):
        """The borderline case, which is the one a wrong number would actually flip."""
        readings = [Reading(22.0, 60.0)] * 20 + [Reading(27.0, 60.0)] * 3
        pol = policy(hours=6.0)
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        check = cross_check(result, readings, pol)
        assert result.verdict == QUARANTINE_RETEST
        assert check.agrees
        assert check.independent_verdict == QUARANTINE_RETEST

    def test_a_destroy_agrees(self):
        readings = [Reading(22.0, 60.0)] * 20 + [Reading(27.0, 60.0)] * 6
        pol = policy(hours=6.0)
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        check = cross_check(result, readings, pol)
        assert result.verdict == DESTROY
        assert check.agrees


class TestItActuallyCatchesAWrongPrimary:
    """The tests that make this worth having. A check that has never failed proves nothing."""

    def test_a_tampered_mkt_is_caught_and_named(self):
        readings = [Reading(22.0, 60.0)] * 10
        pol = policy()
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        tampered = dataclasses.replace(result, mkt_c=result.mkt_c + 0.5)

        check = cross_check(tampered, readings, pol)
        assert not check.agrees
        assert check.blocks_presentation
        assert any("MKT disagrees" in d for d in check.disagreements)

    def test_a_tampered_verdict_is_caught_and_says_do_not_present(self):
        """The loudest failure: the two implementations reach different dispositions."""
        readings = [Reading(22.0, 60.0)] * 20 + [Reading(27.0, 60.0)] * 3
        pol = policy(hours=6.0)
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        tampered = dataclasses.replace(result, verdict=RELEASE)

        check = cross_check(tampered, readings, pol)
        assert not check.agrees
        assert check.independent_verdict == QUARANTINE_RETEST
        assert any("VERDICT DISAGREES" in d for d in check.disagreements)
        assert any("Do not present" in d for d in check.disagreements)

    def test_tampered_excursion_minutes_are_caught(self):
        readings = [Reading(22.0, 60.0)] * 10 + [Reading(27.0, 60.0)]
        pol = policy(hours=6.0)
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        broken_excursion = dataclasses.replace(
            result.excursion, minutes_above=result.excursion.minutes_above + 30.0
        )
        tampered = dataclasses.replace(result, excursion=broken_excursion)

        check = cross_check(tampered, readings, pol)
        assert not check.agrees
        assert any("excursion minutes disagree" in d for d in check.disagreements)

    def test_a_difference_inside_tolerance_is_not_a_disagreement(self):
        """Float noise must not cry wolf, or nobody will believe a real disagreement."""
        readings = [Reading(22.0, 60.0)] * 10
        pol = policy()
        result = disposition(readings, CRT_LOWER, CRT_UPPER, pol)
        nudged = dataclasses.replace(result, mkt_c=result.mkt_c + AGREEMENT_TOLERANCE_C / 10)
        assert cross_check(nudged, readings, pol).agrees


class TestSerialisedOutput:
    def test_it_reports_its_own_method_and_limits(self):
        readings = [Reading(22.0, 60.0)] * 5
        pol = policy()
        document = cross_check(
            disposition(readings, CRT_LOWER, CRT_UPPER, pol), readings, pol
        ).to_dict()

        assert document["agrees"] is True
        assert "direct summation" in document["method"]
        # The honest caveat has to travel with the reassurance, or the reassurance is
        # overclaiming: two implementations can share a misreading of the standard.
        assert "not proof of correctness" in document["limits"]
        assert math.isclose(document["primary_mkt_c"], document["independent_mkt_c"], abs_tol=1e-6)


class TestFalseDisagreementsAreTheWorstFailure:
    """A verifier that fires on valid input trains the operator that the alarm cries wolf.

    Both cases here produced exit code 3 — "do not trust this bundle" — for shipments the
    primary logic handled correctly. That is worse than having no cross-check: a real
    disagreement afterwards would be read as another false alarm.
    """

    def test_a_zero_degree_envelope_bound_is_not_absent(self):
        """0.0 is falsy, so `envelope_lower_c or label_lower_c` silently discarded it.

        The checker then evaluated a different envelope than disposition() did. A frozen-goods
        label with a 0 °C floor is an entirely ordinary thing for this system to be handed.
        """
        readings = [Reading(3.0, 60.0)] * 8 + [Reading(-2.0, 60.0)]
        pol = policy(hours=6.0, freeze_is_disqualifying=False)
        result = disposition(
            readings, 2.0, 8.0, pol, excursion_lower_c=0.0, excursion_upper_c=10.0
        )
        assert result.envelope_lower_c == 0.0

        check = cross_check(result, readings, pol)
        assert check.agrees, f"false disagreement: {check.disagreements}"
        assert check.independent_verdict == result.verdict

    def test_a_zero_bound_still_catches_a_genuine_breach(self):
        """Fixing the false positive must not cost the true positive."""
        readings = [Reading(3.0, 60.0)] * 8 + [Reading(-5.0, 60.0)]
        pol = policy(hours=6.0, freeze_is_disqualifying=False)
        result = disposition(
            readings, 2.0, 8.0, pol, excursion_lower_c=0.0, excursion_upper_c=10.0
        )
        assert result.verdict == QUARANTINE_RETEST
        assert cross_check(result, readings, pol).agrees

    def test_a_one_shot_iterable_does_not_exhaust_between_the_two_paths(self):
        """`readings: object` is advertised the way disposition() advertises it.

        The primary path consumed the generator, then the verification received an empty
        series and raised — so handing over a perfectly legal input broke the verifier.
        """
        pol = policy(hours=6.0)
        materialised = [Reading(22.0, 60.0)] * 20 + [Reading(27.0, 60.0)] * 3
        result = disposition(iter(materialised), CRT_LOWER, CRT_UPPER, pol)
        check = cross_check(result, iter(materialised), pol)
        assert check.agrees
        assert check.independent_verdict == result.verdict
