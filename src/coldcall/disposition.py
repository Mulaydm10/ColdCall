"""The regulatory disposition decision: release, quarantine-and-retest, or destroy.

Where this sits
---------------
``mkt.py`` holds the primitives — mean kinetic temperature, excursion accounting, and the
stability budget. They are deliberately conservative and speak a three-way vocabulary of
``release`` / ``review`` / ``quarantine`` that answers "is this clean?".

This module answers the question a QA director actually has to sign: **what happens to the
pallet?** That is a different question with a different vocabulary — ``release``,
``quarantine_retest``, ``destroy`` — and a different set of inputs, because "destroy" is an
irreversible commercial act and "retest" costs money and time.

Nothing here is an LLM judgement. The agent gathers the telemetry, explains the output, and
drafts the deviation report; every number below is arithmetic that a reviewer can re-run.

What is regulation and what is ours
-----------------------------------
This distinction is load-bearing and must survive into the README and the demo narration.

* **Anchored in regulation.** The MKT formula (USP <1079>, ICH Q1A), the concept of a labelled
  storage range with a permitted excursion range, and the principle that cumulative thermal
  stress is what matters rather than a single peak (WHO TRS-999 Annex 5).
* **Our configurable policy.** The *thresholds* that turn a budget percentage into a verdict —
  ``retest_at_pct`` and ``destroy_at_pct`` below — and the excursion *duration* allowance in
  hours. Real drug labels state a permitted excursion **range** (e.g. 15–30 °C) but, in the
  general case, no permitted **duration**. Choosing a duration is a policy decision that a
  real quality system makes from the product's own stability data. We surface it as an input,
  cite where our value came from, and never present it as if the label said it.

The Arrhenius potency estimate is labelled an estimate everywhere it appears, including in
the emitted JSON, because a first-order model with an assumed rate constant is not a potency
assay and must never be shown as one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from coldcall.mkt import (
    DEFAULT_ACTIVATION_ENERGY_J_PER_MOL,
    GAS_CONSTANT_J_PER_MOL_K,
    ExcursionSummary,
    Reading,
    _as_readings,
    excursion_summary,
    mean_kinetic_temperature,
)

__all__ = [
    "DEFAULT_DESTROY_AT_PCT",
    "DEFAULT_POTENCY_RATE_PER_DAY",
    "DEFAULT_POTENCY_REF_C",
    "DEFAULT_RETEST_AT_PCT",
    "Disposition",
    "DispositionPolicy",
    "RELEASE",
    "QUARANTINE_RETEST",
    "DESTROY",
    "disposition",
    "potency_estimate_pct",
]

#: Verdict vocabulary. Three strings, fixed, because they are written into the incident
#: record and read by downstream systems — see the ``incidents.verdict`` column.
RELEASE = "release"
QUARANTINE_RETEST = "quarantine_retest"
DESTROY = "destroy"

#: Fraction of the excursion allowance at which the shipment can no longer be waved through
#: and must be quarantined pending a potency retest. **Demo policy, not regulation.**
DEFAULT_RETEST_AT_PCT = 50.0

#: Fraction at which the allowance is considered spent and the material is not releasable.
#: **Demo policy, not regulation.**
DEFAULT_DESTROY_AT_PCT = 100.0

#: First-order degradation rate at the reference temperature, per day. A generic small value
#: standing in for a real product's measured rate; it is an ESTIMATE input, and the emitted
#: JSON says so. Override it whenever a product's actual stability data is available.
DEFAULT_POTENCY_RATE_PER_DAY = 1.0e-4

#: Reference temperature for the potency estimate, °C. Defaults to the midpoint of USP
#: Controlled Room Temperature (20–25 °C), which is the storage class this build replays.
DEFAULT_POTENCY_REF_C = 22.5


def potency_estimate_pct(
    readings: object,
    reference_temp_c: float = DEFAULT_POTENCY_REF_C,
    rate_per_day_at_reference: float = DEFAULT_POTENCY_RATE_PER_DAY,
    activation_energy_j_per_mol: float = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL,
) -> float:
    """Estimate remaining potency (%) after the recorded thermal history.

    First-order decay whose rate constant is scaled by Arrhenius from a reference
    temperature::

        k(T) = k_ref · exp[ (ΔH/R) · (1/T_ref − 1/T) ]
        remaining = Π exp(−k(Tᵢ) · Δtᵢ)

    This is **an estimate, not an assay.** It uses an assumed rate constant and an assumed
    activation energy; a real release decision rests on the potency test that ``retest``
    calls for, which is exactly why the verdict vocabulary has a retest option in it.

    Raises:
        ValueError: on an empty series, a non-positive rate, or a non-finite reference.
    """
    if not math.isfinite(reference_temp_c) or reference_temp_c <= -273.15:
        raise ValueError(
            f"reference temperature must be a real temperature, got {reference_temp_c!r}"
        )
    if not math.isfinite(rate_per_day_at_reference) or rate_per_day_at_reference < 0:
        raise ValueError(
            f"rate constant must be non-negative and finite, got {rate_per_day_at_reference!r}"
        )
    if not math.isfinite(activation_energy_j_per_mol) or activation_energy_j_per_mol <= 0:
        raise ValueError(
            f"activation energy must be positive and finite, got {activation_energy_j_per_mol!r}"
        )

    series = _as_readings(readings)
    dh_over_r = activation_energy_j_per_mol / GAS_CONSTANT_J_PER_MOL_K
    ref_k = reference_temp_c + 273.15

    # Accumulate the exponent rather than multiplying probabilities: a long record is
    # thousands of factors, and repeated multiplication of near-1.0 floats drifts.
    total_exponent = math.fsum(
        -rate_per_day_at_reference
        * math.exp(dh_over_r * (1.0 / ref_k - 1.0 / r.kelvin))
        * (r.minutes / 1440.0)
        for r in series
    )
    return 100.0 * math.exp(total_exponent)


@dataclass(frozen=True, slots=True)
class DispositionPolicy:
    """The configurable half of the decision. Every field here is ours, not the label's.

    Kept as an explicit object rather than loose keyword arguments so that the policy in
    force can be serialised into the incident record alongside the verdict. An auditor
    re-deriving the decision needs the thresholds that were applied at the time, not the
    thresholds that happen to be in the code today.
    """

    allowed_excursion_hours: float
    retest_at_pct: float = DEFAULT_RETEST_AT_PCT
    destroy_at_pct: float = DEFAULT_DESTROY_AT_PCT
    freeze_is_disqualifying: bool = True
    activation_energy_j_per_mol: float = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL
    potency_reference_c: float = DEFAULT_POTENCY_REF_C
    potency_rate_per_day: float = DEFAULT_POTENCY_RATE_PER_DAY
    source: str = "ColdCall demo policy — not a regulatory limit"
    """Where these numbers came from. Written verbatim into the incident record."""

    def __post_init__(self) -> None:
        if not math.isfinite(self.allowed_excursion_hours) or self.allowed_excursion_hours < 0:
            raise ValueError(
                f"allowed excursion must be a non-negative finite number of hours, "
                f"got {self.allowed_excursion_hours!r}"
            )
        # Finiteness is checked before ordering, because `inf <= inf` is true: a policy of
        # retest=inf, destroy=inf would pass an ordering-only check and then never reach
        # either threshold, silently releasing arbitrarily over-budget material.
        for field_name, value in (
            ("retest_at_pct", self.retest_at_pct),
            ("destroy_at_pct", self.destroy_at_pct),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite, got {value!r}")
        if not 0 < self.retest_at_pct <= self.destroy_at_pct:
            raise ValueError(
                f"thresholds must satisfy 0 < retest ({self.retest_at_pct}) "
                f"<= destroy ({self.destroy_at_pct})"
            )

    @property
    def allowed_excursion_minutes(self) -> float:
        return self.allowed_excursion_hours * 60.0


@dataclass(frozen=True, slots=True)
class Disposition:
    """A signed-off-able verdict, carrying every input needed to re-derive it."""

    verdict: str
    mkt_c: float
    budget_consumed_pct: float
    est_potency_pct: float
    excursion: ExcursionSummary
    label_lower_c: float
    label_upper_c: float
    policy: DispositionPolicy
    envelope_lower_c: float | None
    """Lower bound of the label's permitted excursion range, or ``None`` when the label states
    no separate excursion range. ``None`` is not the same as "equal to the storage bound": it
    means there is no wider envelope to breach, so the beyond-envelope rule does not apply."""
    envelope_upper_c: float | None
    envelope_minutes_outside: float
    """Time spent outside the permitted excursion range — conditions the label makes no
    stability claim about at all, as distinct from time merely outside the storage range."""
    rationale: tuple[str, ...] = field(default_factory=tuple)

    @property
    def margin_pct(self) -> float:
        """Percentage points of budget between this shipment and the next-worse verdict.

        A verdict that is one point from flipping is a different fact from one that clears
        by forty, and the human signing it deserves to be told which they are looking at.
        Reported in the JSON, and the reason the demo can honestly say "move the policy line
        two points and this pallet quarantines instead".

        Zero once the worst verdict is reached — there is nothing further to fall to.
        """
        if self.verdict == DESTROY:
            return 0.0
        target = (
            self.policy.retest_at_pct
            if self.verdict == RELEASE
            else self.policy.destroy_at_pct
        )
        return max(0.0, target - self.budget_consumed_pct)

    @property
    def is_borderline(self) -> bool:
        """Within five points of flipping. Threshold is presentational, not regulatory."""
        return 0.0 < self.margin_pct <= 5.0

    @property
    def is_irreversible(self) -> bool:
        """Whether acting on this verdict destroys value that cannot be recovered.

        The approval gate keys off this. ``release`` ships the goods and ``destroy`` bins
        them; both are one-way. ``quarantine_retest`` is the conservative middle and is the
        only verdict that leaves every option open — which is why the agent is allowed to
        propose it after a denial.
        """
        return self.verdict in (RELEASE, DESTROY)

    def to_dict(self) -> dict[str, Any]:
        """The JSON the sandbox driver prints and the evidence bundle carries."""
        return {
            "verdict": self.verdict,
            "mkt_c": round(self.mkt_c, 3),
            "budget_consumed_pct": round(self.budget_consumed_pct, 2),
            "est_potency_pct": round(self.est_potency_pct, 4),
            "est_potency_disclaimer": (
                "First-order Arrhenius ESTIMATE from an assumed rate constant. "
                "Not a potency assay; a retest verdict calls for the real thing."
            ),
            "label": {
                "lower_c": self.label_lower_c,
                "upper_c": self.label_upper_c,
                "excursion_permitted_lower_c": self.envelope_lower_c,
                "excursion_permitted_upper_c": self.envelope_upper_c,
            },
            "minutes_beyond_permitted_envelope": round(self.envelope_minutes_outside, 2),
            "excursion": {
                "minutes_total": self.excursion.minutes_total,
                "minutes_out_of_range": self.excursion.minutes_out_of_range,
                "minutes_above": self.excursion.minutes_above,
                "minutes_below": self.excursion.minutes_below,
                "max_c": self.excursion.max_celsius,
                "min_c": self.excursion.min_celsius,
                "peak_above_c": round(self.excursion.peak_above_c, 3),
                "peak_below_c": round(self.excursion.peak_below_c, 3),
            },
            "policy": {
                "allowed_excursion_hours": self.policy.allowed_excursion_hours,
                "retest_at_pct": self.policy.retest_at_pct,
                "destroy_at_pct": self.policy.destroy_at_pct,
                "freeze_is_disqualifying": self.policy.freeze_is_disqualifying,
                "activation_energy_j_per_mol": self.policy.activation_energy_j_per_mol,
                # The potency estimate is only re-derivable if its inputs are recorded with
                # it. Reporting the figure without them makes an auditable number
                # unauditable.
                "potency_reference_c": self.policy.potency_reference_c,
                "potency_rate_per_day": self.policy.potency_rate_per_day,
                "source": self.policy.source,
                "note": (
                    "Thresholds and the excursion duration are ColdCall policy inputs, "
                    "not label text. The MKT formula and the labelled range are the "
                    "regulation-anchored parts."
                ),
            },
            "margin_pct": round(self.margin_pct, 2),
            "is_borderline": self.is_borderline,
            "rationale": list(self.rationale),
            "requires_human_approval": self.is_irreversible,
        }


def disposition(
    readings: object,
    label_lower_c: float,
    label_upper_c: float,
    policy: DispositionPolicy,
    excursion_lower_c: float | None = None,
    excursion_upper_c: float | None = None,
) -> Disposition:
    """Decide the disposition of a shipment from its recorded temperature history.

    Two bands, not one
    ------------------
    A real label states both: a **storage range** ("store at 20–25 °C") and a **permitted
    excursion range** ("excursions permitted to 15–30 °C"). They mean different things and
    conflating them gets the verdict wrong in both directions:

    * Time outside the *storage* range is what spends the excursion budget.
    * Time outside the *permitted excursion* range is a condition the label does not cover at
      all, and no amount of remaining budget makes it releasable on the arithmetic alone.

    Passing only the storage band — which this function used to do — treats a labelled-and-
    permitted 18 °C as a freeze, and lets a brief 35 °C spike through whenever MKT and the
    time percentage stay low. Both are wrong. When the excursion band is omitted it falls
    back to the storage band, which is the conservative reading for a label that states no
    excursion range.

    The rules, applied in order of severity, with the first match winning:

    1. **Freeze**, when ``freeze_is_disqualifying``: time below the *permitted excursion*
       minimum. A freeze is a product-integrity question, not a budget item, and it is never
       waved through on a percentage.
    2. **Beyond the permitted envelope**: any time outside the label's own excursion range
       quarantines for retest, regardless of budget. The product experienced conditions the
       label makes no claim about.
    3. **Allowance spent** — budget consumed at or above ``destroy_at_pct`` — leaves no
       basis on which the material can be released.
    4. **MKT above the labelled maximum**, or budget consumed at or above ``retest_at_pct``:
       quarantine pending a potency retest. An MKT above the label means the *cumulative*
       thermal stress exceeded what the product is labelled for, whatever the clock says.
    5. Otherwise **release**, logging the deviation if the range was left at all.

    Note that rule 3 is deliberately reachable only through the time budget. A single
    catastrophic spike inflates MKT and lands on retest, not destruction — the arithmetic
    should never be the thing that condemns a pallet on its own.
    """
    # Whether the label states a separate excursion range at all. When it does not, there is
    # no wider envelope to breach and rule 2 must not fire — otherwise the fallback collapses
    # onto the storage band and *every* excursion becomes "beyond the envelope", making the
    # budget rules unreachable.
    has_envelope = excursion_lower_c is not None or excursion_upper_c is not None
    envelope_lower = label_lower_c if excursion_lower_c is None else excursion_lower_c
    envelope_upper = label_upper_c if excursion_upper_c is None else excursion_upper_c
    if envelope_lower > label_lower_c or envelope_upper < label_upper_c:
        raise ValueError(
            f"the permitted excursion range {envelope_lower:g}-{envelope_upper:g} °C must "
            f"contain the labelled storage range {label_lower_c:g}-{label_upper_c:g} °C"
        )

    series: list[Reading] = _as_readings(readings)
    exc = excursion_summary(series, label_lower_c, label_upper_c)
    envelope = excursion_summary(series, envelope_lower, envelope_upper)
    mkt = mean_kinetic_temperature(series, policy.activation_energy_j_per_mol)
    potency = potency_estimate_pct(
        series,
        reference_temp_c=policy.potency_reference_c,
        rate_per_day_at_reference=policy.potency_rate_per_day,
        activation_energy_j_per_mol=policy.activation_energy_j_per_mol,
    )

    allowance_min = policy.allowed_excursion_minutes
    if allowance_min <= 0:
        consumed_pct = 100.0 if exc.minutes_out_of_range > 0 else 0.0
    else:
        consumed_pct = 100.0 * exc.minutes_out_of_range / allowance_min

    rationale = [
        f"MKT over the full record: {mkt:.2f} °C against a labelled range of "
        f"{label_lower_c:g}–{label_upper_c:g} °C (USP <1079> method, ΔH "
        f"{policy.activation_energy_j_per_mol:g} J/mol).",
        f"Time out of labelled range: {exc.minutes_out_of_range:.1f} min of "
        f"{exc.minutes_total:.1f} min recorded "
        f"({exc.minutes_above:.1f} above, {exc.minutes_below:.1f} below); "
        f"peak {exc.max_celsius:g} °C."
        + (
            f" Of that, {envelope.minutes_out_of_range:.1f} min fell outside the label's own "
            f"permitted excursion range of {envelope_lower:g}-{envelope_upper:g} °C."
            if has_envelope
            else ""
        ),
        f"Stability budget consumed: {consumed_pct:.1f}% of a "
        f"{policy.allowed_excursion_hours:g} h allowance ({policy.source}).",
        f"Estimated potency remaining: {potency:.2f}% — first-order Arrhenius ESTIMATE, "
        f"not an assay.",
    ]

    def _margin_note(verdict: str) -> str | None:
        """Say how close the call was, in the same breath as making it."""
        if verdict == DESTROY:
            return None
        target = policy.retest_at_pct if verdict == RELEASE else policy.destroy_at_pct
        gap = target - consumed_pct
        worse = QUARANTINE_RETEST if verdict == RELEASE else DESTROY
        if gap <= 5.0:
            return (
                f"Borderline: {gap:.1f} percentage points of budget from a {worse} verdict. "
                f"A policy line at {consumed_pct:.1f}% instead of {target:g}% would flip this."
            )
        return f"Margin: {gap:.1f} percentage points of budget before this becomes {worse}."

    if policy.freeze_is_disqualifying and (
        envelope.minutes_below if has_envelope else exc.minutes_below
    ) > 0:
        verdict = QUARANTINE_RETEST
        rationale.append(
            f"Freeze event: "
            f"{(envelope.minutes_below if has_envelope else exc.minutes_below):.1f} min below "
            f"{(envelope_lower if has_envelope else label_lower_c):g} °C "
            f"(minimum {exc.min_celsius:g} °C)"
            + (
                ", beneath what the label permits even as an excursion"
                if has_envelope
                else ""
            )
            + ". Product integrity cannot be assumed from time-at-temperature alone — "
            "quarantine and retest."
        )
    elif has_envelope and envelope.minutes_out_of_range > 0:
        verdict = QUARANTINE_RETEST
        rationale.append(
            f"Beyond the permitted excursion envelope: "
            f"{envelope.minutes_out_of_range:.1f} min outside "
            f"{envelope_lower:g}-{envelope_upper:g} °C (peak {envelope.max_celsius:g} °C). The "
            f"label makes no stability claim about these conditions, so remaining budget does "
            f"not make the material releasable — quarantine and retest."
        )
    elif consumed_pct >= policy.destroy_at_pct:
        verdict = DESTROY
        rationale.append(
            f"Excursion allowance fully consumed ({consumed_pct:.1f}% ≥ "
            f"{policy.destroy_at_pct:g}%). No remaining basis for release "
            f"(WHO TRS-999 Annex 5, excursion evaluation)."
        )
    elif mkt > label_upper_c:
        verdict = QUARANTINE_RETEST
        rationale.append(
            f"MKT {mkt:.2f} °C exceeds the labelled maximum {label_upper_c:g} °C: cumulative "
            f"thermal stress is above label regardless of elapsed time — quarantine and retest."
        )
    elif consumed_pct >= policy.retest_at_pct:
        verdict = QUARANTINE_RETEST
        rationale.append(
            f"Material portion of the allowance consumed ({consumed_pct:.1f}% ≥ "
            f"{policy.retest_at_pct:g}%) — quarantine pending a potency retest before release."
        )
    else:
        verdict = RELEASE
        if exc.in_range:
            rationale.append(
                "Held within the labelled range for the entire record — releasable."
            )
        else:
            rationale.append(
                f"Within the allowance ({consumed_pct:.1f}% < {policy.retest_at_pct:g}%) "
                f"and MKT in band — releasable; log the deviation."
            )

    margin_note = _margin_note(verdict)
    if margin_note:
        rationale.append(margin_note)

    return Disposition(
        verdict=verdict,
        mkt_c=mkt,
        budget_consumed_pct=consumed_pct,
        est_potency_pct=potency,
        excursion=exc,
        label_lower_c=label_lower_c,
        label_upper_c=label_upper_c,
        policy=policy,
        envelope_lower_c=envelope_lower if has_envelope else None,
        envelope_upper_c=envelope_upper if has_envelope else None,
        envelope_minutes_outside=envelope.minutes_out_of_range if has_envelope else 0.0,
        rationale=tuple(rationale),
    )
