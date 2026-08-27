"""Sandbox entry point: telemetry in, disposition JSON and chart out.

This is what actually runs inside the Daytona sandbox. The agent does not compute the
verdict and does not paraphrase it — it invokes this and reports what came back:

    python -m coldcall.cli --telemetry leg.json --product product_profile.json \
        --allowed-excursion-hours 6 --svg-out excursion.svg

Everything it needs is a positional file or a flag, so the agent can construct the call
from the incident payload without any hidden state. Output is a single JSON object on
stdout; diagnostics go to stderr so that ``stdout`` stays machine-readable even when
something is wrong.

Exit codes: 0 on a computed verdict (including ``destroy`` — a verdict is a success),
2 on bad input. The verdict itself is never signalled through the exit code, because a
caller that branches on exit status would silently treat a destroy as a crash.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from coldcall.disposition import DispositionPolicy, disposition
from coldcall.mkt import Reading
from coldcall.plot import excursion_svg

__all__ = ["main", "load_readings"]

#: Field names accepted for the temperature of a reading, in priority order. The dataset,
#: the replay engine and hand-written fixtures each spell it differently and there is no
#: value in forcing them to agree.
_TEMP_KEYS = ("temp_c", "celsius", "temperature_c", "internal_temp_c", "temperature")
_MINUTES_KEYS = ("minutes", "duration_minutes", "interval_min")
#: Field names accepted for a reading's timestamp. When present, each reading's duration is
#: derived from the gap to the next one rather than assumed — see ``_durations_from_timestamps``.
_TS_KEYS = ("ts", "timestamp", "time", "recorded_at")


def _parse_iso(raw: object) -> datetime | None:
    """Parse an ISO-8601 timestamp, tolerating the trailing ``Z`` that JSON exports use."""
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _durations_from_timestamps(stamps: list[datetime | None], fallback: float) -> list[float]:
    """Turn a list of timestamps into the minutes each reading stands for.

    A logger samples on a nominal interval that drifts, and it drops out. Assuming a flat
    interval understates a record with gaps in it — which biases the excursion percentage,
    which is the number the verdict turns on. So each reading covers the span until the next
    one, and the last reading inherits the median of the rest rather than a guess.

    Returns the fallback for every reading if the stamps are unusable (missing, unordered,
    or all identical), because a wrong duration is worse than an assumed one.
    """
    if any(s is None for s in stamps) or len(stamps) < 2:
        return [fallback] * len(stamps)

    ordered = [s for s in stamps if s is not None]
    gaps = [
        (b - a).total_seconds() / 60.0 for a, b in zip(ordered, ordered[1:], strict=False)
    ]
    if any(g <= 0 for g in gaps):
        return [fallback] * len(stamps)

    tail = sorted(gaps)[len(gaps) // 2]
    return [*gaps, tail]


def load_readings(payload: Any, default_interval_minutes: float = 1.0) -> list[Reading]:
    """Coerce a decoded JSON telemetry document into ``Reading`` objects.

    Accepts three shapes, because three different producers feed this:

    * ``[20.1, 20.4, ...]`` — bare numbers, each standing for ``default_interval_minutes``.
    * ``[{"temp_c": 20.1, "minutes": 5}, ...]`` — explicit durations.
    * ``{"readings": [...], "interval_minutes": 5}`` — a wrapper carrying the interval once.

    Raises:
        ValueError: if the document is not one of those, or a record has no temperature.
    """
    interval = default_interval_minutes
    if isinstance(payload, dict):
        for key in ("interval_minutes", "interval_min", "sampling_interval_minutes"):
            if isinstance(payload.get(key), (int, float)):
                interval = float(payload[key])
                break
        for key in ("readings", "telemetry", "points", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            raise ValueError(
                "telemetry object has no 'readings'/'telemetry'/'points'/'data' array"
            )

    if not isinstance(payload, list) or not payload:
        raise ValueError("telemetry must be a non-empty array of readings")

    temps: list[float] = []
    explicit: list[float | None] = []
    stamps: list[datetime | None] = []
    for index, item in enumerate(payload):
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            temps.append(float(item))
            explicit.append(None)
            stamps.append(None)
            continue
        if not isinstance(item, dict):
            raise ValueError(f"reading {index} is neither a number nor an object")
        for key in _TEMP_KEYS:
            value = item.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                temps.append(float(value))
                break
        else:
            raise ValueError(
                f"reading {index} has no temperature field (looked for {', '.join(_TEMP_KEYS)})"
            )
        explicit.append(
            next(
                (
                    float(item[k])
                    for k in _MINUTES_KEYS
                    if isinstance(item.get(k), (int, float)) and not isinstance(item[k], bool)
                ),
                None,
            )
        )
        stamps.append(next((_parse_iso(item.get(k)) for k in _TS_KEYS if k in item), None))

    derived = _durations_from_timestamps(stamps, interval)
    return [
        Reading(temp, given if given is not None else span)
        for temp, given, span in zip(temps, explicit, derived, strict=True)
    ]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coldcall.cli",
        description="Compute the regulatory disposition of a shipment from its telemetry.",
    )
    p.add_argument("--telemetry", required=True, type=Path, help="JSON telemetry file")
    p.add_argument(
        "--product",
        type=Path,
        help="product profile JSON carrying storage_min_c / storage_max_c and, optionally, "
        "excursion_min_c / excursion_max_c and the label provenance",
    )
    p.add_argument("--label-lower-c", type=float, help="override the product's labelled minimum")
    p.add_argument("--label-upper-c", type=float, help="override the product's labelled maximum")
    p.add_argument(
        "--allowed-excursion-hours",
        type=float,
        required=True,
        help="permitted time out of range. ColdCall policy, not label text — see disposition.py",
    )
    p.add_argument("--retest-at-pct", type=float, default=50.0)
    p.add_argument("--destroy-at-pct", type=float, default=100.0)
    p.add_argument(
        "--no-freeze-rule",
        action="store_true",
        help="stop treating any time below the labelled minimum as automatically disqualifying",
    )
    p.add_argument("--interval-minutes", type=float, default=1.0)
    p.add_argument("--svg-out", type=Path, help="write the excursion chart here")
    p.add_argument("--json-out", type=Path, help="also write the verdict JSON here")
    p.add_argument("--shipment-id", default="", help="echoed into the output for traceability")
    p.add_argument("--lot-id", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        readings = load_readings(
            json.loads(args.telemetry.read_text(encoding="utf-8")),
            default_interval_minutes=args.interval_minutes,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"could not load telemetry from {args.telemetry}: {exc}", file=sys.stderr)
        return 2

    product: dict[str, Any] = {}
    if args.product:
        try:
            product = json.loads(args.product.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"could not load product profile from {args.product}: {exc}", file=sys.stderr)
            return 2

    lower = args.label_lower_c if args.label_lower_c is not None else product.get("storage_min_c")
    upper = args.label_upper_c if args.label_upper_c is not None else product.get("storage_max_c")
    if lower is None or upper is None:
        print(
            "no labelled storage range: pass --label-lower-c/--label-upper-c or a --product "
            "profile carrying storage_min_c and storage_max_c",
            file=sys.stderr,
        )
        return 2

    try:
        policy = DispositionPolicy(
            allowed_excursion_hours=args.allowed_excursion_hours,
            retest_at_pct=args.retest_at_pct,
            destroy_at_pct=args.destroy_at_pct,
            freeze_is_disqualifying=not args.no_freeze_rule,
            source=str(
                product.get("allowance_source")
                or "ColdCall demo policy — not a regulatory limit"
            ),
        )
        result = disposition(readings, float(lower), float(upper), policy)
    except ValueError as exc:
        print(f"could not compute a disposition: {exc}", file=sys.stderr)
        return 2

    document = result.to_dict()
    document["shipment_id"] = args.shipment_id
    document["lot_id"] = args.lot_id
    if product:
        document["product"] = {
            key: product.get(key)
            for key in (
                "set_id",
                "brand_name",
                "generic_name",
                "manufacturer_name",
                "storage_and_handling_verbatim",
                "retrieval_url",
            )
            if product.get(key) is not None
        }

    if args.svg_out:
        try:
            args.svg_out.write_text(
                excursion_svg(
                    readings,
                    float(lower),
                    float(upper),
                    excursion_lower_c=product.get("excursion_min_c"),
                    excursion_upper_c=product.get("excursion_max_c"),
                    title=f"{args.shipment_id or 'Shipment'} — temperature vs labelled envelope",
                    subtitle=(
                        f"verdict: {result.verdict} · MKT {result.mkt_c:.2f} °C · "
                        f"budget {result.budget_consumed_pct:.1f}% consumed"
                    ),
                ),
                encoding="utf-8",
            )
            document["chart_svg_path"] = str(args.svg_out)
        except OSError as exc:  # a missing chart must not lose the verdict
            print(f"warning: could not write the chart to {args.svg_out}: {exc}", file=sys.stderr)

    rendered = json.dumps(document, indent=2, sort_keys=False)
    if args.json_out:
        try:
            args.json_out.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"warning: could not write JSON to {args.json_out}: {exc}", file=sys.stderr)
    print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
