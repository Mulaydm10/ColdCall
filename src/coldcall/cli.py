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
2 on bad input, **3 when the independent cross-check disagrees with the primary
implementation**. The verdict itself is never signalled through the exit code, because a
caller that branches on exit status would silently treat a destroy as a crash — but a
disagreement between two implementations of a regulated calculation is a different kind of
event from either, and deserves its own code.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from coldcall.crosscheck import cross_check
from coldcall.disposition import DispositionPolicy, disposition
from coldcall.mkt import Reading
from coldcall.plot import excursion_svg
from coldcall.weather import CONTAINMENT_GAP_C, attribute_excursion, fetch_ambient

__all__ = ["main", "load_readings"]

#: Field names accepted for the temperature of a reading, in priority order. The dataset,
#: the replay engine and hand-written fixtures each spell it differently and there is no
#: value in forcing them to agree.
_TEMP_KEYS = ("temp_c", "celsius", "temperature_c", "internal_temp_c", "temperature")
_MINUTES_KEYS = ("minutes", "duration_minutes", "interval_min")
#: Field names accepted for a reading's timestamp. When present, each reading's duration is
#: derived from the gap to the next one rather than assumed — see ``_durations_from_timestamps``.
_TS_KEYS = ("ts", "timestamp", "time", "recorded_at")

#: Longest gap that still counts as measured exposure, in minutes. Matches
#: ``replay.to_readings``' default: past four hours of silence, a logger has stopped
#: reporting rather than reported a steady temperature.
MAX_GAP_MINUTES = 240.0


def _parse_iso(raw: object) -> datetime | None:
    """Parse an ISO-8601 timestamp, tolerating the trailing ``Z`` that JSON exports use.

    A naive timestamp is assumed to be UTC rather than left naive. Mixing naive and aware
    datetimes in one series makes subtraction raise ``TypeError``, which turned otherwise
    valid telemetry into a crash instead of the documented exit code 2 — and real exports mix
    the two freely.
    """
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _durations_from_timestamps(
    stamps: list[datetime | None],
    fallback: float,
    max_gap_minutes: float = MAX_GAP_MINUTES,
) -> list[float]:
    """Turn a list of timestamps into the minutes each reading stands for.

    A logger samples on a nominal interval that drifts, and it drops out. Assuming a flat
    interval understates a record with gaps in it — which biases the excursion percentage,
    which is the number the verdict turns on. So each reading covers the span until the next
    one, and the last reading inherits the median of the rest rather than a guess.

    **A dropout is missing evidence, not measured exposure.** Any gap longer than
    ``max_gap_minutes`` is capped there, matching ``replay.to_readings``. Without the cap a
    multi-day logger silence became days of recorded exposure at whatever the last reading
    happened to be — enough to condemn a pallet on a stale hot value, or to dilute MKT with a
    stale cold one. Neither is a measurement.

    Raises:
        ValueError: if the timestamps are not strictly increasing. The previous behaviour was
            to fall back to a flat interval for the *whole* series, which silently collapsed
            hours of excursion into minutes and could release a shipment that should not
            have been. Rejecting is the safe direction to be wrong in; the caller can sort.
    """
    # No timestamps anywhere is a legitimate shape — bare numbers, or records carrying only
    # an explicit duration. SOME timestamps missing or unparseable is corruption, and the old
    # behaviour of falling back for the WHOLE series then turned hours of measured excursion
    # into minutes. Same failure as the out-of-order case, so it gets the same answer.
    if all(s is None for s in stamps) or len(stamps) < 2:
        return [fallback] * len(stamps)
    missing = [i for i, s in enumerate(stamps) if s is None]
    if missing:
        raise ValueError(
            f"{len(missing)} of {len(stamps)} readings have a missing or unparseable "
            f"timestamp (first at index {missing[0]}), while others have one. Guessing "
            f"durations for those would misstate the excursion — fix or drop them."
        )

    ordered = [s for s in stamps if s is not None]
    gaps = [(b - a).total_seconds() / 60.0 for a, b in zip(ordered, ordered[1:], strict=False)]

    for index, gap in enumerate(gaps):
        if gap <= 0:
            raise ValueError(
                f"telemetry is not in chronological order: reading {index + 1} "
                f"({ordered[index + 1].isoformat()}) does not follow reading {index} "
                f"({ordered[index].isoformat()}). Sort the series before scoring it — "
                f"guessing a duration here would misstate the excursion."
            )

    capped = [min(gap, max_gap_minutes) for gap in gaps]
    # A true median, not the upper-middle element. On an even number of gaps the latter can
    # hand the final reading a materially larger duration than the record justifies, which
    # moves the excursion percentage and with it the verdict.
    ordered_gaps = sorted(capped)
    middle = len(ordered_gaps) // 2
    tail = (
        ordered_gaps[middle]
        if len(ordered_gaps) % 2
        else (ordered_gaps[middle - 1] + ordered_gaps[middle]) / 2.0
    )
    return [*capped, tail]


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

    # Only derive from timestamps for readings that do not carry their own duration. When
    # every reading has an authoritative `minutes`, the timestamps are incidental metadata
    # and their completeness is irrelevant — validating them anyway rejected a documented,
    # supported shape over a field nothing was going to read. That was a regression from
    # tightening the timestamp rules, and the tightening is still right for the case where
    # durations actually come from timestamps.
    if all(given is not None for given in explicit):
        return [Reading(temp, given) for temp, given in zip(temps, explicit, strict=True)]

    derived = _durations_from_timestamps(stamps, interval)
    return [
        Reading(temp, given if given is not None else span)
        for temp, given, span in zip(temps, explicit, derived, strict=True)
    ]


