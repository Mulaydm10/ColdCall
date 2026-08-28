"""Adapt the strawberry cold-chain transport dataset into canonical corpus legs.

One leg per shipment x probe position. The source is a wide table — one row per 10-minute
instant, nine probe columns — so the adapter's real job is to explode it back into nine
independent single-probe series and cut each of them where the record goes silent. Probes are
never averaged: the whole point of nine probes in one trailer is that they disagree, and a
trailer-mean would hide exactly the hot corner a disposition call turns on.

Cutting and cleaning rules (all documented in DATASET.md):

* a gap longer than ``GAP_MINUTES`` (3 h) starts a new leg — a probe that stops reporting for
  hours and resumes has been through a handover this record cannot see, and treating the whole
  span as one journey would let the quiet hours dilute an excursion;
* a segment with fewer than ``MIN_READINGS`` readings or a span under ``MIN_DURATION_MINUTES``
  carries almost no duration evidence and is dropped;
* duplicate instants are resolved here rather than in the CLI (which rejects rather than
  guesses): of a duplicated instant the later-parsed reading survives;
* blank cells are missing samples, not zeros, and are simply absent from the leg. Nothing is
  interpolated, smoothed or invented.

Source timestamps are naive (no offset, no timezone stated anywhere in the paper or the
mirror). They are labelled UTC without shifting — see the "Timezone" section of DATASET.md;
every quantity ColdCall computes from a leg is a duration or an ordering, so the unknown
absolute offset cannot change a verdict.

Run ``fetch.sh`` first (it downloads the Parquet and converts it to the CSV read here).
Stdlib only.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "corpus" / "strawberry"

SHIPMENTS = ("S1", "S2", "S3", "S4", "S5", "S6")
SENSORS = (
    "Front_Top",
    "Front_Middle",
    "Front_Bottom",
    "Middle_Top",
    "Middle_Middle",
    "Middle_Bottom",
    "Rear_Top",
    "Rear_Middle",
    "Rear_Bottom",
)

GAP_MINUTES = 180.0  # same journey-cut threshold the zenodo-ll1 adapter uses
MIN_READINGS = 8
MIN_DURATION_MINUTES = 120.0

SOURCE = (
    "Abdella, Brecht & Uysal, arXiv:2103.12895 / doi:10.1016/j.jfoodeng.2021.110477 — "
    "via huggingface.co/datasets/Professor29/Cold-Chain-Transportation-Strawberry "
    "@53ddd9410cf560e6e4647e7dff96655d48811559 (benchmark_v2/S1..S6)"
)


@dataclass(frozen=True)
class Reading:
    """One probe sample: an instant and a temperature in degrees Celsius."""

    at: datetime
    celsius: float


def parse_timestamp(raw: str) -> datetime:
    """Parse a source timestamp and label it UTC.

    The converted CSV writes ISO-8601 (``2019-03-12T12:30:00``); the mirrors also publish the
    same instants as ``2019/3/12 12:30``, so both are accepted. A timestamp that already
    carries an offset is converted rather than relabelled.
    """
    text = raw.strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        raise ValueError(f"unparseable timestamp: {raw!r}")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_shipment(path: Path) -> dict[str, list[Reading]]:
    """Explode one wide shipment CSV into one time-ordered series per probe position."""
    series: dict[str, list[Reading]] = {sensor: [] for sensor in SENSORS}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            at = parse_timestamp(row["ts"])
            for sensor in SENSORS:
                cell = (row.get(sensor) or "").strip()
                if not cell:  # missing sample — absent, not zero
                    continue
                series[sensor].append(Reading(at, float(cell)))
    return {sensor: points for sensor, points in series.items() if points}


def cut_legs(points: list[Reading]) -> list[list[Reading]]:
    """Split one probe's time-ordered readings wherever the record goes silent."""
    ordered = sorted(points, key=lambda p: p.at)
    legs: list[list[Reading]] = []
    current: list[Reading] = []
    for point in ordered:
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
    missing = [s for s in SHIPMENTS if not (DATA_DIR / f"{s}.csv").exists()]
    if missing:
        print(
            f"missing {', '.join(f'{s}.csv' for s in missing)} in {DATA_DIR} — "
            "run corpus/datasets/strawberry/fetch.sh first",
            file=sys.stderr,
        )
        return 2

    legs_dir = DATA_DIR / "legs"
    legs_dir.mkdir(parents=True, exist_ok=True)
    manifest_legs = []
    probes = 0
    for shipment in SHIPMENTS:
        series = read_shipment(DATA_DIR / f"{shipment}.csv")
        for sensor in SENSORS:
            points = series.get(sensor)
            if not points:  # probe absent from this trailer, or never reported
                continue
            probes += 1
            legs = cut_legs(points)
            # A probe that stayed contiguous keeps the plain <shipment>-<sensor> id; one the
            # gap rule split gets a start-stamped id per segment, so no id is ever reused.
            split = len(legs) > 1
            for leg in legs:
                start = leg[0].at
                leg_id = f"{shipment}-{sensor}"
                if split:
                    leg_id = f"{leg_id}-{start:%Y%m%d-%H%M}"
                file_name = f"{leg_id}.json"
                (legs_dir / file_name).write_text(
                    json.dumps(
                        [{"ts": p.at.isoformat(), "temp_c": p.celsius} for p in leg],
                        indent=1,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                manifest_legs.append(
                    {
                        "id": leg_id,
                        "file": f"legs/{file_name}",
                        "shipment": shipment,
                        "sensor": sensor,
                        "start": leg[0].at.isoformat(),
                        "end": leg[-1].at.isoformat(),
                        "n": len(leg),
                        "min_c": min(p.celsius for p in leg),
                        "max_c": max(p.celsius for p in leg),
                    }
                )

    manifest = {
        "dataset": "strawberry",
        "source": SOURCE,
        "legs": manifest_legs,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{len(manifest_legs)} legs from {probes} reporting probes across "
        f"{len(SHIPMENTS)} shipments -> {DATA_DIR / 'manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
