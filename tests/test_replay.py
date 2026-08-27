"""Tests for the streaming telemetry replay.

These build their own fixtures rather than depending on the real 400 MB dataset. The point
of the parser is that it handles the *shape* of that file — a pretty-printed array, Mongo
extended-JSON timestamps, missing measurements, a truncated tail — and every one of those
shapes can be written into a temporary file in a few lines. A test suite that needed a
400 MB download to run is a test suite nobody runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from coldcall.mkt import mean_kinetic_temperature
from coldcall.replay import (
    ShipmentLeg,
    TelemetryPoint,
    group_by_device,
    iter_telemetry,
    to_readings,
)

BASE = datetime(2021, 11, 8, 17, 48, 4, tzinfo=timezone.utc)


def record(device: str, minutes: int, celsius: float | None, **extra: object) -> dict:
    """One raw message in the source file's actual shape."""
    measurements: dict[str, object] = {"battery": 3.05}
    if celsius is not None:
        measurements["temperature"] = celsius
    measurements.update(extra)
    return {
        "_id": {"$oid": "61a85c97931b91f5b5844226"},
        "identifier": device,
        "timestamp": {"$date": (BASE + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "status": ["normal"],
        "measurements": measurements,
    }


def write_array(tmp_path, records: list[dict], truncate_bytes: int = 0):
    """Write records as a pretty-printed JSON array, optionally chopping the tail off."""
    path = tmp_path / "telemetry.json"
    text = json.dumps(records, indent=2)
    if truncate_bytes:
        text = text[:-truncate_bytes]
    path.write_text(text, encoding="utf-8")
    return path


class TestIterTelemetry:
    def test_reads_a_pretty_printed_array(self, tmp_path) -> None:
        path = write_array(tmp_path, [record("A", i, 5.0 + i) for i in range(5)])
        points = list(iter_telemetry(path))
        assert len(points) == 5
        assert [p.celsius for p in points] == [5.0, 6.0, 7.0, 8.0, 9.0]

    def test_survives_a_truncated_tail(self, tmp_path) -> None:
        """Range-requesting a few MB of a huge remote file always ends mid-object."""
        path = write_array(tmp_path, [record("A", i, 5.0) for i in range(20)], truncate_bytes=90)
        points = list(iter_telemetry(path))
        assert 15 <= len(points) < 20  # everything complete, nothing invented

    def test_drops_messages_with_no_temperature_rather_than_defaulting(self, tmp_path) -> None:
        """A battery-only check-in is not evidence the shipment was at 0 °C."""
        path = write_array(
            tmp_path, [record("A", 0, 5.0), record("A", 1, None), record("A", 2, 6.0)]
        )
        points = list(iter_telemetry(path))
        assert [p.celsius for p in points] == [5.0, 6.0]

    def test_parses_gps_when_present_and_tolerates_its_absence(self, tmp_path) -> None:
        path = write_array(
            tmp_path,
            [
                record("A", 0, 5.0, gps={"lat": 39.4565, "long": -0.3465}),
                record("A", 1, 6.0),
            ],
        )
        located, unlocated = list(iter_telemetry(path))
        assert located.has_position and located.lat == pytest.approx(39.4565)
        assert not unlocated.has_position

    def test_limit_stops_early(self, tmp_path) -> None:
        path = write_array(tmp_path, [record("A", i, 5.0) for i in range(100)])
        assert len(list(iter_telemetry(path, limit=7))) == 7

    def test_empty_array_yields_nothing(self, tmp_path) -> None:
        assert list(iter_telemetry(write_array(tmp_path, []))) == []

    def test_malformed_timestamp_is_dropped_not_guessed(self, tmp_path) -> None:
        bad = record("A", 0, 5.0)
        bad["timestamp"] = {"$date": "not-a-date"}
        path = write_array(tmp_path, [bad, record("A", 1, 6.0)])
        assert [p.celsius for p in iter_telemetry(path)] == [6.0]


class TestGrouping:
    def test_splits_by_device_and_orders_by_time(self, tmp_path) -> None:
        path = write_array(
            tmp_path,
            [record("B", 5, 9.0), record("A", 2, 6.0), record("A", 0, 5.0), record("B", 0, 8.0)],
        )
        legs = {leg.device: leg for leg in group_by_device(iter_telemetry(path))}
        assert set(legs) == {"A", "B"}
        assert [p.celsius for p in legs["A"].points] == [5.0, 6.0]

    def test_single_point_devices_are_dropped_as_check_ins_not_journeys(self, tmp_path) -> None:
        path = write_array(
            tmp_path, [record("A", 0, 5.0), record("B", 0, 5.0), record("B", 3, 6.0)]
        )
        assert [leg.device for leg in group_by_device(iter_telemetry(path))] == ["B"]

    def test_leg_reports_its_own_span(self, tmp_path) -> None:
        path = write_array(tmp_path, [record("A", 0, 5.0), record("A", 90, 6.0)])
        leg = group_by_device(iter_telemetry(path))[0]
        assert leg.duration_minutes == pytest.approx(90.0)


class TestToReadings:
    def test_weights_each_reading_by_the_time_until_the_next(self, tmp_path) -> None:
        leg = ShipmentLeg(
            device="A",
            points=(
                TelemetryPoint("A", BASE, 5.0),
                TelemetryPoint("A", BASE + timedelta(minutes=120), 9.0),
                TelemetryPoint("A", BASE + timedelta(minutes=130), 5.0),
            ),
        )
        readings = to_readings(leg)
        assert readings[0].minutes == pytest.approx(120.0)
        assert readings[1].minutes == pytest.approx(10.0)

    def test_a_logger_dropout_cannot_absorb_unlimited_weight(self, tmp_path) -> None:
        """A three-day silence is missing evidence, not three days of proven 5 °C."""
        leg = ShipmentLeg(
            device="A",
            points=(
                TelemetryPoint("A", BASE, 5.0),
                TelemetryPoint("A", BASE + timedelta(days=3), 5.0),
            ),
        )
        readings = to_readings(leg, max_gap_minutes=240.0)
        assert readings[0].minutes == pytest.approx(240.0)

    def test_feeds_the_stability_maths_end_to_end(self, tmp_path) -> None:
        path = write_array(
            tmp_path, [record("A", i * 30, 5.0 if i % 2 else 6.0) for i in range(10)]
        )
        leg = group_by_device(iter_telemetry(path))[0]
        mkt = mean_kinetic_temperature(to_readings(leg))
        assert 5.0 <= mkt <= 6.5

    def test_non_positive_gap_cap_is_rejected(self) -> None:
        leg = ShipmentLeg(device="A", points=(TelemetryPoint("A", BASE, 5.0),))
        with pytest.raises(ValueError, match="must be positive"):
            to_readings(leg, max_gap_minutes=0.0)
