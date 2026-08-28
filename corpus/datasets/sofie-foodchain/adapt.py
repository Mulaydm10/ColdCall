"""Adapt SOFIE table-grape transport and warehouse data into canonical corpus legs.

Zenodo record 4392842 publishes two Mongo shell exports for truck journeys and one CSV for
warehouse rooms. Timestamps are Unix epoch milliseconds and temperatures are Celsius (unit
documented in SOFIE deliverable D5.4). Candidate streams are kept separate by journey/sensor
or warehouse room, sorted, de-duplicated, cut after logger silences, and filtered by the corpus
duration/read-count floors.

Run ``fetch.sh`` first. Stdlib only.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "corpus" / "sofie-foodchain"
TRANSPORT_FARM_WAREHOUSE = DATA_DIR / "transport_farm_warehouse.json"
TRANSPORT_WAREHOUSE_SUPERMARKET = DATA_DIR / "transport_warehouse_supermarket.json"
WAREHOUSE = DATA_DIR / "warehouse.csv"

GAP_MINUTES = 30.0
MIN_READINGS = 8
MIN_DURATION_MINUTES = 120.0

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_OBJECT_ID = re.compile(r'ObjectId\(("[^"]*")\)')
_NUMBER_LONG = re.compile(r"NumberLong\((-?\d+)\)")


@dataclass(frozen=True, slots=True)
class Point:
    at: datetime
    celsius: float
    sequence: int
    humidity_pct: float | None = None


def epoch_ms_to_utc(value: object) -> datetime:
    """Convert a numeric Unix-millisecond value to an aware UTC datetime."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"timestamp is not numeric Unix milliseconds: {value!r}")
    return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc)


def load_mongo_shell_export(path: Path) -> list[dict[str, object]]:
    """Parse the limited Mongo shell wrappers used by the two transport files."""
    text = path.read_text(encoding="utf-8")
    text = _COMMENT.sub("", text)
    text = _OBJECT_ID.sub(r"\1", text)
    text = _NUMBER_LONG.sub(r"\1", text)
    loaded = json.loads(text)
    if not isinstance(loaded, list):
        raise ValueError(f"{path} must contain an array")
    if not all(isinstance(item, dict) for item in loaded):
        raise ValueError(f"{path} contains a non-object transport record")
    return loaded


def parse_transport(path: Path) -> dict[str, list[Point]]:
    """Return Celsius points grouped by truck gateway and sensor type."""
    streams: dict[str, list[Point]] = {}
    for sequence, record in enumerate(load_mongo_shell_export(path)):
        header = record.get("header")
        event = record.get("event")
        if not isinstance(header, dict) or not isinstance(event, dict):
            continue
        timestamp = header.get("timestamp")
        if not isinstance(timestamp, dict):
            continue
        temperature = event.get("Temperature")
        gateway = event.get("GatewayId")
        sensor_type = event.get("SensorType")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not isinstance(gateway, str)
            or not isinstance(sensor_type, str)
        ):
            continue
        point = Point(
            at=epoch_ms_to_utc(timestamp.get("long")),
            celsius=float(temperature),
            sequence=sequence,
        )
        streams.setdefault(f"{gateway}-{sensor_type}", []).append(point)
    return streams


