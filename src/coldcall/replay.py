"""Streaming replay of real shipment telemetry.

The source file this is built for is a single pretty-printed JSON array of roughly 400 MB.
That rules out ``json.load``: the demo machine should not need half a gigabyte of resident
memory to look at one shipment, and the agent's sandbox certainly should not. So this module
decodes objects out of the array incrementally, one at a time, and never holds more than a
buffer's worth of text.

It is deliberately tolerant of a truncated tail. Pulling a few megabytes of a large remote
file with an HTTP range request is the cheapest way to get a realistic fixture, and that
always ends mid-object; a parser that raised on it would make the cheap path unusable.

Nothing here imports anything outside the standard library, for the same reason the maths
module does not: this code runs inside the sandbox.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from coldcall.mkt import Reading

__all__ = ["TelemetryPoint", "ShipmentLeg", "iter_telemetry", "group_by_device", "to_readings"]

_CHUNK = 1 << 20


@dataclass(frozen=True, slots=True)
class TelemetryPoint:
    """One sensor message from a real logger, normalised."""

    device: str
    at: datetime
    celsius: float
    lat: float | None = None
    lon: float | None = None
    battery: float | None = None
    status: tuple[str, ...] = ()
    address: str | None = None

    @property
    def has_position(self) -> bool:
        return self.lat is not None and self.lon is not None


@dataclass(frozen=True, slots=True)
class ShipmentLeg:
    """One device's ordered telemetry, which is as close to "a shipment" as the raw data gets."""

    device: str
    points: tuple[TelemetryPoint, ...]

    @property
    def started_at(self) -> datetime:
        return self.points[0].at

    @property
    def ended_at(self) -> datetime:
        return self.points[-1].at

    @property
    def duration_minutes(self) -> float:
        return (self.ended_at - self.started_at).total_seconds() / 60.0


def _parse_timestamp(raw: object) -> datetime | None:
    """Accept both the Mongo extended-JSON form and a plain ISO string."""
    if isinstance(raw, dict):
        raw = raw.get("$date")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _normalise(record: dict) -> TelemetryPoint | None:
    """Turn one raw message into a TelemetryPoint, or None if it carries no usable reading.

    Messages without a temperature are dropped rather than defaulted. A logger that reported
    only its battery level is not evidence that the shipment was at 0 °C, and inventing a
    value here would silently corrupt every number downstream.
    """
    device = record.get("identifier")
    measurements = record.get("measurements") or {}
    temperature = measurements.get("temperature")
    at = _parse_timestamp(record.get("timestamp"))

    if not isinstance(device, str) or at is None:
        return None
    if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
        return None

    gps = measurements.get("gps") or {}
    status = record.get("status") or []

    return TelemetryPoint(
        device=device,
        at=at,
        celsius=float(temperature),
        lat=gps.get("lat") if isinstance(gps.get("lat"), (int, float)) else None,
        lon=gps.get("long") if isinstance(gps.get("long"), (int, float)) else None,
        battery=measurements.get("battery"),
        status=tuple(s for s in status if isinstance(s, str)),
        address=record.get("address") if isinstance(record.get("address"), str) else None,
    )


def iter_telemetry(path: str | Path, limit: int | None = None) -> Iterator[TelemetryPoint]:
    """Yield telemetry points from a large JSON array without loading it into memory.

    Args:
        path: the raw messages file.
        limit: stop after this many usable points. Useful for a demo that must stay inside
            three minutes.

    A truncated final object ends the iteration quietly — see the module docstring.
    """
    if limit is not None and limit <= 0:
        return

    decoder = json.JSONDecoder()
    buffer = ""
    started = False
    produced = 0

    with open(path, encoding="utf-8") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if chunk:
                buffer += chunk
            elif not buffer.strip():
                return

            if not started:
                opening = buffer.find("[")
                if opening == -1:
                    if not chunk:
                        return
                    continue
                buffer = buffer[opening + 1 :]
                started = True

            while True:
                stripped = buffer.lstrip()
                trimmed = len(buffer) - len(stripped)
                buffer = stripped
                if buffer[:1] in {",", ""}:
                    buffer = buffer[1:]
                    if not buffer and not chunk:
                        return
                    if not buffer:
                        break
                    continue
                if buffer[0] == "]":
                    return
                try:
                    record, end = decoder.raw_decode(buffer)
                except ValueError:
                    # Incomplete object: pull more bytes, unless there are none left.
                    if not chunk:
                        return
                    buffer = " " * trimmed + buffer
                    break
                buffer = buffer[end:]
                point = _normalise(record) if isinstance(record, dict) else None
                if point is not None:
                    produced += 1
                    yield point
                    if limit is not None and produced >= limit:
                        return

            if not chunk and not buffer.strip():
                return


def group_by_device(
    points: Iterator[TelemetryPoint] | list[TelemetryPoint],
    min_points: int = 2,
) -> list[ShipmentLeg]:
    """Collect points into per-device legs, ordered in time.

    Legs shorter than ``min_points`` are dropped: a single reading has no duration, so it
    cannot be weighted, and a one-point "shipment" is a logger check-in rather than a journey.
    """
    buckets: dict[str, list[TelemetryPoint]] = {}
    for point in points:
        buckets.setdefault(point.device, []).append(point)

    legs = [
        ShipmentLeg(device=device, points=tuple(sorted(items, key=lambda p: p.at)))
        for device, items in buckets.items()
        if len(items) >= min_points
    ]
    legs.sort(key=lambda leg: len(leg.points), reverse=True)
    return legs


def to_readings(leg: ShipmentLeg, max_gap_minutes: float = 240.0) -> list[Reading]:
    """Convert a leg into duration-weighted readings for the stability maths.

    Each reading is weighted by the time until the next one, which is what makes an hour at
    12 °C count for twelve times as much as five minutes at 12 °C.

    Two cases have no measured interval behind them, and both are dropped rather than assigned
    a plausible-looking default:

    * **The final reading.** Nothing after it establishes how long it held. Inventing a minute
      here would add exposure that was never observed, and on a short leg that invented minute
      can move the MKT and therefore the verdict.
    * **A duplicate or out-of-order timestamp.** A zero or negative interval is a logger fault,
      not an instant of exposure. Of a duplicated pair the *later* reading survives, since the
      interval to the next point belongs to it — which also means a hot duplicate is preserved
      rather than discarded, and a logger fault can never hide an excursion.

    Dropping them means ``len(to_readings(leg))`` can be smaller than ``len(leg.points)``. That
    is the honest shape: these are *durations*, and a reading with no measurable duration
    contributes no thermal exposure. The points themselves stay in the leg, so the record of
    what the logger reported is not altered.

    ``max_gap_minutes`` caps how much weight a single reading can absorb when the logger goes
    silent. A dropout is missing evidence, not a guarantee that the temperature held; letting
    one pre-dropout reading speak for two days would turn a gap in the record into a confident
    claim about it. Capping keeps the known-good part of the journey honest and leaves the gap
    visible in the leg's own timestamps.
    """
    if max_gap_minutes <= 0:
        raise ValueError("max_gap_minutes must be positive")

    points = leg.points
    readings: list[Reading] = []
    for index in range(len(points) - 1):
        point = points[index]
        gap = (points[index + 1].at - point.at).total_seconds() / 60.0
        if gap <= 0:
            continue
        readings.append(Reading(celsius=point.celsius, minutes=min(gap, max_gap_minutes)))
    return readings
