"""The replay engine — the "world" that ColdCall reacts to.

What it does
------------
Streams a **real recorded shipment leg** into the incident store at a configurable speed,
watches the readings as they land, and the moment the excursion is sustained past its trigger
threshold it opens an incident in TrueForge with a webhook-shaped payload.

Honest framing, everywhere, without exception
---------------------------------------------
This is **real recorded telemetry, replayed**. It is not live commercial telemetry and must
never be described as such — in the README, in the narration, or in the payload this engine
emits. The leg, its provenance, and why it was chosen over the runners-up are documented in
``replay/SHIPMENT.md``. The realism claim we make is the same one Stripe test-mode makes:
real data, real code path, stakes deliberately absent.

Stdlib only — ``urllib`` rather than ``httpx`` — so this runs from a clean checkout with no
install step beyond the project venv.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from coldcall.store import IncidentStore, TelemetryTick  # noqa: E402

DEFAULT_BASE_URL = "http://localhost:8790/api/v1"


@dataclass(frozen=True, slots=True)
class ExcursionTrigger:
    """What the engine saw at the moment it decided this was an incident."""

    shipment_id: str
    started_ts: str
    detected_ts: str
    minutes_out_of_range: float
    peak_c: float
    """The reading furthest from the labelled range, hot or cold — not the maximum.

    Tracking `max()` alone reported a freeze excursion's peak as the coldest-but-highest
    reading, or as -inf when every out-of-range reading was below the minimum. A cold-chain
    incident is exactly the case where that is wrong."""
    label_upper_c: float
    label_lower_c: float
    readings_so_far: int

    def as_payload(self) -> dict[str, Any]:
        return {
            "event": "temperature_excursion",
            "shipment_id": self.shipment_id,
            "excursion_started": self.started_ts,
            "detected_at": self.detected_ts,
            "minutes_out_of_range_at_detection": round(self.minutes_out_of_range, 1),
            "peak_temp_c": self.peak_c,
            "labelled_range_c": [self.label_lower_c, self.label_upper_c],
            "readings_recorded": self.readings_so_far,
            "telemetry_provenance": "real recorded shipment leg, replayed - see replay/SHIPMENT.md",
        }


def _midpoint(lower: float, upper: float) -> float:
    return (lower + upper) / 2.0


def _minutes_between(a: str, b: str) -> float:
    from datetime import datetime

    def parse(raw: str):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))

    return (parse(b) - parse(a)).total_seconds() / 60.0


def _post(url: str, body: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def create_incident_session(base_url: str, agent_manifest: dict[str, Any]) -> str:
    """Create the TrueForge session that *is* the incident record.

    Raises rather than degrading: a replay that silently fails to open an incident looks
    identical to a shipment that never excursed, which is the worst way for this to go wrong.

    Note the body shape — ``{"agent": {"spec": ...}}``. The build spec's Appendix A.6 has
    ``{"agent": ...}``, which the API rejects with only "Invalid input at agent".
    """
    session = _post(f"{base_url}/sessions", {"agent": {"spec": agent_manifest}})
    data = session.get("data", session)
    session_id = data.get("id") or data.get("session_id")
    if not session_id:
        raise RuntimeError(f"session created but no id in response: {session}")
    return str(session_id)


def send_excursion_turn(base_url: str, session_id: str, trigger: ExcursionTrigger) -> str:
    """Send the excursion alert as the session's first turn."""
    message = (
        "EXCURSION ALERT — open an incident and work it per the coldchain-sop skill.\n\n"
        + json.dumps(trigger.as_payload(), indent=2)
    )
    turn = _post(
        f"{base_url}/sessions/{session_id}/turns",
        {"stream": False, "input": [{"type": "user.message", "content": message}]},
    )
    turn_id = turn.get("data", turn).get("id")
    if not turn_id:
        # Session creation already holds this contract; a turn deserves the same one. An
        # empty string here meant replay printed "incident opened" and returned success with
        # no verifiable receipt — the exact thing the SOP forbids the agent from doing.
        raise RuntimeError(f"turn created but no id in response: {turn}")
    return str(turn_id)


def _parse_leg_ts(raw: str) -> datetime:
    """Parse a leg timestamp into an aware datetime, assuming UTC when no offset is given.

    Naive stamps are made aware rather than left alone: `replay` subtracts them, and mixing
    naive with offset-aware raises ``TypeError`` mid-loop — after telemetry has already been
    written, so the advertised input-error path became a partial-write traceback instead.
    """
    return (
        parsed.replace(tzinfo=timezone.utc)
        if (parsed := datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))).tzinfo is None
        else parsed
    )