def parse_warehouse(path: Path) -> dict[str, list[Point]]:
    """Return Celsius and relative-humidity points grouped by monitored room."""
    streams: dict[str, list[Point]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for sequence, row in enumerate(csv.DictReader(handle)):
            entity = row.get("entity_id")
            if not entity:
                continue
            try:
                point = Point(
                    at=epoch_ms_to_utc(int(row["time_index"])),
                    celsius=float(row["temperature"]),
                    humidity_pct=float(row["humidity"]),
                    sequence=sequence,
                )
            except (KeyError, TypeError, ValueError):
                continue
            streams.setdefault(entity, []).append(point)
    return streams


def order_and_deduplicate(points: list[Point]) -> list[Point]:
    """Sort points and keep the later-parsed reading at a duplicate instant."""
    by_instant: dict[datetime, Point] = {}
    for point in sorted(points, key=lambda item: (item.at, item.sequence)):
        by_instant[point.at] = point
    return [by_instant[instant] for instant in sorted(by_instant)]


def cut_legs(points: list[Point]) -> tuple[list[list[Point]], list[list[Point]]]:
    """Split after long silences, returning accepted and duration/count-rejected legs."""
    ordered = order_and_deduplicate(points)
    candidates: list[list[Point]] = []
    current: list[Point] = []
    for point in ordered:
        if (
            current
            and (point.at - current[-1].at).total_seconds() / 60.0 > GAP_MINUTES
        ):
            candidates.append(current)
            current = []
        current.append(point)
    if current:
        candidates.append(current)

    accepted: list[list[Point]] = []
    rejected: list[list[Point]] = []
    for leg in candidates:
        duration = (leg[-1].at - leg[0].at).total_seconds() / 60.0
        target = (
            accepted
            if len(leg) >= MIN_READINGS and duration >= MIN_DURATION_MINUTES
            else rejected
        )
        target.append(leg)
    return accepted, rejected


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _emit_leg(
    legs_dir: Path,
    leg: list[Point],
    leg_id: str,
    metadata: dict[str, object],
) -> dict[str, object]:
    file_name = f"{leg_id}.json"
    (legs_dir / file_name).write_text(
        json.dumps(
            [{"ts": _iso_z(point.at), "temp_c": point.celsius} for point in leg],
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "id": leg_id,
        "file": f"legs/{file_name}",
        "start": _iso_z(leg[0].at),
        "end": _iso_z(leg[-1].at),
        "n": len(leg),
        **metadata,
    }


def _rejection(
    source: str, stream: str, leg: list[Point]
) -> dict[str, object]:
    span_minutes = (leg[-1].at - leg[0].at).total_seconds() / 60.0
    failed = []
    if len(leg) < MIN_READINGS:
        failed.append(f"{len(leg)} readings < {MIN_READINGS}")
    if span_minutes < MIN_DURATION_MINUTES:
        failed.append(f"{span_minutes:.3f} minutes < {MIN_DURATION_MINUTES:g}")
    return {
        "source_file": source,
        "stream": stream,
        "start": _iso_z(leg[0].at),
        "end": _iso_z(leg[-1].at),
        "n": len(leg),
        "span_minutes": round(span_minutes, 3),
        "reason": f"below corpus floor: {', '.join(failed)}",
    }


def main() -> int:
    required = [
        TRANSPORT_FARM_WAREHOUSE,
        TRANSPORT_WAREHOUSE_SUPERMARKET,
        WAREHOUSE,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        print(
            f"missing {', '.join(str(path) for path in missing)} — "
            "run corpus/datasets/sofie-foodchain/fetch.sh first",
            file=sys.stderr,
        )
        return 2

    legs_dir = DATA_DIR / "legs"
    legs_dir.mkdir(parents=True, exist_ok=True)
    for old_leg in legs_dir.glob("*.json"):
        old_leg.unlink()

    manifest_legs: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []

    transport_sources = [
        ("farm-warehouse", TRANSPORT_FARM_WAREHOUSE),
        ("warehouse-supermarket", TRANSPORT_WAREHOUSE_SUPERMARKET),
    ]
    for journey, path in transport_sources:
        for sensor, points in sorted(parse_transport(path).items()):
            accepted, rejected = cut_legs(points)
            for index, leg in enumerate(accepted, start=1):
                short_sensor = sensor.split("-", maxsplit=1)[0][-8:].lower()
                leg_id = (
                    f"transport-{journey}-{short_sensor}-{leg[0].at:%Y%m%d-%H%M}"
                    f"-{index}"
                )
                manifest_legs.append(
                    _emit_leg(
                        legs_dir,
                        leg,
                        leg_id,
                        {
                            "stream_type": "transport_temperature",
                            "journey": journey,
                            "sensor": sensor,
                        },
                    )
                )
            for leg in rejected:
                excluded.append(
                    _rejection(
                        path.name,
                        sensor,
                        leg,
                    )
                )

    for room, points in sorted(parse_warehouse(WAREHOUSE).items()):
        accepted, rejected = cut_legs(points)
        for index, leg in enumerate(accepted, start=1):
            leg_id = f"warehouse-{room.lower()}-{leg[0].at:%Y%m%d-%H%M}-{index}"
            humidities = [
                point.humidity_pct for point in leg if point.humidity_pct is not None
            ]
            manifest_legs.append(
                _emit_leg(
                    legs_dir,
                    leg,
                    leg_id,
                    {
                        "stream_type": "warehouse_temperature_humidity",
                        "location": room,
                        "humidity_min_pct": min(humidities),
                        "humidity_max_pct": max(humidities),
                    },
                )
            )
        for leg in rejected:
            excluded.append(
                _rejection(
                    WAREHOUSE.name,
                    room,
                    leg,
                )
            )

    manifest = {
        "dataset": "sofie-foodchain",
        "source": "https://doi.org/10.5281/zenodo.4392842 (version 2.0)",
        "legs": manifest_legs,
        "excluded_streams": excluded,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{len(manifest_legs)} legs; {len(excluded)} short streams excluded -> "
        f"{DATA_DIR / 'manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
