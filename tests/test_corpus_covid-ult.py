"""The covid-ult adapter: header parsing, °F conversion, DST-aware time, channel selection.

Synthetic fixtures only — miniature CSVs in the exact multi-row-header shapes figshare
14888121 publishes. The rules under test are the ones that would silently change a verdict if
they broke: the unit conversion, the timezone assumption at the DST boundary, which channels
count as product temperature, and where a leg is cut.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


adapt = _load_module(
    REPO_ROOT / "corpus" / "datasets" / "covid-ult" / "adapt.py", "covid_ult_adapt"
)

T0 = datetime(2020, 12, 16, 16, 25, 54, tzinfo=timezone.utc)


def _point(minutes: float, celsius: float = -78.5):
    return (T0 + timedelta(minutes=minutes), celsius)


def _write_test1(path: Path, rows: list[str], labels: str = "b1", units: str = "F") -> Path:
    """A Test-1-shaped CSV: name row, label row, unit row, then `date,time,elapsed,...`."""
    header = [
        "date,time,Time Elapsed,Pod1,Ambient\n",
        f",,,{labels},Toutside\n",
        f",,,{units},F\n",
    ]
    path.write_text("".join(header) + "".join(rows), encoding="utf-8")
    return path


def _write_test2(path: Path, rows: list[str], units: str = "Deg F") -> Path:
    """A Test-2-shaped CSV: name row, unit row, then `TIMESTAMP,...`."""
    header = [
        "TIMESTAMP,TC_A1,TC_TB1,TC_TB21,O2\n",
        f"TS,Deg F,{units},Deg F,\n",
    ]
    path.write_text("".join(header) + "".join(rows), encoding="utf-8")
    return path


class TestUnits:
    def test_fahrenheit_to_celsius(self):
        assert adapt.f_to_c(32.0) == 0.0
        assert adapt.f_to_c(-76.0) == -60.0  # the label's upper ULT bound
        assert adapt.f_to_c(-130.0) == -90.0  # the label's lower ULT bound
        assert adapt.f_to_c(-109.3) == -78.5  # dry-ice sublimation point

    def test_a_unit_header_that_is_not_fahrenheit_is_refused(self, tmp_path):
        # Silently applying the F->C formula to a re-published Celsius file would shift every
        # reading by ~40 C and quietly change every verdict.
        path = _write_test1(
            tmp_path / "t1.csv", ["16-Dec-20,11:25:54,0:00:00,-113.4,71.7\n"], units="C"
        )
        with pytest.raises(ValueError, match="not F"):
            adapt.read_test1(path)


class TestTimezone:
    def test_naive_local_becomes_utc_at_eastern_standard_offset(self):
        assert adapt.to_utc(datetime(2020, 12, 16, 11, 25, 54)) == datetime(
            2020, 12, 16, 16, 25, 54, tzinfo=timezone.utc
        )

    def test_spring_forward_boundary_stays_one_minute_apart(self):
        # Test 2's record jumps 02:00 -> 03:01 local on 2021-03-14: the logger observed DST.
        # In UTC that must be a 1-minute step, not a 61-minute phantom gap.
        before = adapt.to_utc(datetime(2021, 3, 14, 2, 0))
        after = adapt.to_utc(datetime(2021, 3, 14, 3, 1))
        assert (after - before).total_seconds() == 60

    def test_after_the_transition_the_offset_is_daylight_time(self):
        assert adapt.to_utc(datetime(2021, 3, 15, 12, 0)) == datetime(
            2021, 3, 15, 16, 0, tzinfo=timezone.utc
        )


class TestParsing:
    def test_test1_keys_channels_by_their_label_row_and_ignores_ambient(self, tmp_path):
        path = _write_test1(
            tmp_path / "t1.csv",
            [
                "16-Dec-20,11:25:54,0:00:00,-113.4706,71.7494\n",
                "16-Dec-20,11:26:12,0:00:18,-113.494,71.735\n",
            ],
        )
        stamps, series = adapt.read_test1(path)
        assert list(series) == ["b1"]  # Toutside is not a package
        assert stamps[0] == datetime(2020, 12, 16, 16, 25, 54, tzinfo=timezone.utc)
        assert series["b1"] == [-113.4706, -113.494]

    def test_test2_takes_only_payload_box_channels(self, tmp_path):
        path = _write_test2(
            tmp_path / "t2.csv",
            [
                "3/9/2021 6:37,-23.34,-91.1,62.79,14.65\n",
                "3/9/2021 6:38,-23.06,-91.2,62.78,14.61\n",
            ],
        )
        stamps, series = adapt.read_test2(path)
        assert sorted(series) == ["TC_TB1", "TC_TB21"]  # container air and O2 dropped here
        assert stamps[1] == datetime(2021, 3, 9, 11, 38, tzinfo=timezone.utc)


class TestChannelFilter:
    def _stamps(self, n: int) -> list[datetime]:
        return [datetime(2021, 3, 9, 6, 37) + timedelta(minutes=i) for i in range(n)]

    def test_room_temperature_channel_is_not_a_package(self):
        stamps = [t.replace(tzinfo=timezone.utc) for t in self._stamps(200)]
        legs = adapt.build_legs(stamps, {"TC_TB21": [63.0] * 200}, "test2")
        assert legs == []

    def test_a_cold_channel_survives_and_is_named_after_its_box(self):
        stamps = [t.replace(tzinfo=timezone.utc) for t in self._stamps(200)]
        legs = adapt.build_legs(stamps, {"TC_TB7": [-109.3] * 200}, "test2")
        assert [leg_id for leg_id, _ in legs] == ["test2-B7"]
        assert legs[0][1][0][1] == -78.5  # converted to Celsius

    def test_a_channel_that_swings_around_ambient_is_dropped_whatever_its_extremes(self):
        # TC_TB2's real shape: a detached thermocouple whose median sits near room
        # temperature even though it touches package-like values.
        stamps = [t.replace(tzinfo=timezone.utc) for t in self._stamps(200)]
        values = [-122.5 if i % 10 == 0 else 70.0 for i in range(200)]
        assert adapt.build_legs(stamps, {"TC_TB2": values}, "test2") == []


class TestCutting:
    def test_a_continuous_record_is_one_leg(self):
        # The real files' largest gap is 11 minutes: no cut, one leg per sensor.
        points = [_point(m) for m in range(0, 200, 10)]
        assert len(adapt.cut_legs(points)) == 1

    def test_silence_longer_than_the_threshold_cuts(self):
        points = [_point(m) for m in range(0, 150, 10)]
        points += [_point(140 + 240 + m) for m in range(0, 150, 10)]
        legs = adapt.cut_legs(points)
        assert len(legs) == 2
        assert legs[0][-1][0] < legs[1][0][0]

    def test_short_or_sparse_legs_are_dropped(self):
        assert adapt.cut_legs([_point(m) for m in range(0, 50, 10)]) == []

    def test_second_and_later_legs_get_a_suffix(self):
        stamps = [T0 + timedelta(minutes=m) for m in list(range(0, 150, 10))]
        stamps += [T0 + timedelta(minutes=380 + m) for m in range(0, 150, 10)]
        legs = adapt.build_legs(stamps, {"b4": [-113.0] * len(stamps)}, "test1")
        assert [leg_id for leg_id, _ in legs] == ["test1-b4", "test1-b4-2"]

    def test_duplicate_instant_keeps_the_later_parsed_reading(self):
        points = [_point(m) for m in range(0, 130, 10)]
        points.insert(4, _point(30, celsius=-40.0))  # duplicate instant of points[3]
        deduped = adapt.dedupe(points)
        at_30 = [p for p in deduped if p[0] == T0 + timedelta(minutes=30)]
        assert len(at_30) == 1
        assert at_30[0][1] == -40.0

    def test_out_of_order_input_is_sorted_upstream(self):
        # The CLI rejects a non-monotonic series rather than guessing, so the adapter must
        # never hand it one.
        points = [_point(m) for m in (0, 30, 10, 20)]
        assert [p[0] for p in adapt.dedupe(points)] == [
            T0 + timedelta(minutes=m) for m in (0, 10, 20, 30)
        ]