def _load_leg(leg_path: Path) -> list[dict[str, Any]]:
    """Read and *validate* a recorded leg.

    Checking JSON syntax alone was not enough, and neither was checking each reading in
    isolation. The leg is user-supplied via ``--leg``, so this is an input contract, and three
    things about the series as a whole matter as much as the individual records:

    * **Timestamps must actually parse.** A non-empty string is not a timestamp. ``replay``
      subtracts them later, so a malformed one raised deep in the loop with rows already
      persisted.
    * **They must be strictly increasing.** ``replay`` computes durations and state
      transitions in file order, so an unordered leg yields negative excursion durations, can
      suppress a real trigger, and replays on a timeline that never happened.
    * **No duplicates.** The store keeps only the first reading at a given instant (uniqueness
      on ``(shipment_id, ts)``), while ``replay`` would evaluate every raw temperature — so
      the incident's peak and trigger payload could rest on a reading that is *absent* from
      the audit telemetry a downstream verdict is computed from. Two records for one instant
      is a contradiction to resolve upstream, not something to silently pick between.

    Raises:
        ValueError: naming the offending index and what was wrong with it.
    """
    payload = json.loads(leg_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected a JSON array of readings, got {type(payload).__name__}")
    if not payload:
        raise ValueError("the leg is empty — there is nothing to replay")

    previous: datetime | None = None
    for index, reading in enumerate(payload):
        if not isinstance(reading, dict):
            raise ValueError(f"reading {index} is {type(reading).__name__}, not an object")

        raw_ts = reading.get("ts")
        if not isinstance(raw_ts, str) or not raw_ts.strip():
            raise ValueError(f"reading {index} has no usable 'ts' timestamp")
        try:
            stamp = _parse_leg_ts(raw_ts)
        except ValueError as exc:
            raise ValueError(
                f"reading {index} has an unparseable 'ts' ({raw_ts!r}): {exc}"
            ) from exc

        if previous is not None:
            if stamp == previous:
                raise ValueError(
                    f"reading {index} repeats the timestamp of reading {index - 1} "
                    f"({raw_ts}). The store keeps only the first reading at an instant, so a "
                    f"duplicate would leave the incident resting on telemetry absent from the "
                    f"audit record — resolve the conflict rather than letting one be dropped."
                )
            if stamp < previous:
                raise ValueError(
                    f"reading {index} ({raw_ts}) precedes reading {index - 1}. The replay "
                    f"computes durations in file order, so an unordered leg produces negative "
                    f"excursion times and can suppress a real trigger — sort it first."
                )
        previous = stamp

        temp = reading.get("temp_c")
        if isinstance(temp, bool) or not isinstance(temp, (int, float)):
            raise ValueError(f"reading {index} has a non-numeric 'temp_c' ({temp!r})")
        if not math.isfinite(float(temp)):
            raise ValueError(f"reading {index} has a non-finite 'temp_c' ({temp!r})")
    return payload


def replay(
    leg_path: Path,
    seed_path: Path,
    db_path: Path,
    shipment_id: str,
    speed: float,
    trigger_after_minutes: float,
    base_url: str,
    manifest_path: Path | None,
    dry_run: bool,
) -> int:
    store = IncidentStore(db_path)
    store.initialise()
    store.seed(json.loads(seed_path.read_text(encoding="utf-8")))

    product = store.product_for(shipment_id)
    if product is None:
        print(f"no product for shipment {shipment_id}; is the seed loaded?", file=sys.stderr)
        return 2
    lower = float(product["storage_min_c"])
    upper = float(product["storage_max_c"])

    if not leg_path.exists():
        # data/samples/ is gitignored, so a fresh clone has no leg at all. Saying which file
        # is missing and how to rebuild it beats a bare FileNotFoundError traceback.
        print(
            f"no telemetry at {leg_path}.\n"
            f"data/samples/ is gitignored — the leg is re-fetchable from the dataset. See "
            f"replay/SHIPMENT.md for the exact range request that rebuilds it, or pass "
            f"--leg with your own file.",
            file=sys.stderr,
        )
        return 2

    try:
        readings = _load_leg(leg_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"could not read the leg at {leg_path}: {exc}", file=sys.stderr)
        return 2

    print(
        f"replaying {len(readings)} real readings for {shipment_id} at {speed:g}x "
        f"against a labelled range of {lower:g}-{upper:g} °C",
        flush=True,
    )

    excursion_started: str | None = None
    minutes_out = 0.0
    peak: float | None = None
    fired = False

    for index, reading in enumerate(readings):
        # Persist the INSTANT, normalised to UTC — never the raw offset-bearing string.
        # `_load_leg` validates ordering by comparing parsed instants, but `telemetry_for`
        # sorts the stored `ts` column lexicographically, so a strictly-increasing leg
        # written with mixed offsets came back in reverse chronological order:
        # "…T12:00:00+02:00" (10:00Z) sorts after "…T11:00:00Z" as text and before it in
        # time. Everything downstream reads that column in order, so the excursion window
        # itself was wrong.
        #
        # Normalising here also makes the (shipment_id, ts) uniqueness constraint
        # offset-independent. Two spellings of one instant used to insert as two readings,
        # which double-counts time-at-temperature — the number the verdict turns on.
        ts = _parse_leg_ts(str(reading["ts"])).astimezone(timezone.utc).isoformat()
        temp = float(reading["temp_c"])
        store.record_ticks([TelemetryTick(shipment_id, ts, temp)])

        breached = temp > upper or temp < lower
        if breached:
            # Furthest from the band in whichever direction this excursion actually went.
            if peak is None or abs(temp - _midpoint(lower, upper)) > abs(
                peak - _midpoint(lower, upper)
            ):
                peak = temp
            if excursion_started is None:
                excursion_started = ts
                print(f"  {ts}  {temp:g} °C  ← out of range, excursion opens", flush=True)
            else:
                minutes_out = _minutes_between(excursion_started, ts)
        elif excursion_started is not None and not fired:
            # Back in range before the trigger threshold: a blip, not an incident. Reset
            # rather than accumulating, so two brief blips hours apart never add up to one.
            print(f"  {ts}  {temp:g} °C  ← back in range, excursion closed as a blip", flush=True)
            excursion_started, minutes_out, peak = None, 0.0, None

        if not fired and excursion_started and minutes_out >= trigger_after_minutes:
            fired = True
            trigger = ExcursionTrigger(
                shipment_id=shipment_id,
                started_ts=excursion_started,
                detected_ts=ts,
                minutes_out_of_range=minutes_out,
                peak_c=peak if peak is not None else temp,
                label_upper_c=upper,
                label_lower_c=lower,
                readings_so_far=index + 1,
            )
            print(
                f"\nEXCURSION SUSTAINED {minutes_out:.0f} min (threshold "
                f"{trigger_after_minutes:g}) — peak {peak:g} °C\n",
                flush=True,
            )
            if dry_run or manifest_path is None:
                print(json.dumps(trigger.as_payload(), indent=2), flush=True)
            else:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest.pop("$comment", None)
                # Create the session, record the incident locally, and only THEN send the
                # turn. The agent's first instruction is "open an incident", so it must not
                # run before the row its verdict and actions attach to exists. Doing the
                # turn first also meant a mid-turn failure returned with an orphaned
                # TrueForge session and no local incident or `opened` audit event at all.
                try:
                    session_id = create_incident_session(base_url, manifest)
                except (urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
                    print(f"could not open the incident in TrueForge: {exc}", file=sys.stderr)
                    return 1
                store.open_incident(session_id, shipment_id)
                try:
                    turn_id = send_excursion_turn(base_url, session_id, trigger)
                except (urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
                    # The incident row survives on purpose: an excursion that was detected
                    # and could not be worked is a fact worth keeping, not one to roll back.
                    print(f"incident {session_id} opened but its turn failed: {exc}",
                          file=sys.stderr)
                    return 1
                print(f"incident opened — session {session_id} turn {turn_id}", flush=True)
                print(f"   watch it at {base_url.rsplit('/api/', 1)[0]}", flush=True)

        # Sleep the *replayed* interval, so the demo runs on shipment time compressed, not on
        # a fixed tick. A 12-minute gap in the record is a 12-second pause at 60x.
        if speed > 0 and index + 1 < len(readings):
            gap = _minutes_between(ts, str(readings[index + 1]["ts"]))
            time.sleep(max(0.0, gap * 60.0 / speed))

    if not fired:
        print("\nreplay finished with no sustained excursion", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python replay/engine.py",
        description="Replay a real recorded shipment leg and open an incident on excursion.",
    )
    p.add_argument(
        "--leg",
        type=Path,
        default=REPO_ROOT / "data/samples/selected_leg.json",
        help="the recorded leg to replay. The default lives under data/samples/, which is "
        "gitignored — see replay/SHIPMENT.md for the exact range request that rebuilds it.",
    )
    p.add_argument("--seed", type=Path, default=REPO_ROOT / "replay/seed.json")
    p.add_argument("--db", type=Path, default=REPO_ROOT / "data/coldcall.db")
    p.add_argument("--shipment-id", default="VCC-118")
    p.add_argument(
        "--speed",
        type=float,
        default=60.0,
        help="replay speed multiplier; 0 replays instantly with no pauses",
    )
    p.add_argument(
        "--trigger-after-minutes",
        type=float,
        default=60.0,
        help="sustained minutes out of range before this counts as an incident rather than a blip",
    )
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--manifest", type=Path, default=REPO_ROOT / "agents/coldcall.agent.json")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="stream and detect, print the trigger payload, but do not touch TrueForge",
    )
    args = p.parse_args(argv)

    return replay(
        leg_path=args.leg,
        seed_path=args.seed,
        db_path=args.db,
        shipment_id=args.shipment_id,
        speed=args.speed,
        trigger_after_minutes=args.trigger_after_minutes,
        base_url=args.base_url.rstrip("/"),
        manifest_path=args.manifest,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
