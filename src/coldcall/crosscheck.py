"""An independent recomputation that must agree before a verdict is shown to anyone.

The claim this defends
----------------------
ColdCall's whole argument is that the disposition is *arithmetic a regulator could re-derive*,
not a model's opinion. That claim has a weak point nobody usually tests: the arithmetic is
implemented once. A bug in `mkt.py` produces a wrong number that is perfectly reproducible,
perfectly auditable, and wrong — and reproducibility would make it *more* convincing, not less.

So this module recomputes the same quantities by **deliberately different means** and refuses
to agree with itself cheaply:

* MKT is recomputed with **direct summation** of the Arrhenius terms, in the textbook form,
  rather than `mkt.py`'s log-sum-exp. Different numerical path, same definition.
* Excursion minutes are recounted by **accumulating a running clock** rather than by filtering
  and summing durations.
* The verdict is re-derived from those independent inputs by re-reading the policy thresholds.

Two implementations agreeing is not proof — they could share a misreading of the standard. It
*is* enough to catch the failure this is actually aimed at: a coding error in one path. And a
disagreement is never resolved silently; it is surfaced as a reason not to trust the bundle.

Why the primary implementation is still the primary one
-------------------------------------------------------
The direct-summation form here is the *less* numerically sound of the two: the exponentials
involved are around 1e-16 and naive summation of many such terms loses precision exactly where
a borderline shipment is decided. That is why `mkt.py` uses log-sum-exp and why this is the
checker rather than the source of truth. The tolerance below is chosen to be far tighter than
any difference that could change a verdict, and far looser than float noise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from coldcall.disposition import (
    DESTROY,
    QUARANTINE_RETEST,
    RELEASE,
    Disposition,
    DispositionPolicy,
)
from coldcall.mkt import GAS_CONSTANT_J_PER_MOL_K, Reading, _as_readings

__all__ = ["AGREEMENT_TOLERANCE_C", "CrossCheck", "cross_check", "recompute_mkt_directly"]

#: How far the two MKT implementations may differ before the result is untrustworthy, in °C.
#: Far tighter than any difference that could move a verdict — the thresholds are whole
#: degrees and whole percentage points — and far looser than accumulated float noise over a
#: few thousand readings.
AGREEMENT_TOLERANCE_C = 1e-6

#: Same, for minutes out of range. These are sums of the same durations by different routes,
#: so anything beyond rounding is a real disagreement.
AGREEMENT_TOLERANCE_MIN = 1e-6


def recompute_mkt_directly(
    readings: object, activation_energy_j_per_mol: float
) -> float:
    """Mean kinetic temperature by direct summation — the textbook form, not log-sum-exp.

    MKT = (ΔH/R) / −ln( Σ wᵢ·e^(−ΔH/(R·Tᵢ)) / Σ wᵢ )

    Written to share as little as possible with ``mkt.mean_kinetic_temperature``: no shifting,
    no ``math.fsum``, plain accumulation. If the two agree, they agree despite taking
    different numerical routes; if they disagree, one of them has a bug.
    """
    series = _as_readings(readings)
    dh_over_r = activation_energy_j_per_mol / GAS_CONSTANT_J_PER_MOL_K

    weighted_sum = 0.0
    total_weight = 0.0
    for reading in series:
        weighted_sum += reading.minutes * math.exp(-dh_over_r / (reading.celsius + 273.15))
        total_weight += reading.minutes

    if weighted_sum <= 0.0:
        # Underflow: every exponential rounded to zero. The log-sum-exp path exists precisely
        # to survive this, so reaching it here is a real finding rather than an edge case to
        # paper over — say so instead of returning a number.
        raise ArithmeticError(
            "direct summation underflowed to zero; the primary implementation's log-sum-exp "
            "form is required for this series and the cross-check cannot confirm it"
        )
    return dh_over_r / -math.log(weighted_sum / total_weight) - 273.15


def _recount_excursion_minutes(
    readings: list[Reading], lower_c: float, upper_c: float
) -> tuple[float, float]:
    """Recount time out of range with a running clock. Returns (out_of_range, total)."""
    out_of_range = 0.0
    total = 0.0
    for reading in readings:
        total += reading.minutes
        if reading.celsius > upper_c or reading.celsius < lower_c:
            out_of_range += reading.minutes
    return out_of_range, total


@dataclass(frozen=True, slots=True)
class CrossCheck:
    """Whether an independent recomputation reached the same conclusion."""

    agrees: bool
    primary_verdict: str
    independent_verdict: str
    primary_mkt_c: float
    independent_mkt_c: float | None
    mkt_difference_c: float | None
    primary_minutes_out: float
    independent_minutes_out: float
    disagreements: tuple[str, ...]

    @property
    def blocks_presentation(self) -> bool:
        """Whether this result must stop the evidence bundle reaching a human.

        A disagreement means one of two implementations of a regulated calculation is wrong
        and we do not know which. Presenting a verdict in that state — even labelled — invites
        someone to act on it, so the answer is to stop, not to annotate.
        """
        return not self.agrees

    def to_dict(self) -> dict[str, object]:
        return {
            "agrees": self.agrees,
            "primary_verdict": self.primary_verdict,
            "independent_verdict": self.independent_verdict,
            "primary_mkt_c": round(self.primary_mkt_c, 6),
            "independent_mkt_c": (
                None if self.independent_mkt_c is None else round(self.independent_mkt_c, 6)
            ),
            "mkt_difference_c": (
                None if self.mkt_difference_c is None else f"{self.mkt_difference_c:.3e}"
            ),
            "primary_minutes_out_of_range": self.primary_minutes_out,
            "independent_minutes_out_of_range": self.independent_minutes_out,
            "disagreements": list(self.disagreements),
            "method": (
                "MKT recomputed by direct summation rather than log-sum-exp; excursion "
                "minutes recounted with a running clock rather than a filtered sum; verdict "
                "re-derived from those independent inputs."
            ),
            "limits": (
                "Two implementations agreeing is not proof of correctness — they could share "
                "a misreading of the standard. It catches a coding error in one path, which "
                "is what it is for."
            ),
        }


def cross_check(
    result: Disposition,
    readings: object,
    policy: DispositionPolicy,
) -> CrossCheck:
    """Recompute ``result`` independently and report whether the two agree.

    Never raises on a disagreement — it reports one. The caller decides what to do, and the
    SOP says what that is: stop, and say which two numbers disagree.
    """
    # Materialise once, up front. Both public helpers advertise `readings: object` the way
    # `disposition()` does, so a caller may legitimately hand over a one-shot iterable — and
    # this function used it twice, computing the primary path and then blowing up the
    # verification with "cannot compute over an empty temperature series". A verifier that
    # fails on valid input is worse than no verifier: it trains the operator to ignore it.
    series = _as_readings(readings)
    disagreements: list[str] = []

    # Resolve the envelope with explicit `is None` checks, never truthiness. A legitimate
    # 0.0 °C bound is falsy, so `envelope_lower_c or label_lower_c` silently discarded it and
    # the checker evaluated a DIFFERENT envelope than `disposition()` did — manufacturing a
    # disagreement, and exit code 3, on a shipment the primary logic handled correctly. For a
    # module whose whole meaning is "a disagreement means do not trust this bundle", a false
    # disagreement is the worst thing it can produce.
    envelope_lower = (
        result.label_lower_c if result.envelope_lower_c is None else result.envelope_lower_c
    )
    envelope_upper = (
        result.label_upper_c if result.envelope_upper_c is None else result.envelope_upper_c
    )
    has_envelope = result.envelope_lower_c is not None or result.envelope_upper_c is not None

    try:
        independent_mkt: float | None = recompute_mkt_directly(
            series, policy.activation_energy_j_per_mol
        )
    except ArithmeticError as exc:
        independent_mkt = None
        disagreements.append(f"independent MKT could not be computed: {exc}")

    minutes_out, _total = _recount_excursion_minutes(
        series, result.label_lower_c, result.label_upper_c
    )

    mkt_difference: float | None = None
    if independent_mkt is not None:
        mkt_difference = abs(independent_mkt - result.mkt_c)
        if mkt_difference > AGREEMENT_TOLERANCE_C:
            disagreements.append(
                f"MKT disagrees: primary {result.mkt_c:.6f} °C vs independent "
                f"{independent_mkt:.6f} °C (difference {mkt_difference:.3e} °C, tolerance "
                f"{AGREEMENT_TOLERANCE_C:.0e})"
            )

    if abs(minutes_out - result.excursion.minutes_out_of_range) > AGREEMENT_TOLERANCE_MIN:
        disagreements.append(
            f"excursion minutes disagree: primary "
            f"{result.excursion.minutes_out_of_range:.6f} vs independent {minutes_out:.6f}"
        )

    # Re-derive the verdict from the independent numbers, applying the policy afresh. This is
    # a deliberately simplified restatement of disposition()'s rules: if the two ever diverge
    # in structure, that divergence is itself a finding worth surfacing.
    allowance = policy.allowed_excursion_minutes
    consumed = (
        (100.0 if minutes_out > 0 else 0.0)
        if allowance <= 0
        else 100.0 * minutes_out / allowance
    )
    reference_mkt = independent_mkt if independent_mkt is not None else result.mkt_c

    if policy.freeze_is_disqualifying and any(r.celsius < envelope_lower for r in series):
        independent_verdict = QUARANTINE_RETEST
    elif has_envelope and any(
        r.celsius > envelope_upper or r.celsius < envelope_lower for r in series
    ):
        independent_verdict = QUARANTINE_RETEST
    elif consumed >= policy.destroy_at_pct:
        independent_verdict = DESTROY
    elif reference_mkt > result.label_upper_c or consumed >= policy.retest_at_pct:
        independent_verdict = QUARANTINE_RETEST
    else:
        independent_verdict = RELEASE

    if independent_verdict != result.verdict:
        disagreements.append(
            f"VERDICT DISAGREES: primary says {result.verdict}, independent recomputation "
            f"says {independent_verdict}. Do not present this bundle."
        )

    return CrossCheck(
        agrees=not disagreements,
        primary_verdict=result.verdict,
        independent_verdict=independent_verdict,
        primary_mkt_c=result.mkt_c,
        independent_mkt_c=independent_mkt,
        mkt_difference_c=mkt_difference,
        primary_minutes_out=result.excursion.minutes_out_of_range,
        independent_minutes_out=minutes_out,
        disagreements=tuple(disagreements),
    )
