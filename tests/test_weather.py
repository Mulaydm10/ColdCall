"""Route-context attribution: did the weather explain the excursion, or didn't it?

No network. `fetch_ambient` is exercised against the live archive by `scripts/verify_apis.sh`,
which is where a network dependency belongs; a unit test that reaches the internet fails for
reasons that have nothing to do with the code under test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from coldcall.weather import (
    CONTAINMENT,
    ENVIRONMENTAL,
    UNDETERMINED,
    AmbientSeries,
    LocationEvidence,
    attribute_excursion,
    fetch_ambient,
)

LABEL_UPPER = 25.0


def ambient(start: datetime, temps: list[float]) -> AmbientSeries:
    """An hourly ambient series beginning at `start`."""
    return AmbientSeries(
        latitude=39.4565,
        longitude=-0.3465,
        times=tuple(start + timedelta(hours=i) for i in range(len(temps))),
        celsius=tuple(temps),
        source="synthetic fixture",
    )


def at(start: datetime, minutes: int) -> datetime:
    return start + timedelta(minutes=minutes)


START = datetime(2021, 11, 9, 12, 0, tzinfo=timezone.utc)


class TestAmbientLookup:
    def test_matches_the_nearest_hour_not_the_preceding_one(self):
        """A 14:58 reading is better represented by 15:00 than by 14:00.

        Rounding down would systematically lag the ambient curve behind the telemetry, which
        biases every gap in the same direction — exactly the kind of quiet error an
        attribution should not rest on.
        """
        series = ambient(START, [10.0, 20.0, 30.0])
        assert series.at(START + timedelta(minutes=58)) == 20.0
        assert series.at(START + timedelta(minutes=2)) == 10.0

    def test_returns_none_well_outside_the_series(self):
        series = ambient(START, [10.0, 11.0])
        assert series.at(START - timedelta(hours=5)) is None
        assert series.at(START + timedelta(hours=9)) is None

    def test_tolerates_a_naive_timestamp(self):
        """Real telemetry mixes naive and aware; a lookup must not raise on either."""
        series = ambient(START, [12.0, 13.0])
        assert series.at(datetime(2021, 11, 9, 12, 10)) == 12.0

    def test_a_gap_in_the_archive_is_not_a_temperature(self):
        series = ambient(START, [float("nan"), 15.0])
        assert series.at(START) is None

    def test_an_empty_series_never_pretends_to_know(self):
        series = AmbientSeries(0.0, 0.0, (), (), "empty")
        assert series.at(START) is None


class TestAttribution:
    def test_a_load_far_above_outside_air_is_a_containment_failure(self):
        """The real demo leg's shape: 27 °C inside while it was ~15 °C outside.

        No routing decision prevents that — the finding has to point at packaging or the
        reefer, and a deviation record that said only "reached 27 °C" would have sent the
        investigation to the wrong place.
        """
        series = ambient(START, [15.0, 15.0, 16.0, 15.0])
        readings = [(at(START, m), 27.0) for m in (10, 70, 130, 190)]
        result = attribute_excursion(readings, series, LABEL_UPPER)
        assert result.attribution == CONTAINMENT
        assert result.median_gap_c == pytest.approx(12.0, abs=0.5)
        assert result.coverage == 1.0
        assert any("packaging" in n for n in result.notes)

    def test_a_load_tracking_a_hot_day_is_environmental(self):
        series = ambient(START, [27.0, 28.0, 28.0, 27.0])
        readings = [(at(START, m), 29.0) for m in (10, 70, 130, 190)]
        result = attribute_excursion(readings, series, LABEL_UPPER)
        assert result.attribution == ENVIRONMENTAL
        assert any("lane" in n for n in result.notes)

    def test_only_out_of_band_readings_are_attributed(self):
        """In-band time would drag the median toward the ambient baseline and mask the gap."""
        series = ambient(START, [15.0, 15.0, 15.0, 15.0])
        readings = [
            (at(START, 10), 22.0),   # in band — must be ignored
            (at(START, 70), 22.0),   # in band
            (at(START, 130), 27.0),  # the excursion
            (at(START, 190), 27.0),
        ]
        result = attribute_excursion(readings, series, LABEL_UPPER)
        assert result.total_excursion_readings == 2
        assert result.median_gap_c == pytest.approx(12.0)

    def test_no_excursion_means_nothing_to_explain(self):
        series = ambient(START, [15.0, 15.0])
        readings = [(at(START, 10), 22.0), (at(START, 70), 23.0)]
        result = attribute_excursion(readings, series, LABEL_UPPER)
        assert result.attribution == UNDETERMINED
        assert result.total_excursion_readings == 0
        assert any("nothing to explain" in n for n in result.notes)

    def test_thin_coverage_refuses_to_attribute(self):
        """An investigation that cannot tell is a legitimate outcome.

        Forcing a cause out of two matched readings is how a bad CAPA gets written, so below
        half coverage this returns undetermined and says why rather than guessing.
        """
        series = ambient(START, [15.0])  # one hour only
        readings = [(at(START, m), 27.0) for m in (10, 200, 260, 320, 380)]
        result = attribute_excursion(readings, series, LABEL_UPPER)
        assert result.attribution == UNDETERMINED
        assert result.median_gap_c is None
        assert any("too few" in n for n in result.notes)

    def test_the_threshold_is_configurable_and_reported(self):
        """It is our policy, so it travels with the verdict rather than hiding in the code."""
        series = ambient(START, [15.0, 15.0])
        readings = [(at(START, m), 27.0) for m in (10, 70)]
        strict = attribute_excursion(readings, series, LABEL_UPPER, threshold_c=20.0)
        assert strict.attribution == ENVIRONMENTAL  # 12 °C gap no longer clears 20
        assert strict.to_dict()["containment_gap_threshold_c"] == 20.0
        assert "not a regulatory value" in strict.to_dict()["threshold_note"]


class TestFetchValidation:
    """Argument checking, which needs no network."""

    @pytest.mark.parametrize(
        "lat,lon",
        [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)],
    )
    def test_impossible_coordinates_are_refused(self, lat, lon):
        with pytest.raises(ValueError, match="impossible coordinate"):
            fetch_ambient(lat, lon, START, START + timedelta(hours=1))

    def test_an_inverted_window_is_refused(self):
        with pytest.raises(ValueError, match="ends before it starts"):
            fetch_ambient(39.0, -0.3, START, START - timedelta(hours=1))


class TestLocationEvidence:
    """A weather lookup is only as good as the coordinate, and a coordinate has a timestamp.

    Treating a last-known position as an established location during a later excursion is the
    same class of overclaim as calling a reanalysis a measurement. The number may still be
    right; the record has to say what it rests on.
    """

    def stale(self) -> LocationEvidence:
        """The demo leg's real situation: 15 fixes ending 12.3 h before the window."""
        return LocationEvidence(
            latitude=39.4565,
            longitude=-0.3465,
            fix_count=15,
            earliest_fix="2021-11-08T17:48:04Z",
            latest_fix="2021-11-08T20:06:41Z",
            spread_m=366.8,
            covers_window=False,
            gap_hours=12.3,
        )

    def current(self) -> LocationEvidence:
        return LocationEvidence(
            latitude=39.4565,
            longitude=-0.3465,
            fix_count=15,
            earliest_fix="2021-11-09T14:00:00Z",
            latest_fix="2021-11-09T18:00:00Z",
            spread_m=40.0,
            covers_window=True,
            gap_hours=0.0,
        )

    def containment_case(self, location):
        series = ambient(START, [15.0, 15.0, 16.0, 15.0])
        readings = [(at(START, m), 27.0) for m in (10, 70, 130, 190)]
        return attribute_excursion(readings, series, LABEL_UPPER, location=location)

    def test_a_stale_coordinate_qualifies_the_attribution_without_withdrawing_it(self):
        """A 12 °C gap against a regional November ambient is not explained by having been a
        few hundred metres away — so the finding stands. But `qualified` has to be
        machine-readable: a reader that checks only `attribution` would otherwise treat an
        assumed location exactly like an observed one.
        """
        result = self.containment_case(self.stale())
        assert result.attribution == CONTAINMENT
        assert result.qualified is True
        assert any("LAST-KNOWN POSITION" in n for n in result.notes)
        assert any("an assumption, not an observation" in n for n in result.notes)

    def test_a_coordinate_observed_during_the_window_is_not_qualified(self):
        result = self.containment_case(self.current())
        assert result.attribution == CONTAINMENT
        assert result.qualified is False
        assert not any("LAST-KNOWN POSITION" in n for n in result.notes)

    def test_no_location_evidence_never_claims_the_position_was_current(self):
        """Saying nothing about when a fix was taken is not the same as saying it was current."""
        result = self.containment_case(None)
        assert result.qualified is False
        assert result.to_dict()["location_evidence"] is None

    def test_the_emitted_record_carries_the_gap_and_the_spread(self):
        """The honest limit has to live in the record, not only in the prose around it."""
        document = self.containment_case(self.stale()).to_dict()
        evidence = document["location_evidence"]
        assert document["qualified"] is True
        assert evidence["covers_window"] is False
        assert evidence["gap_hours_to_window"] == 12.3
        assert evidence["fix_spread_m"] == 366.8
        assert "LAST-KNOWN POSITION" in evidence["provenance"]

    def test_an_undetermined_attribution_still_reports_its_location_evidence(self):
        """Whichever way the attribution lands, the reader gets the same provenance."""
        series = ambient(START, [15.0])
        readings = [(at(START, m), 27.0) for m in (10, 200, 260, 320, 380)]
        result = attribute_excursion(readings, series, LABEL_UPPER, location=self.stale())
        assert result.attribution == UNDETERMINED
        assert result.to_dict()["location_evidence"]["covers_window"] is False
