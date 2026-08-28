"""The corpus harness: leg cutting, the CLI-subprocess runner, and the results table.

The maths under the corpus is covered by its own suites; these tests cover the harness's own
honesty rules — where journeys are cut, which duplicate survives, and that the runner reports
the CLI's verdict rather than a reinterpretation of it.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
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


adapt = _load_module(REPO_ROOT / "corpus" / "datasets" / "zenodo-ll1" / "adapt.py", "ll1_adapt")
runner = _load_module(REPO_ROOT / "corpus" / "run_corpus.py", "corpus_runner")

from coldcall.replay import TelemetryPoint  # noqa: E402

T0 = datetime(2021, 11, 9, 8, 0, tzinfo=timezone.utc)


def _point(minutes: float, celsius: float = 22.0) -> TelemetryPoint:
    return TelemetryPoint(device="AA:BB", at=T0 + timedelta(minutes=minutes), celsius=celsius)


class TestCutLegs:
    def test_splits_on_silence_longer_than_gap(self):
        # Two dense clusters separated by a 4 h silence: two journeys, not one.
        points = [_point(m) for m in range(0, 150, 10)]
        points += [_point(140 + 240 + m) for m in range(0, 150, 10)]
        legs = adapt.cut_legs(points)
        assert len(legs) == 2
        assert legs[0][-1].at < legs[1][0].at

    def test_short_or_sparse_legs_are_dropped(self):
        # 5 readings over 40 minutes: below both the count and duration floors.
        assert adapt.cut_legs([_point(m) for m in range(0, 50, 10)]) == []

    def test_duplicate_instant_keeps_the_later_parsed_reading(self):
        # Same rule as coldcall.replay.to_readings: the survivor owns the next interval,
        # so a hot duplicate parsed second can never be silently discarded.
        points = [_point(m) for m in range(0, 130, 10)]
        points.insert(4, _point(30, celsius=29.5))  # duplicate instant of points[3]
        (leg,) = adapt.cut_legs(sorted(points, key=lambda p: p.at))
        at_30 = [p for p in leg if p.at == T0 + timedelta(minutes=30)]
        assert len(at_30) == 1
        assert at_30[0].celsius == 29.5


class TestDemoInputLeg:
    def test_demo_input_is_exactly_the_demo_leg(self):
        # DEMO-0001 replays exactly 64 readings (replay/SHIPMENT.md). The corpus pin is only
        # a pin of the demo if it reconstructs that input reading-for-reading.
        if not adapt.RAW.exists():
            pytest.skip("zenodo-ll1 raw sample not fetched (corpus/datasets/zenodo-ll1/fetch.sh)")
        leg = adapt._demo_input_leg()
        assert len(leg) == adapt.DEMO_INPUT_READINGS == 64
        assert leg[0].at.isoformat() == adapt.DEMO_WINDOW_START
        assert leg[-1].at.isoformat() == adapt.DEMO_WINDOW_END
        assert all(a.at < b.at for a, b in zip(leg[:-1], leg[1:], strict=True))


class TestRunLeg:
    POLICY = {"allowed_excursion_hours": 6, "retest_at_pct": 50.0, "destroy_at_pct": 100.0}
    PROFILE = REPO_ROOT / "data" / "product_profile.json"

    def _leg_file(self, tmp_path: Path, temps: list[float]) -> Path:
        leg = [
            {"ts": (T0 + timedelta(minutes=10 * i)).isoformat(), "temp_c": t}
            for i, t in enumerate(temps)
        ]
        path = tmp_path / "leg.json"
        path.write_text(json.dumps(leg), encoding="utf-8")
        return path

    def test_in_range_leg_releases_with_crosscheck(self, tmp_path):
        row = runner._run_leg(
            self._leg_file(tmp_path, [22.0] * 20), self.PROFILE, self.POLICY, "t-release"
        )
        assert row["status"] == "ok"
        assert row["verdict"] == "release"
        assert row["crosscheck_agrees"] is True

    def test_bad_input_is_an_error_row_not_a_crash(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text('{"not": "an array of readings"}', encoding="utf-8")
        row = runner._run_leg(bad, self.PROFILE, self.POLICY, "t-bad")
        assert row["status"] == "error"
        assert row["exit_code"] == 2
        assert row["detail"]  # stderr preserved: that is the actionable part

    def test_timeout_is_an_error_row_not_a_crash(self, tmp_path, monkeypatch):
        def _hang(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        monkeypatch.setattr(runner.subprocess, "run", _hang)
        row = runner._run_leg(
            self._leg_file(tmp_path, [22.0] * 20), self.PROFILE, self.POLICY, "t-hang"
        )
        assert row["status"] == "error"
        assert row["exit_code"] is None
        assert "timed out" in row["detail"]


class TestRunDataset:
    def _dataset(self, tmp_path: Path, expected_legs: dict) -> Path:
        data_dir = tmp_path / "data"
        (data_dir / "legs").mkdir(parents=True)
        leg = [
            {"ts": (T0 + timedelta(minutes=10 * i)).isoformat(), "temp_c": 22.0}
            for i in range(20)
        ]
        (data_dir / "legs" / "present.json").write_text(json.dumps(leg), encoding="utf-8")
        (data_dir / "manifest.json").write_text(
            json.dumps(
                {"legs": [{"id": "present", "file": "legs/present.json", "n": len(leg)}]}
            ),
            encoding="utf-8",
        )
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "config.json").write_text(
            json.dumps(
                {
                    "slug": "t",
                    "data_dir": str(data_dir),
                    "profile": str(REPO_ROOT / "data" / "product_profile.json"),
                    "policy": {"allowed_excursion_hours": 6},
                }
            ),
            encoding="utf-8",
        )
        (dataset_dir / "expected.json").write_text(
            json.dumps({"legs": expected_legs}), encoding="utf-8"
        )
        return dataset_dir

    def test_pinned_leg_dropped_by_the_adapter_is_a_fail_row(self, tmp_path):
        # A reviewed pin whose leg vanished from the manifest must fail the run, not
        # silently shrink the corpus.
        expected = {
            "present": {"verdict": "release"},
            "ghost": {"verdict": "destroy"},
        }
        outcome = runner.run_dataset(self._dataset(tmp_path, expected))
        by_id = {row["leg_id"]: row for row in outcome["legs"]}
        assert by_id["present"]["check"] == "PASS"
        assert by_id["ghost"]["check"] == "FAIL"
        assert by_id["ghost"]["status"] == "error"
        assert by_id["ghost"]["pinned"] == "destroy"
        assert "absent from manifest" in by_id["ghost"]["detail"]


class TestMarkdown:
    def test_error_rows_render_without_verdict_columns(self):
        results = [
            {
                "slug": "x",
                "title": "X",
                "legs": [
                    {"leg_id": "a", "status": "error", "detail": "boom", "check": "FAIL"},
                    {
                        "leg_id": "b",
                        "status": "ok",
                        "verdict": "release",
                        "mkt_c": 22.0,
                        "budget_consumed_pct": 0.0,
                        "excursion_minutes": 0.0,
                        "check": "PASS",
                        "n_readings": 5,
                    },
                ],
            }
        ]
        text = runner._markdown(results, "2026-08-25T00:00:00+00:00")
        assert "error: boom" in text
        assert "| `b` | 5 | `release` |" in text
        assert "1 FAIL, 1 PASS" in text
