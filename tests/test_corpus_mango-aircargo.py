"""The mango air-cargo adapter's parsing and cutting rules, on synthetic fixtures.

The published files are a pathology-free 5-minute grid — no gaps, no duplicate instants, no
missing cells — so none of the adapter's defensive rules fire on the real download. That is
exactly why they are tested here: the leg definition has to be a property of the adapter, not
an accident of one dataset. Fixtures are hand-written in the source's own format (tab-separated,
``DD/MM/YYYY HH:MM``, CRLF), so a change to the parser that only works on the real file fails.
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
    REPO_ROOT / "corpus" / "datasets" / "mango-aircargo" / "adapt.py", "mango_adapt"
)

T0 = datetime(2023, 4, 18, 15, 2, tzinfo=adapt.SOURCE_TZ)


def _rows(start: datetime, minutes_step: float, temps: list[float], air_offset: float = 1.0):
    return "\r\n".join(
        f"{(start + timedelta(minutes=minutes_step * i)):%d/%m/%Y %H:%M}\t{t}\t{t + air_offset}"
        for i, t in enumerate(temps)
    )


def _file(temps: list[float], header: str = "Time\tT_mangoes\tT_Air", **kwargs) -> str:
    return header + "\r\n" + _rows(T0, 5.0, temps, **kwargs) + "\r\n"


class TestParseFile:
    def test_reads_both_temperature_channels_as_separate_series(self):
        series = adapt.parse_file(_file([31.6, 30.6, 29.6]))
        assert sorted(series) == ["air", "mangoes"]
        assert [c for _, c in series["mangoes"]] == [31.6, 30.6, 29.6]
        assert [c for _, c in series["air"]] == [32.6, 31.6, 30.6]

    def test_day_first_timestamps_are_read_in_the_source_zone(self):
        # 18/04 is a day-first date; read as month-first it would be 4 April and the whole
        # journey would land in the wrong week.
        (first, _), *_ = adapt.parse_file(_file([20.0, 20.0]))["mangoes"]
        assert first == datetime(2023, 4, 18, 15, 2, tzinfo=adapt.SOURCE_TZ)
        assert first.astimezone(timezone.utc) == datetime(2023, 4, 18, 8, 2, tzinfo=timezone.utc)

    def test_humidity_column_is_ignored_not_scored(self):
        text = "Time\tT_mangoes\tT_Air\tRH_Air\r\n18/04/2023 15:02\t31.6\t32.1\t52.8\r\n"
        series = adapt.parse_file(text)
        assert sorted(series) == ["air", "mangoes"]
        assert series["air"] == [(T0, 32.1)]

    def test_unknown_header_is_rejected_rather_than_guessed(self):
        with pytest.raises(ValueError, match="no temperature column"):
            adapt.parse_file("Time\tT_probe\r\n18/04/2023 15:02\t31.6\r\n")
        with pytest.raises(ValueError, match="wanted 'Time'"):
            adapt.parse_file("Date\tT_mangoes\r\n18/04/2023 15:02\t31.6\r\n")

    def test_ragged_row_is_rejected(self):
        # A row short of a column would silently shift T_Air into T_mangoes' place.
        text = (
            "Time\tT_mangoes\tT_Air\r\n"
            "18/04/2023 15:02\t31.6\t32.1\r\n"
            "18/04/2023 15:07\t31.6\r\n"
        )
        with pytest.raises(ValueError, match="line 3"):
            adapt.parse_file(text)


class TestCutLegs:
    def test_unbroken_grid_stays_one_leg(self):
        points = [(T0 + timedelta(minutes=5 * i), 20.0) for i in range(667)]
        (leg,) = adapt.cut_legs(points)
        assert len(leg) == 667

    def test_splits_on_silence_longer_than_three_hours(self):
        before = [(T0 + timedelta(minutes=5 * i), 20.0) for i in range(30)]
        after = [(before[-1][0] + timedelta(minutes=181 + 5 * i), 20.0) for i in range(30)]
        first, second = adapt.cut_legs(before + after)
        assert (len(first), len(second)) == (30, 30)
        assert first[-1][0] < second[0][0]

    def test_gap_at_exactly_the_threshold_does_not_split(self):
        before = [(T0 + timedelta(minutes=5 * i), 20.0) for i in range(30)]
        after = [(before[-1][0] + timedelta(minutes=180 + 5 * i), 20.0) for i in range(30)]
        assert len(adapt.cut_legs(before + after)) == 1

    def test_short_or_sparse_legs_are_dropped(self):
        # 6 readings over 25 min: under both the count floor and the 2 h duration floor.
        assert adapt.cut_legs([(T0 + timedelta(minutes=5 * i), 20.0) for i in range(6)]) == []
        # 10 readings but only 45 min of evidence: still dropped.
        assert adapt.cut_legs([(T0 + timedelta(minutes=5 * i), 20.0) for i in range(10)]) == []

    def test_duplicate_instant_keeps_the_later_parsed_reading(self):
        points = [(T0 + timedelta(minutes=5 * i), 20.0) for i in range(30)]
        points.insert(4, (T0 + timedelta(minutes=15), 31.5))  # duplicate of points[3]
        (leg,) = adapt.cut_legs(sorted(points, key=lambda p: p[0]))
        at_15 = [c for ts, c in leg if ts == T0 + timedelta(minutes=15)]
        assert at_15 == [31.5]