def _reading_stamps(path: Path, default_interval_minutes: float) -> list[datetime | None]:
    """Re-read the telemetry for its timestamps alone.

    ``load_readings`` deliberately returns ``Reading`` objects, which carry a duration and no
    absolute time — that is the right shape for the maths, which only cares about how long a
    temperature was held. Route context needs the wall-clock instant to line a reading up
    against an hourly weather series, so it comes from a second pass rather than by widening
    ``Reading`` with a field nothing else uses.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        for key in ("readings", "telemetry", "points", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        return []
    return [
        next((_parse_iso(item.get(k)) for k in _TS_KEYS if k in item), None)
        if isinstance(item, dict)
        else None
        for item in payload
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
    p.add_argument(
        "--route-lat",
        type=float,
        help="latitude of the shipment's route. With --route-lon, adds route context: real "
        "recorded weather at that point, used to say whether the excursion tracked the "
        "outside air or ran away from it. Requires network; omit to skip.",
    )
    p.add_argument("--route-lon", type=float)
    p.add_argument(
        "--containment-gap-c",
        type=float,
        default=CONTAINMENT_GAP_C,
        help="median °C above outside air that marks a containment failure rather than "
        "environmental exposure. ColdCall policy, not a regulatory value.",
    )
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
            loaded = json.loads(args.product.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"could not load product profile from {args.product}: {exc}", file=sys.stderr)
            return 2
        if not isinstance(loaded, dict):
            # Valid JSON is not the same as a usable profile. A top-level list or string
            # parses fine and then explodes on the first .get() — after the telemetry has
            # already been read, which reads like a crash in the maths rather than bad input.
            print(
                f"product profile in {args.product} must be a JSON object, got "
                f"{type(loaded).__name__}",
                file=sys.stderr,
            )
            return 2
        product = loaded

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
        result = disposition(
            readings,
            float(lower),
            float(upper),
            policy,
            excursion_lower_c=product.get("excursion_min_c"),
            excursion_upper_c=product.get("excursion_max_c"),
        )
    except ValueError as exc:
        print(f"could not compute a disposition: {exc}", file=sys.stderr)
        return 2

    document = result.to_dict()

    # Recompute independently before anyone sees the verdict. On a disagreement the document
    # says so and the exit code is non-zero, because a bundle whose two implementations
    # disagree must not reach a human who might act on it.
    check = cross_check(result, readings, policy)
    document["cross_check"] = check.to_dict()

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

    # Route context is opt-in and never fatal. It explains *why* the load warmed, which the
    # disposition maths cannot; but a weather lookup failing must not cost us a verdict we
    # already computed, so the failure is reported inside the document rather than raised.
    if args.route_lat is not None and args.route_lon is not None:
        # Keep every reading, timestamp or not. Dropping the untimestamped ones would let
        # the coverage figure describe only the timestamped subset — a report claiming full
        # coverage while some hot readings were never considered at all.
        derived_stamps = _reading_stamps(args.telemetry, args.interval_minutes)
        stamps = [
            (stamp, reading.celsius)
            for stamp, reading in zip(derived_stamps, readings, strict=False)
        ]
        if not any(stamp is not None for stamp, _ in stamps):
            document["route_context"] = {
                "error": "no usable timestamps in the telemetry, so weather cannot be matched"
            }
        else:
            known = [stamp for stamp, _ in stamps if stamp is not None]
            try:
                ambient = fetch_ambient(
                    args.route_lat, args.route_lon, min(known), max(known)
                )
                context = attribute_excursion(
                    stamps, ambient, float(upper), threshold_c=args.containment_gap_c
                )
                document["route_context"] = context.to_dict()
                document["route_context"]["ambient_source"] = ambient.source
            except (RuntimeError, ValueError) as exc:
                print(f"warning: no route context ({exc})", file=sys.stderr)
                document["route_context"] = {"error": str(exc)}

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

    if check.blocks_presentation:
        for line in check.disagreements:
            print(f"CROSS-CHECK FAILED: {line}", file=sys.stderr)
        print(
            "The verdict above was computed twice and the two implementations disagree. "
            "Do not present it. Exit code 3.",
            file=sys.stderr,
        )

    rendered = json.dumps(document, indent=2, sort_keys=False)
    if args.json_out:
        try:
            args.json_out.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"warning: could not write JSON to {args.json_out}: {exc}", file=sys.stderr)
    print(rendered)
    # 3, distinct from 2 (bad input) and 0 (a verdict, including destroy). A caller that
    # branches on this can tell "your telemetry is wrong" from "our arithmetic is wrong",
    # which are different emergencies.
    return 3 if check.blocks_presentation else 0


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
