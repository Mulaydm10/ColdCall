"""Mean kinetic temperature and excursion accounting for cold-chain shipments.

Why this module exists at all
-----------------------------
An LLM must never be the thing that decides whether a pharmaceutical shipment is still
within its stability budget. That decision is arithmetic with a regulatory definition
behind it, it has to be reproducible, and it has to be auditable by someone who does not
trust the agent. So the agent's job is to *gather* the telemetry and *explain* the result;
the number itself comes from here, deterministically, with the inputs recorded.

Mean kinetic temperature (MKT)
------------------------------
MKT is the single isothermal temperature that would produce the same amount of thermal
degradation as the actual, varying temperature history over the same period. It is defined
by the Arrhenius relationship (the form given in USP General Chapter <1079> and ICH Q1A):

                          ΔH / R
    MKT = ---------------------------------------
           -ln( Σ wᵢ·exp(-ΔH / (R·Tᵢ)) / Σ wᵢ )

where Tᵢ are absolute temperatures (K), wᵢ the time each reading represents, R the gas
constant, and ΔH an assumed activation energy of degradation.

MKT is always greater than or equal to the (time-weighted) arithmetic mean, and strictly
greater whenever the temperature varies at all. That is the entire point of using it: a
shipment that spends an hour at 15 °C and an hour at 1 °C is *not* equivalent to one held
steadily at 8 °C, and the arithmetic mean would claim it was.

Conventions
-----------
* ``DEFAULT_ACTIVATION_ENERGY_J_PER_MOL`` is 83 144 J/mol, the value in common regulatory
  use. It is chosen so that ΔH/R lands within a rounding error of 10 000 K (9 999.91 K with
  the CODATA gas constant used here, exactly 10 000 K if R is taken as the rounded 8.3144),
  which is why worked examples in the literature come out in round numbers. Any other
  activation energy may be passed explicitly, and the value used is echoed back in the
  result so a report can state its own assumptions.
* Temperatures are handled in °C at the boundary (that is what telemetry and drug labels
  speak) and converted to kelvin internally.
* Summation uses the log-sum-exp form rather than summing the exponentials directly. The
  exponentials involved are around 1e-16, and naive summation of many such terms loses
  precision exactly where a borderline shipment would be decided.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "ABSOLUTE_ZERO_C",
    "DEFAULT_ACTIVATION_ENERGY_J_PER_MOL",
    "GAS_CONSTANT_J_PER_MOL_K",
    "ExcursionSummary",
    "Reading",
    "StabilityBudget",
    "excursion_summary",
    "mean_kinetic_temperature",
    "stability_budget",
]

#: Gas constant, J/(mol·K). CODATA value, truncated as USP <1079> worked examples use it.
GAS_CONSTANT_J_PER_MOL_K = 8.314472

#: Assumed activation energy of degradation, J/mol. See module docstring for why this value.
DEFAULT_ACTIVATION_ENERGY_J_PER_MOL = 83144.0

#: Absolute zero in °C. Readings at or below this are physically impossible, not merely odd.
ABSOLUTE_ZERO_C = -273.15


@dataclass(frozen=True, slots=True)
class Reading:
    """One temperature observation and the span of time it stands for.

    ``minutes`` is the duration this reading represents, not a timestamp. Loggers usually
    sample on a fixed interval, in which case every reading carries the same weight and the
    value is the sampling period. When a logger drops out and resumes, the reading that
    covers the gap should carry the longer duration, otherwise the gap silently disappears
    from the average.
    """

    celsius: float
    minutes: float = 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.celsius):
            raise ValueError(f"temperature must be finite, got {self.celsius!r}")
        if self.celsius <= ABSOLUTE_ZERO_C:
            raise ValueError(
                f"temperature {self.celsius} °C is at or below absolute zero; "
                "this is a sensor fault, not a cold shipment"
            )
        if not math.isfinite(self.minutes) or self.minutes <= 0:
            raise ValueError(
                f"duration must be a positive finite number of minutes, got {self.minutes!r}"
            )

    @property
    def kelvin(self) -> float:
        return self.celsius - ABSOLUTE_ZERO_C


def _as_readings(readings: object) -> list[Reading]:
    """Accept either Reading objects or bare numbers, so callers are not forced to wrap."""
    if isinstance(readings, (str, bytes)) or not hasattr(readings, "__iter__"):
        raise TypeError("readings must be an iterable of Reading or of numbers")
    out: list[Reading] = []
    for item in readings:  # type: ignore[union-attr]
        if isinstance(item, Reading):
            out.append(item)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            out.append(Reading(float(item)))
        else:
            raise TypeError(f"expected Reading or number, got {type(item).__name__}")
    if not out:
        raise ValueError("cannot compute over an empty temperature series")
    return out


def mean_kinetic_temperature(
    readings: object,
    activation_energy_j_per_mol: float = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL,
) -> float:
    """Return the mean kinetic temperature of a series, in °C.

    Args:
        readings: ``Reading`` objects, or bare numbers treated as equally weighted °C values.
        activation_energy_j_per_mol: assumed ΔH. Must be positive; the default is the value
            that makes published worked examples reproducible (see module docstring).

    Returns:
        MKT in °C. For a constant series this is exactly that temperature; for any varying
        series it is strictly above the time-weighted arithmetic mean.

    Raises:
        ValueError: on an empty series, a non-positive activation energy, or a reading at or
            below absolute zero.
    """
    if not math.isfinite(activation_energy_j_per_mol) or activation_energy_j_per_mol <= 0:
        raise ValueError(
            f"activation energy must be positive and finite, got {activation_energy_j_per_mol!r}"
        )

    series = _as_readings(readings)
    dh_over_r = activation_energy_j_per_mol / GAS_CONSTANT_J_PER_MOL_K

    # Log-sum-exp: ln( Σ wᵢ·e^{aᵢ} / Σ wᵢ ) computed as
    #     (m + ln Σ wᵢ·e^{aᵢ-m}) - ln Σ wᵢ ,  with m = max aᵢ
    # which keeps every term inside float range no matter how cold the shipment ran.
    exponents = [-dh_over_r / r.kelvin for r in series]
    weights = [r.minutes for r in series]
    shift = max(exponents)
    weighted = math.fsum(w * math.exp(a - shift) for a, w in zip(exponents, weights, strict=True))
    total_weight = math.fsum(weights)
    log_mean = shift + math.log(weighted) - math.log(total_weight)

    return dh_over_r / -log_mean + ABSOLUTE_ZERO_C


@dataclass(frozen=True, slots=True)
class ExcursionSummary:
    """How far, and for how long, a shipment left its labelled storage range."""

    minutes_total: float
    minutes_above: float
    minutes_below: float
    max_celsius: float
    min_celsius: float
    peak_above_c: float
    """Largest overshoot above the upper limit, in °C. Zero if never exceeded."""
    peak_below_c: float
    """Largest undershoot below the lower limit, in °C. Zero if never exceeded."""

    @property
    def minutes_out_of_range(self) -> float:
        return self.minutes_above + self.minutes_below

    @property
    def in_range(self) -> bool:
        return self.minutes_out_of_range == 0


def excursion_summary(
    readings: object,
    lower_c: float,
    upper_c: float,
) -> ExcursionSummary:
    """Account for time spent outside a labelled storage range (e.g. 2 °C to 8 °C).

    Freezing and overheating are tracked separately and never netted against each other:
    for most biologics a single freeze is disqualifying on its own, and a summary that let
    cold minutes cancel warm ones would hide exactly the event that matters.
    """
    if not (math.isfinite(lower_c) and math.isfinite(upper_c)):
        raise ValueError("storage limits must be finite")
    if lower_c >= upper_c:
        raise ValueError(f"lower limit {lower_c} °C must be below upper limit {upper_c} °C")

    series = _as_readings(readings)
    above = math.fsum(r.minutes for r in series if r.celsius > upper_c)
    below = math.fsum(r.minutes for r in series if r.celsius < lower_c)
    temps = [r.celsius for r in series]

    return ExcursionSummary(
        minutes_total=math.fsum(r.minutes for r in series),
        minutes_above=above,
        minutes_below=below,
        max_celsius=max(temps),
        min_celsius=min(temps),
        peak_above_c=max(0.0, max(temps) - upper_c),
        peak_below_c=max(0.0, lower_c - min(temps)),
    )


@dataclass(frozen=True, slots=True)
class StabilityBudget:
    """The verdict on a shipment, with every input needed to re-derive it.

    ``verdict`` is deliberately one of three plain strings rather than a boolean. "Release"
    and "quarantine" are decisions a human signs; "review" is the honest answer when the
    arithmetic is inside limits but the excursion profile is not clean, and collapsing it
    into either neighbour would be the agent overstepping.
    """

    mkt_celsius: float
    label_lower_c: float
    label_upper_c: float
    excursion: ExcursionSummary
    allowed_excursion_minutes: float
    activation_energy_j_per_mol: float
    verdict: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def excursion_minutes_remaining(self) -> float:
        return max(0.0, self.allowed_excursion_minutes - self.excursion.minutes_out_of_range)

    @property
    def budget_consumed_fraction(self) -> float:
        if self.allowed_excursion_minutes <= 0:
            return 1.0 if self.excursion.minutes_out_of_range > 0 else 0.0
        return self.excursion.minutes_out_of_range / self.allowed_excursion_minutes


def stability_budget(
    readings: object,
    label_lower_c: float,
    label_upper_c: float,
    allowed_excursion_minutes: float = 0.0,
    freeze_is_disqualifying: bool = True,
    activation_energy_j_per_mol: float = DEFAULT_ACTIVATION_ENERGY_J_PER_MOL,
) -> StabilityBudget:
    """Decide release / review / quarantine for a shipment, showing the work.

    The rules applied, in order of severity:

    1. Any time below the lower limit quarantines the shipment when
       ``freeze_is_disqualifying`` is set, regardless of how brief. For refrigerated
       biologics a freeze event is not a budget item, it is a product-integrity failure.
    2. An MKT above the labelled upper limit quarantines it. MKT is the regulatory measure
       of cumulative thermal stress; above the label there is no budget left to spend.
    3. Excursion minutes beyond ``allowed_excursion_minutes`` quarantine it.
    4. Anything else that left the range at all is returned as ``"review"`` — inside the
       budget, but not clean enough for the agent to wave through on its own.
    5. Otherwise ``"release"``.

    Args:
        allowed_excursion_minutes: the permitted time outside the range, which comes from
            the product's own stability data. It defaults to 0, i.e. no allowance, because
            assuming an allowance nobody granted is the dangerous direction to be wrong in.

    Returns:
        A ``StabilityBudget`` carrying the verdict, the reasons, and the inputs.
    """
    if allowed_excursion_minutes < 0 or not math.isfinite(allowed_excursion_minutes):
        raise ValueError(
            f"allowed excursion must be a non-negative finite number of minutes, "
            f"got {allowed_excursion_minutes!r}"
        )

    # Normalise once. Both calculations below coerce their input independently, so forwarding
    # the caller's object twice would exhaust a generator on the first pass and hand the second
    # an empty series. A one-shot iterable is a perfectly reasonable thing to be handed here.
    series = _as_readings(readings)
    excursion = excursion_summary(series, label_lower_c, label_upper_c)
    mkt = mean_kinetic_temperature(series, activation_energy_j_per_mol)

    reasons: list[str] = []
    verdict = "release"

    if freeze_is_disqualifying and excursion.minutes_below > 0:
        verdict = "quarantine"
        reasons.append(
            f"freeze event: {excursion.minutes_below:g} min below {label_lower_c:g} °C "
            f"(minimum {excursion.min_celsius:g} °C, {excursion.peak_below_c:g} °C under limit)"
        )
    if mkt > label_upper_c:
        verdict = "quarantine"
        reasons.append(
            f"MKT {mkt:.2f} °C exceeds labelled maximum {label_upper_c:g} °C"
        )
    if excursion.minutes_out_of_range > allowed_excursion_minutes:
        verdict = "quarantine"
        reasons.append(
            f"excursion budget exhausted: {excursion.minutes_out_of_range:g} min out of range "
            f"against an allowance of {allowed_excursion_minutes:g} min"
        )

    if verdict == "release" and not excursion.in_range:
        verdict = "review"
        reasons.append(
            f"{excursion.minutes_out_of_range:g} min out of range, within the "
            f"{allowed_excursion_minutes:g} min allowance — needs a human decision"
        )
    if verdict == "release":
        reasons.append(
            f"held within {label_lower_c:g}–{label_upper_c:g} °C for the whole "
            f"{excursion.minutes_total:g} min record; MKT {mkt:.2f} °C"
        )

    return StabilityBudget(
        mkt_celsius=mkt,
        label_lower_c=label_lower_c,
        label_upper_c=label_upper_c,
        excursion=excursion,
        allowed_excursion_minutes=allowed_excursion_minutes,
        activation_energy_j_per_mol=activation_energy_j_per_mol,
        verdict=verdict,
        reasons=tuple(reasons),
    )
