"""Route context: was the excursion explained by the weather, or by the shipment?

Why this earns its place
------------------------
The disposition maths answers *what happens to the pallet*. It cannot answer *why the pallet
warmed*, and those are different questions with different consequences:

* If the load simply tracked a hot day, the finding is **environmental exposure** — the CAPA is
  about routing, scheduling, or the shipping lane.
* If the load ran well above the outside air, the finding is a **containment failure** — the
  CAPA is about the packaging, the reefer unit, or the loading procedure. Nothing about the
  route would have prevented it.

A deviation record that says "the shipment reached 27 °C" and stops has skipped the only part
an investigator can act on. This module supplies the missing half from a historical weather
archive at the shipment's own coordinates, so the answer is evidence rather than narration.

The data
--------
Open-Meteo's **archive**, which serves **ERA5 reanalysis** — an observation-constrained
model, not a direct measurement at that coordinate. Keyless, free for non-commercial use.
It is retrospective rather than a forecast, which is what an investigation needs; but the
word for it is *reanalysis*, and nothing here should call it an observation.

Honest limits, which belong in any report that quotes this
----------------------------------------------------------
* **Point weather, moving cargo.** We query one coordinate. A multi-drop road leg covers
  ground; the ambient series is representative of the region, not of the truck's exact position
  minute by minute.
* **Hourly granularity** against telemetry that samples every ~12 minutes. Readings are matched
  to the nearest hour, so a sharp local swing between samples is invisible here.
* **Outside air, not the trailer.** A closed vehicle in sun runs hotter than the shade
  temperature ERA5 reports. So a *positive* gap is expected to some degree; it is the **size**
  of the gap that carries the signal, and the threshold for "large" is our policy, stated as
  such, not a regulatory value.

Stdlib only, like the rest of this package — it is uploaded into the sandbox and must import
against a stock interpreter.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

__all__ = [
    "AMBIENT_ARCHIVE_URL",
    "CONTAINMENT_GAP_C",
    "AmbientSeries",
    "LocationAssessment",
    "LocationEvidence",
    "OBSERVED",
    "LAST_KNOWN",
    "RECORDED_AFTER",
    "UNSTATED",
    "RouteContext",
    "attribute_excursion",
    "fetch_ambient",
]

#: Open-Meteo's historical reanalysis endpoint. Keyless; no signup.
AMBIENT_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

#: Median °C by which the load must exceed outside air during the excursion before we call it
#: a containment failure rather than environmental exposure. **ColdCall policy, not a
#: regulatory value** — a closed vehicle in sun genuinely runs warmer than shade temperature,
#: so some positive gap is expected. Stated in every record that quotes an attribution.
CONTAINMENT_GAP_C = 5.0

#: How much is known about where the consignment was during the correlated window. Four
#: states, not a boolean: "nobody told us" and "we checked and it was stale" are different
#: facts, and collapsing them lets unknown provenance pass for verified provenance.
OBSERVED = "observed_during_window"
LAST_KNOWN = "last_known_position"
RECORDED_AFTER = "recorded_after_window"
UNSTATED = "provenance_unstated"


def _parse_fix(raw: str) -> datetime | None:
    """Parse a fix timestamp, assuming UTC when no offset is given."""
    try:
        parsed = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


#: Attribution vocabulary. Deliberately includes an "undetermined" option: an investigation
#: that cannot tell is a legitimate outcome, and forcing a cause is how bad CAPAs get written.
ENVIRONMENTAL = "environmental_exposure"
CONTAINMENT = "containment_failure"
UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class AmbientSeries:
    """Hourly outside-air temperatures at one coordinate, with their provenance."""

    latitude: float
    longitude: float
    times: tuple[datetime, ...]
    celsius: tuple[float, ...]
    source: str

    def at(self, when: datetime) -> float | None:
        """Outside air at the hour nearest ``when``, or None if it falls outside the series.

        Nearest rather than preceding: an excursion reading at 14:58 is better represented by
        the 15:00 observation than the 14:00 one, and rounding down would systematically lag
        the ambient curve behind the telemetry.
        """
        if not self.times:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when < self.times[0] - timedelta(hours=1) or when > self.times[-1] + timedelta(hours=1):
            return None

        index = bisect_left(self.times, when)
        candidates = [i for i in (index - 1, index) if 0 <= i < len(self.times)]
        if not candidates:
            return None
        best = min(candidates, key=lambda i: abs((self.times[i] - when).total_seconds()))
        value = self.celsius[best]
        return None if value is None or not math.isfinite(value) else value


@dataclass(frozen=True, slots=True)
class LocationEvidence:
    """The raw facts about *where* the consignment was fixed, and when.

    Deliberately holds no coverage claim. Whether these fixes cover the readings being
    correlated is a question about the **excursion window**, which only ``attribute_excursion``
    knows — computing it against the whole telemetry record instead meant a fix taken during a
    quiet in-range hour cleared the qualification for an excursion it never covered.

    A weather lookup is only as good as the coordinate it is given, and a coordinate has a
    timestamp. Treating a last-known position as an established location during a later
    excursion is the same class of overclaim as calling a reanalysis a measurement — the
    number may still be right, but the record must say what it rests on.
    """

    latitude: float
    longitude: float
    fix_count: int
    earliest_fix: str
    latest_fix: str
    spread_m: float
    """How far apart the fixes are — the radius of what "here" actually means."""

    def assess(self, window_start: datetime, window_end: datetime) -> LocationAssessment:
        """Resolve these fixes against the window actually being correlated."""
        latest = _parse_fix(self.latest_fix)
        earliest = _parse_fix(self.earliest_fix) or latest
        if latest is None or earliest is None:
            return LocationAssessment(self, UNSTATED, 0.0)

        # "Covers" means a fix falls inside the window, not merely that one exists nearby.
        if earliest <= window_end and latest >= window_start:
            return LocationAssessment(self, OBSERVED, 0.0)

        # Signed, and the sign is the whole point: `abs()` would narrate a fix taken AFTER the
        # excursion as a last-known position BEFORE it — a false temporal statement in a
        # regulated record. Positive means the fixes precede the window.
        if latest < window_start:
            return LocationAssessment(
                self, LAST_KNOWN, (window_start - latest).total_seconds() / 3600.0
            )
        return LocationAssessment(
            self, RECORDED_AFTER, -((earliest - window_end).total_seconds() / 3600.0)
        )


@dataclass(frozen=True, slots=True)
class LocationAssessment:
    """What the fixes turn out to say about the window that was correlated."""

    fixes: LocationEvidence | None
    confidence: str
    gap_hours: float
    """Signed. Positive: the fixes precede the window. Negative: they follow it. Zero when a
    fix falls inside it, or when no provenance was supplied at all."""

    @property
    def qualified(self) -> bool:
        """Anything other than an observed position leaves the attribution resting on an
        assumption — including *unstated*, which is the case a boolean alone used to hide."""
        return self.confidence != OBSERVED

    def to_dict(self) -> dict[str, object]:
        provenance = {
            OBSERVED: "position observed during the correlated window",
            LAST_KNOWN: "LAST-KNOWN POSITION — every fix predates the correlated window",
            RECORDED_AFTER: "POSITION RECORDED AFTER the correlated window — not where it was",
            UNSTATED: "PROVENANCE NOT SUPPLIED — no fix timestamp was given for this coordinate",
        }[self.confidence]
        document: dict[str, object] = {
            "confidence": self.confidence,
            "provenance": provenance,
            "gap_hours_to_window": round(self.gap_hours, 1),
            "gap_direction": (
                "fixes precede the window"
                if self.gap_hours > 0
                else "fixes follow the window"
                if self.gap_hours < 0
                else "not applicable"
            ),
            "limit": (
                "Fixes fall inside the correlated window."
                if self.confidence == OBSERVED
                else "Weather was fetched for this coordinate. Where the consignment actually "
                "was during the window is not established by these fixes."
            ),
        }
        if self.fixes is None:
            document["latitude"] = None
            document["longitude"] = None
            document["fix_count"] = 0
        else:
            document["latitude"] = self.fixes.latitude
            document["longitude"] = self.fixes.longitude
            document["fix_count"] = self.fixes.fix_count
            document["earliest_fix"] = self.fixes.earliest_fix
            document["latest_fix"] = self.fixes.latest_fix
            document["fix_spread_m"] = round(self.fixes.spread_m, 1)
        return document


@dataclass(frozen=True, slots=True)
class RouteContext:
    """What the weather says about an excursion, and how confident that is."""

    attribution: str
    median_gap_c: float | None
    """Median (internal − ambient) across the excursion readings. None if unmatched."""
    peak_internal_c: float
    peak_ambient_c: float | None
    matched_readings: int
    total_excursion_readings: int
    threshold_c: float
    notes: tuple[str, ...]
    location: LocationAssessment | None = None

    @property
    def qualified(self) -> bool:
        """True when the attribution rests on an assumption about location, not an observation.

        The attribution is not withdrawn — a 12 °C gap against a regional November ambient is
        not explained by having been a few hundred metres away. But "qualified" has to be
        machine-readable, because a downstream reader that only checks `attribution` would
        otherwise treat an assumed location exactly like an observed one.

        A missing assessment counts as qualified, not as verified. That was the same trap one
        level up: a reader checking only this boolean would have read "we were never told
        where it was" as "we confirmed where it was".
        """
        return self.location is None or self.location.qualified

    @property
    def coverage(self) -> float:
        if self.total_excursion_readings == 0:
            return 0.0
        return self.matched_readings / self.total_excursion_readings

    def to_dict(self) -> dict[str, object]:
        return {
            "attribution": self.attribution,
            "median_gap_c": None if self.median_gap_c is None else round(self.median_gap_c, 2),
            "peak_internal_c": self.peak_internal_c,
            "peak_ambient_c": self.peak_ambient_c,
            "matched_readings": self.matched_readings,
            "total_excursion_readings": self.total_excursion_readings,
            "coverage": round(self.coverage, 3),
            "containment_gap_threshold_c": self.threshold_c,
            "threshold_note": (
                "The gap threshold is ColdCall policy, not a regulatory value. A closed "
                "vehicle in sun runs warmer than the shade temperature the archive reports, "
                "so some positive gap is expected."
            ),
            "qualified": self.qualified,
            "location_confidence": (
                UNSTATED if self.location is None else self.location.confidence
            ),
            "location_evidence": (
                LocationAssessment(None, UNSTATED, 0.0).to_dict()
                if self.location is None
                else self.location.to_dict()
            ),
            "notes": list(self.notes),
        }


def fetch_ambient(
    latitude: float,
    longitude: float,
    start: datetime,
    end: datetime,
    timeout: float = 30.0,
) -> AmbientSeries:
    """Fetch hourly outside-air temperature for a coordinate and window.

    Raises:
        ValueError: on impossible coordinates or an inverted window.
        RuntimeError: if the archive is unreachable or answers in an unexpected shape. It
            raises rather than returning an empty series on purpose — an empty series would
            silently become "no weather context available", which reads like a finding rather
            than like the failed lookup it is.
    """
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"impossible coordinate: {latitude}, {longitude}")
    if end < start:
        raise ValueError("the window ends before it starts")

    query = urllib.parse.urlencode(
        {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            # Pad by a day either side: the archive works in whole local days, and an
            # excursion that straddles midnight would otherwise lose its tail.
            "start_date": (start - timedelta(days=1)).date().isoformat(),
            "end_date": (end + timedelta(days=1)).date().isoformat(),
            "hourly": "temperature_2m",
            "timezone": "UTC",
        }
    )
    url = f"{AMBIENT_ARCHIVE_URL}?{query}"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RuntimeError(f"could not reach the weather archive: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"the weather archive returned non-JSON: {exc}") from exc

    # Every shape assumption is checked before it is used. `.get` on a decoded list or string
    # raises AttributeError, which is not in the caller's except clause — so a malformed
    # response would have aborted a verdict that had already been computed, breaking this
    # module's own promise that route context is never fatal.
    if not isinstance(payload, dict):
        raise RuntimeError(f"archive returned {type(payload).__name__}, not an object")
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise RuntimeError(f"unexpected archive response shape: {str(payload)[:200]}")
    times_raw = hourly.get("time")
    temps_raw = hourly.get("temperature_2m")
    if not isinstance(times_raw, list) or not isinstance(temps_raw, list):
        raise RuntimeError(
            f"archive response has no usable hourly series: {str(hourly)[:200]}"
        )

    times: list[datetime] = []
    temps: list[float] = []
    for raw_time, raw_temp in zip(times_raw, temps_raw, strict=False):
        try:
            stamp = datetime.fromisoformat(str(raw_time))
        except (ValueError, TypeError):
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        times.append(stamp)
        temps.append(float(raw_temp) if isinstance(raw_temp, (int, float)) else float("nan"))

    if not times:
        raise RuntimeError("the weather archive returned no hourly observations")

    return AmbientSeries(
        latitude=latitude,
        longitude=longitude,
        times=tuple(times),
        celsius=tuple(temps),
        source=(
            f"Open-Meteo historical archive (ERA5 reanalysis), {latitude:.4f},{longitude:.4f}, "
            f"hourly temperature_2m — retrieved from {AMBIENT_ARCHIVE_URL}"
        ),
    )


def attribute_excursion(
    readings: list[tuple[datetime | None, float]],
    ambient: AmbientSeries,
    label_upper_c: float,
    threshold_c: float = CONTAINMENT_GAP_C,
    location: LocationEvidence | None = None,
) -> RouteContext:
    """Decide whether the excursion tracked the weather or ran away from it.

    Args:
        readings: ``(timestamp, internal °C)`` for the whole record, where the timestamp may
            be ``None``. Only readings above ``label_upper_c`` are attributed — the question is
            about the *excursion*, and including in-band time would dilute the gap toward the
            ambient baseline.

            A ``None`` timestamp counts toward the excursion total but can never be matched.
            Dropping such readings entirely would let the coverage figure describe only the
            timestamped subset — a report claiming full coverage while a third of the hot
            readings were never considered.
        ambient: outside air from :func:`fetch_ambient`.
        label_upper_c: the labelled maximum, which defines what counts as an excursion here.
        threshold_c: median gap above which this is a containment failure. Ours, not a
            regulation.
        location: the raw GPS fixes behind the coordinate. They are assessed **against the
            excursion window computed here**, not against the whole telemetry record: a fix
            taken during a quiet in-range hour says nothing about where the consignment was
            while it was warming. When the fixes do not cover that window — or when no
            provenance was supplied at all — the attribution is marked ``qualified`` and says
            so in its own notes.

    Returns:
        A :class:`RouteContext`. Returns ``undetermined`` — never a guess — when too few
        excursion readings could be matched to an ambient observation to support a claim.
    """
    if not math.isfinite(threshold_c) or threshold_c < 0:
        # nan makes every `>=` comparison false, so every excursion would be reported as
        # environmental exposure — a wrong cause, delivered confidently, from a typo.
        raise ValueError(
            f"containment gap threshold must be a non-negative finite number of °C, "
            f"got {threshold_c!r}"
        )

    hot = [(when, temp) for when, temp in readings if temp > label_upper_c]

    # Assess location against the EXCURSION window, which is what the weather is being
    # correlated with. Timestamps outside it are irrelevant to the question being asked.
    hot_stamps = [when for when, _ in hot if when is not None]
    if location is None or not hot_stamps:
        assessment = LocationAssessment(location, UNSTATED, 0.0)
    else:
        assessment = location.assess(min(hot_stamps), max(hot_stamps))

    if not hot:
        return RouteContext(
            attribution=UNDETERMINED,
            median_gap_c=None,
            peak_internal_c=max((t for _, t in readings), default=float("nan")),
            peak_ambient_c=None,
            matched_readings=0,
            total_excursion_readings=0,
            threshold_c=threshold_c,
            notes=("No reading exceeded the labelled maximum, so there is nothing to explain.",),
            location=assessment,
        )

    gaps: list[float] = []
    matched_ambient: list[float] = []
    for when, temp in hot:
        outside = None if when is None else ambient.at(when)
        if outside is None:
            continue
        gaps.append(temp - outside)
        matched_ambient.append(outside)

    peak_internal = max(t for _, t in hot)
    notes: list[str] = []

    # A claim needs enough matched readings to stand on. Half is a judgement call, stated
    # rather than hidden: below it the median is being carried by a minority of the excursion.
    # Ceiling, not floor: with floor division, 2 matches out of 5 hot readings (40 %) passed
    # a check meant to require half. A minority of the excursion was carrying a definitive
    # cause, which is the opposite of what the coverage rule is for.
    required = max(1, -(-len(hot) // 2))
    if not gaps or len(gaps) < required:
        notes.append(
            f"Only {len(gaps)} of {len(hot)} excursion readings could be matched to an "
            f"ambient observation (at least {required} needed) — too few to attribute a cause."
        )
        return RouteContext(
            attribution=UNDETERMINED,
            median_gap_c=None,
            peak_internal_c=peak_internal,
            peak_ambient_c=max(matched_ambient) if matched_ambient else None,
            matched_readings=len(gaps),
            total_excursion_readings=len(hot),
            threshold_c=threshold_c,
            notes=tuple(notes),
            location=assessment,
        )

    ordered = sorted(gaps)
    middle = len(ordered) // 2
    median_gap = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    peak_ambient = max(matched_ambient)

    if median_gap >= threshold_c:
        attribution = CONTAINMENT
        notes.append(
            f"The load ran a median {median_gap:.1f} °C above outside air across the "
            f"excursion (peak internal {peak_internal:g} °C against a peak ambient of "
            f"{peak_ambient:g} °C). The weather does not account for this: heat was retained "
            f"or generated inside the consignment. Investigate packaging, the reefer unit, "
            f"and loading procedure — routing changes would not have prevented it."
        )
    else:
        attribution = ENVIRONMENTAL
        notes.append(
            f"The load tracked outside air closely (median gap {median_gap:.1f} °C, peak "
            f"ambient {peak_ambient:g} °C against peak internal {peak_internal:g} °C). This "
            f"reads as environmental exposure rather than a containment failure — the "
            f"consignment was in conditions it could not have been protected from by "
            f"packaging alone. Investigate lane, schedule and dwell time."
        )

    notes.append(
        "Ambient is point weather from a reanalysis archive, hourly, in shade. The cargo "
        "moved and the trailer was not the open air, so treat the gap as indicative."
    )

    if assessment.qualified:
        # State the assumption in the record, not only in prose. A reader who checks
        # `attribution` and stops must still be able to find this by checking `qualified`.
        if assessment.confidence == UNSTATED and location is None:
            notes.append(
                "QUALIFIED: no provenance was supplied for this coordinate — nothing records "
                "when the position was taken, so whether it describes the consignment during "
                "the excursion is unknown. Unknown is not the same as verified."
            )
        elif assessment.confidence == RECORDED_AFTER:
            notes.append(
                f"QUALIFIED: every fix was recorded AFTER this window closed — the earliest "
                f"is {abs(assessment.gap_hours):.1f} h past its end, from "
                f"{location.fix_count if location else 0} fixes spanning "
                f"{location.spread_m if location else 0:.0f} m. It is where the consignment "
                f"ended up, not where it was while it warmed."
            )
        else:
            notes.append(
                f"QUALIFIED: the coordinate is a LAST-KNOWN POSITION from "
                f"{location.latest_fix if location else '?'}, {assessment.gap_hours:.1f} h "
                f"before this window began, and the {location.fix_count if location else 0} "
                f"available fixes span {location.spread_m if location else 0:.0f} m. Where the "
                f"consignment actually was during the excursion is not established. This "
                f"attribution assumes it remained in weather comparable to that coordinate's — "
                f"plausible for a gap this size against a regional ambient, but an assumption, "
                f"not an observation."
            )
    return RouteContext(
        attribution=attribution,
        median_gap_c=median_gap,
        peak_internal_c=peak_internal,
        peak_ambient_c=peak_ambient,
        matched_readings=len(gaps),
        total_excursion_readings=len(hot),
        threshold_c=threshold_c,
        notes=tuple(notes),
        location=assessment,
    )
