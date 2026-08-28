"""Adapt the Zenodo 7907515 raw-messages sample into canonical corpus legs.

Reuses the streaming parser the demo replay is built on (``coldcall.replay``), then does the
one job the demo never needed: cutting each device's multi-week history into physically
contiguous journeys. A logger that stops reporting for hours and resumes has, as far as the
record shows, been through a handover this data cannot see — treating the whole span as one
shipment would let quiet warehouse weeks dilute a transport excursion's MKT. The cut threshold
(3 h) matches the leg-selection analysis in ``replay/SHIPMENT.md``.

Duplicate-instant readings are resolved here (the CLI rejects rather than guesses): of a
duplicated pair the later-parsed reading survives, the same rule ``coldcall.replay.to_readings``
applies, so a hot duplicate can never be the one discarded silently — both values are real
logger output and the kept one is the one whose interval to the next point exists.

Run ``fetch.sh`` first. Stdlib + coldcall only.
"""

from __future__ import annotations

import json
import sys
from datetime import timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from coldcall.replay import TelemetryPoint, iter_telemetry  # noqa: E402

DATA_DIR = REPO_ROOT / "data" / "corpus" / "zenodo-ll1"
RAW = DATA_DIR / "ll1_raw_sample.json"
GAP_MINUTES = 180.0  # same journey-cut threshold replay/SHIPMENT.md documents
MIN_READINGS = 8  # fewer carries almost no duration evidence
MIN_DURATION_MINUTES = 120.0  # a "journey" shorter than 2 h is a logger check-in

# The exact window DEMO-0001 replays (replay/SHIPMENT.md): device ‴34:CD, 64 readings. Its end
# was the demo sample's last byte, not a logger silence — the journey continues to 11-14 in
# this wider sample — so it is emitted here as an explicit extra leg to keep the demo verdict
# (quarantine_retest) regression-pinned by the corpus alongside the full journey's.
DEMO_WINDOW_DEVICE = "DD:33:04:13:34:CD"
DEMO_WINDOW_START = "2021-11-09T08:23:09+00:00"
DEMO_WINDOW_END = "2021-11-10T04:42:10+00:00"


def cut_legs(points: list[TelemetryPoint]) -> list[list[TelemetryPoint]]:
    """Split one device's time-ordered points wherever the record goes silent."""
    legs: list[list[TelemetryPoint]] = []
    current: list[TelemetryPoint] = []
    for point in points:
        if current and (point.at - current[-1].at).total_seconds() / 60.0 > GAP_MINUTES:
            legs.append(current)
            current = []
        # Duplicate instant: keep the later-parsed reading (see module docstring).
        if current and point.at == current[-1].at:
            current[-1] = point
            continue
        current.append(point)
    if current:
        legs.append(current)
    return [
        leg
        for leg in legs
        if len(leg) >= MIN_READINGS
        and (leg[-1].at - leg[0].at).total_seconds() / 60.0 >= MIN_DURATION_MINUTES
    ]


def main() -> int:
    if not RAW.exists():
        print(f"missing {RAW} — run corpus/datasets/zenodo-ll1/fetch.sh first", file=sys.stderr)
        return 2

    devices: dict[str, list[TelemetryPoint]] = {}
    for point in iter_telemetry(RAW):
        devices.setdefault(point.device, []).append(point)

    legs_dir = DATA_DIR / "legs"
    legs_dir.mkdir(parents=True, exist_ok=True)
    manifest_legs = []
    for device in sorted(devices):
        points = sorted(devices[device], key=lambda p: p.at)
        emit: list[tuple[list[TelemetryPoint], str]] = [(leg, "") for leg in cut_legs(points)]
        if device == DEMO_WINDOW_DEVICE:
            window = [
                p
                for leg, _ in emit
                for p in leg
                if DEMO_WINDOW_START <= p.at.isoformat() <= DEMO_WINDOW_END
            ]
            if window:
                emit.append((window, "-demo-window"))
        for leg, suffix in emit:
            start = leg[0].at.astimezone(timezone.utc)
            leg_id = f"{device.replace(':', '')[-6:]}-{start:%Y%m%d-%H%M}{suffix}"
            file_name = f"{leg_id}.json"
            (legs_dir / file_name).write_text(
                json.dumps(
                    [
                        {"ts": p.at.astimezone(timezone.utc).isoformat(), "temp_c": p.celsius}
                        for p in leg
                    ],
                    indent=1,
                )
                + "\n",
                encoding="utf-8",
            )
            manifest_legs.append(
                {
                    "id": leg_id,
                    "file": f"legs/{file_name}",
                    "device": device,
                    "start": leg[0].at.isoformat(),
                    "end": leg[-1].at.isoformat(),
                    "n": len(leg),
                }
            )

    manifest = {
        "dataset": "zenodo-ll1",
        "source": "https://doi.org/10.5281/zenodo.7907515 (LL1_raw_messages_Public.json)",
        "legs": manifest_legs,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(manifest_legs)} legs from {len(devices)} devices -> {DATA_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
