"""Render the deviation report from a verdict, with the shipment context filled in.

Exists because the alternative failed in a live run. The agent was originally handed an inline
``python -c "…"`` one-liner; it threw a ``SyntaxError`` on an unquoted path, and the retry that
did work passed only the verdict — producing a regulated document that read ``lot ?`` and
``Shipment ?``. A one-liner is the wrong shape for something whose output is an audit record.

Usage inside the sandbox, after the clone:

    PYTHONPATH=src python scripts/make_report.py \\
      --verdict /work/verdict.json \\
      --shipment-id VCC-118 \\
      --out /work/deviation.md

Reads the shipment, product and consignee context from ``replay/seed.json`` in the checkout,
so the numbers in the report come from the same file the strands read.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from coldcall.report import deviation_report  # noqa: E402


def _value_at_risk(units: Any, unit_value: Any) -> float | None:
    """Units x unit value, or ``None`` when the inputs cannot support a currency figure.

    Stricter than "is it a number", because the output is a **regulated deviation record**.
    A `$nan`, `$inf`, or negative value-at-risk rendered as factual currency is worse than
    the `?` the renderer prints for absent data: unusable context is supposed to degrade
    *visibly*, and a bool, a NaN, or a negative slipping through multiplication degrades
    invisibly. `True * 12.5` is `$12.50` and looks perfectly ordinary.

    ``bool`` is excluded explicitly — it is a subclass of ``int``, so an `isinstance` check
    for numbers accepts it. And the product is re-checked after multiplying, because two
    finite operands can still overflow to infinity.
    """
    for candidate in (units, unit_value):
        if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
            return None
        try:
            # `math.isfinite` on an int too large for a float raises rather than returning
            # False, so the guard itself needs guarding — an int literal in a JSON seed has
            # no width limit.
            if not math.isfinite(candidate) or candidate < 0:
                return None
        except OverflowError:
            return None
    try:
        product = float(units) * float(unit_value)
    except (OverflowError, ValueError):
        # Two finite ints can exceed float range on conversion. Losing the figure is
        # correct; losing the whole report to an OverflowError raised through a helper whose
        # docstring promises it never raises is not.
        return None
    return product if math.isfinite(product) else None


def context_from_seed(seed: Any, shipment_id: str) -> dict[str, Any]:
    """Pull the one shipment's context out of the seed fixture.

    Never raises. The docstring used to promise that and the code did not deliver it: a seed
    that was valid JSON but the wrong shape, or a row missing ``id``, raised AttributeError or
    KeyError outside the loader's except clause — losing the whole report, and with it a
    verdict that had already been computed.

    Every layer is therefore checked before it is used, and anything unusable is skipped
    rather than fatal. A report with a blank consignment row is still a usable draft, and the
    renderer prints ``?`` where a value is absent, which a reviewer can see. A traceback is
    not a draft.
    """
    if not isinstance(seed, dict):
        return {"shipment": {}, "product": {}, "consignees": [], "value_at_risk_usd": None}

    def rows(key: str) -> list[dict[str, Any]]:
        value = seed.get(key)
        return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []

    shipment = next((s for s in rows("shipments") if s.get("id") == shipment_id), {})
    product = next(
        (p for p in rows("products") if p.get("id") == shipment.get("product_id")), {}
    )
    consignees = [c for c in rows("consignees") if c.get("shipment_id") == shipment_id]

    value = _value_at_risk(shipment.get("units"), product.get("unit_value_usd"))

    return {
        "shipment": shipment,
        "product": product,
        "consignees": consignees,
        "value_at_risk_usd": value,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python scripts/make_report.py")
    p.add_argument("--verdict", required=True, type=Path, help="verdict JSON from coldcall.cli")
    p.add_argument("--seed", type=Path, default=REPO_ROOT / "replay/seed.json")
    p.add_argument("--shipment-id", required=True)
    p.add_argument("--incident-id", default="", help="the TrueForge session id")
    p.add_argument("--out", type=Path, help="write here as well as to stdout")
    args = p.parse_args(argv)

    try:
        verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read the verdict from {args.verdict}: {exc}", file=sys.stderr)
        return 2

    try:
        seed = json.loads(args.seed.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: no shipment context ({exc}); rendering from the verdict alone",
              file=sys.stderr)
        seed = {}

    context = context_from_seed(seed, args.shipment_id)
    markdown = deviation_report(
        verdict,
        shipment=context["shipment"],
        product=context["product"],
        consignees=context["consignees"],
        incident_id=args.incident_id,
        value_at_risk_usd=context["value_at_risk_usd"],
    )

    print(markdown)
    if args.out:
        try:
            args.out.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            # The caller asked for a file and there is no file. Warning-and-exit-0 meant the
            # agent went on to commit a deviation record that was never written, and the
            # receipt would have pointed at nothing.
            print(f"could not write the report to {args.out}: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
