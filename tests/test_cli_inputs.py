"""Input-handling contracts for the sandbox entry point.

Every case here is a way bad telemetry could have produced a *plausible* verdict instead of
an error. That is the dangerous failure for this project: a wrong number that looks right is
worse than a crash, because a crash gets investigated.
"""

from __future__ import annotations

import json

import pytest

from coldcall.cli import _durations_from_timestamps, _parse_iso, load_readings, main


class TestDurationDerivation:
    def test_no_timestamps_anywhere_falls_back_to_the_flat_interval(self):
        """A legitimate shape: bare numbers, or records carrying only a duration."""
        assert _durations_from_timestamps([None, None, None], 5.0) == [5.0, 5.0, 5.0]

    def test_a_single_unparseable_timestamp_is_refused(self):
        """Partial timestamps are corruption, not a shape.

        The old behaviour fell back for the WHOLE series, turning hours of measured excursion
        into minutes and releasing a shipment that should not have been.
        """
        stamps = [_parse_iso("2026-01-01T00:00:00Z"), None, _parse_iso("2026-01-01T02:00:00Z")]
        with pytest.raises(ValueError, match="missing or unparseable"):
            _durations_from_timestamps(stamps, 5.0)

    def test_a_dropout_is_capped_rather_than_counted(self):
        """Four hours of silence is missing evidence, not four hours at the last reading."""
        stamps = [
            _parse_iso("2026-01-01T00:00:00Z"),
            _parse_iso("2026-01-05T00:00:00Z"),  # four days later
            _parse_iso("2026-01-05T00:10:00Z"),
        ]
        durations = _durations_from_timestamps(stamps, 5.0)
        assert durations[0] == 240.0

    def test_the_tail_gap_is_a_true_median_on_an_even_count(self):
        """`sorted[n//2]` picks the upper middle, which over-credits the final reading.

        Gaps here are 2, 8, 30, 10 minutes. Sorted: 2, 8, 10, 30. The median is 9; the
        upper-middle element is 10. The last reading has no following sample, so whichever
        of those it inherits feeds straight into the excursion percentage.
        """
        stamps = [_parse_iso(f"2026-01-01T00:{m:02d}:00Z") for m in (0, 2, 10, 40, 50)]
        durations = _durations_from_timestamps(stamps, 1.0)
        assert durations[:-1] == [2.0, 8.0, 30.0, 10.0]
        assert durations[-1] == pytest.approx(9.0)


class TestProductProfile:
    def test_valid_json_that_is_not_an_object_is_rejected_cleanly(self, tmp_path, capsys):
        """A top-level list parses fine and then explodes on the first .get()."""
        telemetry = tmp_path / "leg.json"
        telemetry.write_text(json.dumps([{"ts": "2026-01-01T00:00:00Z", "temp_c": 22.0}]))
        product = tmp_path / "product.json"
        product.write_text(json.dumps(["not", "an", "object"]))
        code = main([
            "--telemetry", str(telemetry),
            "--product", str(product),
            "--allowed-excursion-hours", "6",
        ])
        assert code == 2
        assert "must be a JSON object" in capsys.readouterr().err


class TestLoadReadings:
    def test_a_reading_with_no_temperature_names_the_fields_it_looked_for(self):
        with pytest.raises(ValueError, match="temp_c"):
            load_readings([{"ts": "2026-01-01T00:00:00Z"}])

    def test_an_empty_document_is_refused(self):
        with pytest.raises(ValueError, match="non-empty"):
            load_readings([])


class TestExplicitDurationsWin:
    """A reading that states its own duration does not need a timestamp to be believed."""

    def test_explicit_durations_survive_a_missing_timestamp(self):
        """Regression: tightening the timestamp rules rejected a supported shape.

        When every reading carries an authoritative `minutes`, the timestamps are incidental
        metadata that nothing reads — so a missing or malformed one must not invalidate the
        series. The strict rule still applies when durations actually come from timestamps.
        """
        readings = load_readings([
            {"ts": "2026-01-01T00:00:00Z", "temp_c": 22.0, "minutes": 30.0},
            {"temp_c": 27.0, "minutes": 45.0},                      # no timestamp at all
            {"ts": "not-a-timestamp", "temp_c": 23.0, "minutes": 15.0},  # unparseable
        ])
        assert [r.minutes for r in readings] == [30.0, 45.0, 15.0]

    def test_a_partial_timestamp_still_fails_when_durations_are_derived(self):
        """The strict rule survives for the case it was written for."""
        with pytest.raises(ValueError, match="missing or unparseable"):
            load_readings([
                {"ts": "2026-01-01T00:00:00Z", "temp_c": 22.0},
                {"temp_c": 27.0},
            ])

    def test_a_mix_derives_only_the_readings_that_need_it(self):
        readings = load_readings([
            {"ts": "2026-01-01T00:00:00Z", "temp_c": 22.0, "minutes": 5.0},
            {"ts": "2026-01-01T00:20:00Z", "temp_c": 27.0},
            {"ts": "2026-01-01T00:30:00Z", "temp_c": 23.0},
        ])
        assert readings[0].minutes == 5.0     # explicit wins
        assert readings[1].minutes == 10.0    # derived from the gap
