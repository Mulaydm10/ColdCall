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
    "LocationEvidence",
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
    """What is actually known about *where* the consignment was, and when it was known.

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
    covers_window: bool
    """Whether any fix falls inside the correlated window. When False the coordinate is a
    last-known position and the attribution rests on an assumption, not an observation."""
    gap_hours: float
    """Hours from the latest fix to the start of the correlated window. Zero when covered."""

    def to_dict(self) -> dict[str, object]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "provenance": (
                "position observed during the correlated window"
                if self.covers_window
                else "LAST-KNOWN POSITION — no fix falls inside the correlated window"
            ),
            "fix_count": self.fix_count,
            "earliest_fix": self.earliest_fix,
            "latest_fix": self.latest_fix,
            "gap_hours_to_window": round(self.gap_hours, 1),
            "fix_spread_m": round(self.spread_m, 1),
            "covers_window": self.covers_window,
            "limit": (
                "Weather was fetched for this coordinate. Where the consignment actually was "
                "during the window is not established by these fixes."
                if not self.covers_window
                else "Fixes fall inside the correlated window."
            ),
        }


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
    location: LocationEvidence | None = None

    @property
    def qualified(self) -> bool:
        """True when the attribution rests on an assumption about location, not an observation.

        The attribution is not withdrawn — a 12 °C gap against a regional November ambient is
        not explained by having been a few hundred metres away. But "qualified" has to be
        machine-readable, because a downstream reader that only checks `attribution` would
        otherwise treat an assumed location exactly like an observed one.
        """
        return self.location is not None and not self.location.covers_window

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
            "location_evidence": None if self.location is None else self.location.to_dict(),
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
        location: what is known about where the consignment was. When the fixes do not
            temporally cover the correlated window, the attribution is marked ``qualified``
            and says so in its own notes — the weather is real, but which weather applies
            rests on an assumption.

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
            location=location,
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
            location=location,
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

    if location is not None and not location.covers_window:
        # State the assumption in the record, not only in prose. A reader who checks
        # `attribution` and stops must still be able to find this by checking `qualified`.
        notes.append(
            f"QUALIFIED: the coordinate is a LAST-KNOWN POSITION from {location.latest_fix}, "
            f"{location.gap_hours:.1f} h before this window began, and the {location.fix_count} "
            f"available fixes span {location.spread_m:.0f} m. Where the consignment actually "
            f"was during the excursion is not established. This attribution assumes it "
            f"remained in weather comparable to that coordinate's — plausible for a gap this "
            f"size against a regional ambient, but an assumption, not an observation."
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
        location=location,
    )
