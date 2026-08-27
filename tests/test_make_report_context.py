"""Seed parsing for the deviation record: nothing here may raise, and nothing may lie.

`context_from_seed` promises in its docstring that it never raises — the verdict has already
been computed by the time it runs, and losing the report would lose that too. And the report
it feeds is a regulated document, so a figure that cannot be trusted must come out as absent
(`?`) rather than as plausible-looking currency.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from make_report import _value_at_risk, context_from_seed  # noqa: E402

GOOD_SEED = {
    "shipments": [{"id": "VCC-118", "product_id": "P1", "units": 4000}],
    "products": [{"id": "P1", "unit_value_usd": 12.5}],
    "consignees": [{"id": "C1", "shipment_id": "VCC-118", "units_expected": 100}],
}


class TestValueAtRisk:
    """A currency figure in a deviation record is a factual claim about money."""

    def test_the_ordinary_case(self):
        assert _value_at_risk(4000, 12.5) == 50_000.0

    @pytest.mark.parametrize(
        "units,price,why",
        [
            (True, 12.5, "bool is a subclass of int, so isinstance accepts it silently"),
            (4000, True, "and on the other operand too"),
            (-4000, 12.5, "a negative quantity is not a smaller risk, it is a bad row"),
            (4000, -12.5, "a negative price would render as negative currency"),
            (4000, float("nan"), "$nan is worse than no figure at all"),
            (4000, float("inf"), "and so is $inf"),
            (10**200, 10**200, "two finite operands can still overflow the product"),
            (10**400, 2, "math.isfinite raises on an int too wide for a float"),
            ("lots", 12.5, "a string quantity"),
            (None, 12.5, "an absent quantity"),
        ],
    )
    def test_unusable_inputs_produce_no_figure_and_never_raise(self, units, price, why):
        assert _value_at_risk(units, price) is None, why

    def test_zero_is_a_legitimate_value_not_a_rejection(self):
        """Zero units is a real, reportable state — do not confuse it with missing data."""
        assert _value_at_risk(0, 12.5) == 0.0


class TestContextFromSeed:
    def test_the_good_seed_resolves_everything(self):
        context = context_from_seed(GOOD_SEED, "VCC-118")
        assert context["shipment"]["id"] == "VCC-118"
        assert context["product"]["unit_value_usd"] == 12.5
        assert len(context["consignees"]) == 1
        assert context["value_at_risk_usd"] == 50_000.0

    @pytest.mark.parametrize(
        "seed",
        [
            ["not", "a", "mapping"],
            None,
            "a string",
            {"shipments": "not a list", "products": None},
            {"shipments": [{"no_id": 1}], "products": [{"no_id": 2}]},
            {"shipments": [None, 42], "products": [[]]},
            {},
        ],
    )
    def test_a_malformed_seed_degrades_rather_than_raising(self, seed):
        """The verdict is already computed by now. Losing the report would lose it too."""
        context = context_from_seed(seed, "VCC-118")
        assert context["shipment"] == {}
        assert context["value_at_risk_usd"] is None

    def test_an_unknown_shipment_is_empty_not_an_error(self):
        assert context_from_seed(GOOD_SEED, "NO-SUCH")["shipment"] == {}

    def test_a_shipment_with_an_unusable_quantity_keeps_its_other_context(self):
        """One bad field must not cost the consignment table its remaining rows."""
        seed = {
            "shipments": [{"id": "VCC-118", "product_id": "P1", "units": "lots"}],
            "products": [{"id": "P1", "unit_value_usd": 12.5}],
        }
        context = context_from_seed(seed, "VCC-118")
        assert context["shipment"]["id"] == "VCC-118"
        assert context["value_at_risk_usd"] is None
