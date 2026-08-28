"""The strawberry adapter's parsing and cutting rules, on synthetic fixtures.

The corpus harness itself is covered by ``tests/test_corpus.py``; what is adapter-specific here
is the wide-table explode (nine probe columns -> nine independent series), the timezone
assumption the source forces on us, and blank cells meaning "missing", never zero.
"""

from __future__ import annotations

import importlib.util
import json
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
    REPO_ROOT / "corpus" / "datasets" / "strawberry" / "adapt.py", "strawberry_adapt"
)

T0 = datetime(2019, 3, 12, 12, 30, tzinfo=timezone.utc)
HEADER = "ts," + ",".join(adapt.SENSORS)


def _reading(minutes: float, celsius: float = 2.0) -> adapt.Reading:
    return adapt.Reading(at=T0 + timedelta(minutes=minutes), celsius=celsius)


def _write_csv(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "S1.csv"
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return path


class TestParseTimestamp:
    def test_naive_iso_is_labelled_utc_without_shifting(self):
        # The source states no timezone anywhere, so the wall-clock is kept and simply
        # labelled — shifting it would invent an offset (see DATASET.md, "Timezone").
        parsed = adapt.parse_timestamp("2019-03-12T12:30:00")
        assert parsed == datetime(2019, 3, 12, 12, 30, tzinfo=timezone.utc)
        assert parsed.utcoffset() == timedelta(0)

    def test_accepts_the_other_mirrors_slash_format(self):
        assert adapt.parse_timestamp("2019/3/12 12:30") == T0

    def test_an_explicit_offset_is_converted_not_relabelled(self):
        assert adapt.parse_timestamp("2019-03-12T08:30:00-04:00") == T0

    def test_unparseable_timestamp_raises(self):
        with pytest.raises(ValueError):
            adapt.parse_timestamp("12th of March")


class TestReadShipment:
    def test_each_probe_column_becomes_its_own_series(self, tmp_path):
        rows = [
            "2019-03-12T12:30:00,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0",
            "2019-03-12T12:40:00,1.1,2.1,3.1,4.1,5.1,6.1,7.1,8.1,9.1",
        ]
        series = adapt.read_shipment(_write_csv(tmp_path, rows))
        assert set(series) == set(adapt.SENSORS)
        # Nine probes, kept apart: no averaging, no trailer-mean channel.
        assert [r.celsius for r in series["Front_Top"]] == [1.0, 1.1]
        assert [r.celsius for r in series["Rear_Bottom"]] == [9.0, 9.1]

    def test_blank_cells_are_missing_samples_not_zeros(self, tmp_path):
        rows = [
            "2019-03-12T12:30:00,1.0,,3.0,4.0,5.0,6.0,7.0,8.0,9.0",
            "2019-03-12T12:40:00,1.1,2.1,3.1,4.1,5.1,6.1,7.1,8.1,9.1",
        ]
        series = adapt.read_shipment(_write_csv(tmp_path, rows))
        assert [r.celsius for r in series["Front_Middle"]] == [2.1]
        assert all(r.celsius != 0.0 for r in series["Front_Middle"])

    def test_a_wholly_empty_probe_column_is_dropped(self, tmp_path):
        # S1's Front_Bottom and Middle_Bottom are like this in the real source.
        rows = [
            "2019-03-12T12:30:00,1.0,2.0,,4.0,5.0,6.0,7.0,8.0,9.0",
            "2019-03-12T12:40:00,1.1,2.1,,4.1,5.1,6.1,7.1,8.1,9.1",
        ]
        series = adapt.read_shipment(_write_csv(tmp_path, rows))
        assert "Front_Bottom" not in series
        assert len(series) == len(adapt.SENSORS) - 1

    def test_negative_and_subzero_values_survive(self, tmp_path):
        # Freezing matters for this product; a -0.4 must not be clamped or dropped.
        rows = [
            "2019-03-12T12:30:00,-0.4,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0",
            "2019-03-12T12:40:00,-6.5,2.1,3.1,4.1,5.1,6.1,7.1,8.1,9.1",
        ]
        series = adapt.read_shipment(_write_csv(tmp_path, rows))
        assert [r.celsius for r in series["Front_Top"]] == [-0.4, -6.5]


class TestCutLegs:
    def test_a_contiguous_series_is_one_leg(self):
        (leg,) = adapt.cut_legs([_reading(m) for m in range(0, 200, 10)])
        assert len(leg) == 20

    def test_splits_on_silence_longer_than_three_hours(self):
        points = [_reading(m) for m in range(0, 200, 10)]
        points += [_reading(190 + 240 + m) for m in range(0, 200, 10)]
        legs = adapt.cut_legs(points)
        assert len(legs) == 2
        assert legs[0][-1].at < legs[1][0].at

    def test_a_gap_exactly_at_the_threshold_does_not_split(self):
        points = [_reading(m) for m in range(0, 200, 10)]
        points += [_reading(190 + adapt.GAP_MINUTES + m) for m in range(0, 200, 10)]
        assert len(adapt.cut_legs(points)) == 1

    def test_out_of_order_input_is_sorted_before_cutting(self):
        # The CLI rejects out-of-order telemetry rather than guessing, so the ordering has to
        # be resolved here.
        points = list(reversed([_reading(m) for m in range(0, 200, 10)]))
        (leg,) = adapt.cut_legs(points)
        assert [p.at for p in leg] == sorted(p.at for p in leg)

    def test_duplicate_instant_keeps_the_later_parsed_reading(self):
        points = [_reading(m) for m in range(0, 200, 10)]
        points.insert(4, _reading(30, celsius=29.5))  # duplicate of points[3]'s instant
        (leg,) = adapt.cut_legs(points)
        at_30 = [p for p in leg if p.at == T0 + timedelta(minutes=30)]
        assert len(at_30) == 1
        assert at_30[0].celsius == 29.5

    def test_too_few_readings_is_dropped(self):
        # 7 readings over 6 h: long enough, but under the count floor.
        assert adapt.cut_legs([_reading(m * 60) for m in range(7)]) == []

    def test_too_short_a_span_is_dropped(self):
        # 12 readings over 110 min: plenty of points, under the 2 h floor.
        assert adapt.cut_legs([_reading(m * 10) for m in range(12)]) == []

    def test_a_short_tail_after_a_gap_is_dropped_but_the_good_leg_survives(self):
        points = [_reading(m) for m in range(0, 200, 10)]
        points += [_reading(600 + m) for m in range(0, 40, 10)]
        (leg,) = adapt.cut_legs(points)
        assert leg[-1].at == T0 + timedelta(minutes=190)


class TestEndToEnd:
    def test_main_writes_canonical_legs_and_a_manifest(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(adapt, "DATA_DIR", tmp_path)
        rows = [
            f"2019-03-12T{12 + (m // 60):02d}:{m % 60:02d}:00,"
            + ",".join(["2.0"] * (len(adapt.SENSORS) - 1) + [""])
            for m in range(0, 190, 10)
        ]
        for shipment in adapt.SHIPMENTS:
            (tmp_path / f"{shipment}.csv").write_text(
                "\n".join([HEADER, *rows]) + "\n", encoding="utf-8"
            )

        assert adapt.main() == 0
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["dataset"] == "strawberry"
        assert "arXiv:2103.12895" in manifest["source"]
        # 6 shipments x 8 reporting probes; the ninth column is blank throughout.
        assert len(manifest["legs"]) == 6 * (len(adapt.SENSORS) - 1)

        entry = manifest["legs"][0]
        assert entry["id"] == "S1-Front_Top"
        assert entry == {**entry, "n": 19, "min_c": 2.0, "max_c": 2.0}
        leg = json.loads((tmp_path / entry["file"]).read_text(encoding="utf-8"))
        assert leg[0] == {"ts": "2019-03-12T12:00:00+00:00", "temp_c": 2.0}
        assert all(p["ts"].endswith("+00:00") for p in leg)

    def test_main_refuses_when_fetch_has_not_run(self, tmp_path, monkeypatch):
        monkeypatch.setattr(adapt, "DATA_DIR", tmp_path)
        assert adapt.main() == 2
