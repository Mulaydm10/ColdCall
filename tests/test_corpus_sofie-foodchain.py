"""SOFIE food-chain adapter parsing, ordering, and leg-floor rules."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


adapt = _load_module(
    REPO_ROOT / "corpus" / "datasets" / "sofie-foodchain" / "adapt.py",
    "sofie_foodchain_adapt",
)

T0 = datetime(2020, 9, 23, 10, 0, tzinfo=timezone.utc)


def _point(minutes: float, celsius: float = -0.5, sequence: int = 0):
    return adapt.Point(
        at=T0 + timedelta(minutes=minutes),
        celsius=celsius,
        sequence=sequence,
    )


def test_mongo_shell_export_parses_object_id_number_long_and_comment(tmp_path):
    raw = tmp_path / "transport.json"
    raw.write_text(
        """/* 1 */
[
  {
    "_id": ObjectId("5f6b2379a7c4b1feb4c905aa"),
    "header": {"timestamp": {"long": NumberLong(1600856953000)}},
    "event": {
      "GatewayId": "gateway-1",
      "SensorType": "SOFIE_SENSOR_TYPE_1",
      "Temperature": -0.36
    }
  }
]
""",
        encoding="utf-8",
    )

    streams = adapt.parse_transport(raw)

    (point,) = streams["gateway-1-SOFIE_SENSOR_TYPE_1"]
    assert point.at == datetime(2020, 9, 23, 10, 29, 13, tzinfo=timezone.utc)
    assert point.celsius == -0.36


def test_out_of_order_duplicate_keeps_later_parsed_reading():
    points = [
        _point(10, celsius=-0.2, sequence=0),
        _point(0, sequence=1),
        _point(10, celsius=0.4, sequence=2),
    ]

    ordered = adapt.order_and_deduplicate(points)

    assert [point.at for point in ordered] == [T0, T0 + timedelta(minutes=10)]
    assert ordered[-1].celsius == 0.4


def test_gap_cut_and_duration_floor_are_applied():
    long_leg = [_point(minutes, sequence=index) for index, minutes in enumerate(range(0, 130, 10))]
    short_start = 130 + 31
    short_leg = [
        _point(short_start + minutes, sequence=100 + index)
        for index, minutes in enumerate(range(0, 80, 10))
    ]

    accepted, rejected = adapt.cut_legs(long_leg + short_leg)

    assert accepted == [long_leg]
    assert rejected == [short_leg]


def test_warehouse_parser_groups_rooms_and_reads_humidity(tmp_path):
    raw = tmp_path / "warehouse.csv"
    raw.write_text(
        "entity_id,entity_type,humidity,temperature,time_index\n"
        "RoomB,Room,84.0,-0.09,1600869826456\n"
        "RoomA,Room,56.0,25.03,1600870065614\n",
        encoding="utf-8",
    )

    streams = adapt.parse_warehouse(raw)

    assert set(streams) == {"RoomA", "RoomB"}
    assert streams["RoomB"][0].humidity_pct == 84.0
    assert streams["RoomB"][0].celsius == -0.09
