"""The deviation record — the document a regulator would actually read.

This file exists because its absence let a crash ship. `deviation_report` had no test at all,
so a name collision in its section numbering was only caught by running the script by hand.
A rendering function whose output is an audit record deserves the same treatment as the maths
that feeds it.
"""

from __future__ import annotations

import re

import pytest

from coldcall.crosscheck import cross_check
from coldcall.disposition import DispositionPolicy, disposition
from coldcall.mkt import Reading
from coldcall.report import deviation_report

CRT_LOWER, CRT_UPPER = 20.0, 25.0

SHIPMENT = {
    "id": "VCC-118",
    "lot_id": "A2231",
    "units": 4000,
    "origin": "Rotterdam DC",
    "destination": "Lyon regional hub",
    "carrier": "road freight",
}
PRODUCT = {
    "name": "Amoxicillin 500 mg capsules",
    "label_provenance": "openFDA set_id e13cafe2-…: Store at 20 to 25 C",
}


def verdict_document(**extra) -> dict:
    readings = [Reading(22.0, 60.0)] * 20 + [Reading(27.0, 60.0)] * 3
    policy = DispositionPolicy(allowed_excursion_hours=6.0)
    result = disposition(readings, CRT_LOWER, CRT_UPPER, policy)
    document = result.to_dict()
    document["cross_check"] = cross_check(result, readings, policy).to_dict()
    document.update(extra)
    return document


ROUTE = {
    "attribution": "containment_failure",
    "median_gap_c": 12.6,
    "peak_internal_c": 27.0,
    "peak_ambient_c": 17.3,
    "matched_readings": 14,
    "total_excursion_readings": 14,
    "coverage": 1.0,
    "containment_gap_threshold_c": 5.0,
    "threshold_note": "policy, not a regulatory value",
    "notes": ["The load ran a median 12.6 °C above outside air."],
    "ambient_source": "Open-Meteo ERA5",
}


def section_numbers(markdown: str) -> list[int]:
    return [int(m) for m in re.findall(r"^## (\d+)\. ", markdown, re.MULTILINE)]


class TestSectionNumbering:
    """Two sections are conditional, so the numbering has to be computed, not written down."""

    def test_numbers_are_contiguous_without_route_context(self):
        """A gap in a regulated document reads as a *missing section* to an auditor.

        Hard-coded numbers made a report without route context jump from 4 to 6.
        """
        numbers = section_numbers(deviation_report(verdict_document(), SHIPMENT, PRODUCT))
        assert numbers == list(range(1, len(numbers) + 1))

    def test_numbers_are_contiguous_with_route_context(self):
        markdown = deviation_report(verdict_document(route_context=ROUTE), SHIPMENT, PRODUCT)
        numbers = section_numbers(markdown)
        assert numbers == list(range(1, len(numbers) + 1))

    def test_route_context_adds_exactly_one_section(self):
        without = section_numbers(deviation_report(verdict_document(), SHIPMENT, PRODUCT))
        with_route = section_numbers(
            deviation_report(verdict_document(route_context=ROUTE), SHIPMENT, PRODUCT)
        )
        assert len(with_route) == len(without) + 1

    def test_it_renders_at_all(self):
        """The regression that started this file: a name collision crashed the renderer."""
        assert deviation_report(verdict_document(), SHIPMENT, PRODUCT).strip()


class TestFactsComeFromTheVerdict:
    def test_the_numbers_are_the_module_s_own(self):
        document = verdict_document()
        markdown = deviation_report(document, SHIPMENT, PRODUCT, value_at_risk_usd=50_000.0)
        assert f"{document['mkt_c']:.2f}" in markdown
        assert "VCC-118" in markdown and "A2231" in markdown
        assert "$50,000.00" in markdown

    def test_a_missing_context_row_degrades_rather_than_crashing(self):
        """A report with a blank field is still a usable draft; a traceback loses the verdict."""
        markdown = deviation_report(verdict_document())
        assert "QUARANTINE RETEST" in markdown
        assert "?" in markdown  # the unknown consignment fields


class TestHonestySurvivesRendering:
    """Every claim the code is careful about must still be careful on the page."""

    def test_the_potency_figure_is_labelled_an_estimate(self):
        markdown = deviation_report(verdict_document(), SHIPMENT, PRODUCT)
        assert "ESTIMATE, not an assay" in markdown

    def test_policy_and_regulation_stay_separated(self):
        markdown = deviation_report(verdict_document(), SHIPMENT, PRODUCT)
        assert "no real drug label states a permitted excursion" in markdown
        assert "ColdCall policy" in markdown

    def test_the_telemetry_is_never_called_live(self):
        markdown = deviation_report(verdict_document(), SHIPMENT, PRODUCT)
        assert "real recorded shipment data, replayed" in markdown
        assert "live telemetry" not in markdown.replace("Not live telemetry", "")

    def test_the_route_threshold_is_marked_as_ours(self):
        markdown = deviation_report(verdict_document(route_context=ROUTE), SHIPMENT, PRODUCT)
        assert "policy, not a regulatory value" in markdown

    def test_the_cross_check_limit_travels_with_its_reassurance(self):
        """Saying "verified twice" without saying what that does not prove is overclaiming."""
        markdown = deviation_report(verdict_document(), SHIPMENT, PRODUCT)
        assert "not proof of correctness" in markdown

    def test_the_agent_sections_are_marked_not_left_blank(self):
        """A silent blank invites an agent to fill it with something plausible."""
        markdown = deviation_report(verdict_document(), SHIPMENT, PRODUCT)
        assert markdown.count("TO BE COMPLETED BY") >= 3


class TestFailureStates:
    def test_a_disagreeing_cross_check_shouts_on_the_page(self):
        document = verdict_document()
        document["cross_check"] = {
            **document["cross_check"],
            "agrees": False,
            "disagreements": ["VERDICT DISAGREES: primary says release, independent says destroy"],
        }
        markdown = deviation_report(document, SHIPMENT, PRODUCT)
        assert "DO NOT ACT ON THIS RECORD" in markdown
        assert "VERDICT DISAGREES" in markdown

    def test_a_failed_weather_lookup_says_the_cause_is_not_established(self):
        """Not "no cause found" — the difference matters to whoever writes the CAPA."""
        markdown = deviation_report(
            verdict_document(route_context={"error": "archive unreachable"}), SHIPMENT, PRODUCT
        )
        assert "not established" in markdown
        assert "Do not infer one from the temperature alone" in markdown

    @pytest.mark.parametrize("borderline", [True, False])
    def test_a_borderline_verdict_is_called_out(self, borderline):
        document = verdict_document()
        document["is_borderline"] = borderline
        markdown = deviation_report(document, SHIPMENT, PRODUCT)
        assert ("This call is borderline" in markdown) is borderline
