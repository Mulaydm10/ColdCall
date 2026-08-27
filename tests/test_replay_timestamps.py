"""Regression tests for the mixed-UTC-offset timestamp bug in the replay engine.

`_load_leg` validated chronological ordering by comparing PARSED instants, but the raw
offset-bearing timestamp STRING was what got persisted, and `telemetry_for` sorts that column
lexicographically. A leg that is strictly increasing in real time but written with mixed UTC
offsets therefore came back in reverse chronological order — e.g. "…T12:00:00+02:00" (10:00Z)
sorts *after* "…T11:00:00Z" as text despite being an hour earlier. The fix normalises to UTC at
the write site, in `replay()`, before the row is persisted.

``replay/`` is not an installed package (no ``__init__.py``, not on the configured pytest
pythonpath), so `REPO_ROOT` is put on `sys.path` here the same way `replay/engine.py` puts
`src/` on it for its own `coldcall` import.

Every database here is a real SQLite file under ``tmp_path`` — never ``data/coldcall.db``.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from replay.engine import _load_leg, _parse_leg_ts, replay  # noqa: E402

from coldcall.store import IncidentStore  # noqa: E402

SEED_PATH = REPO_ROOT / "replay" / "seed.json"
SHIPMENT_ID = "VCC-118"


def _run_replay(leg_path: Path, db_path: Path) -> int:
    """Invoke the engine the way ``--dry-run`` does: no network, no sleeping, tmp_path db."""
    return replay(
        leg_path=leg_path,
        seed_path=SEED_PATH,
        db_path=db_path,
        shipment_id=SHIPMENT_ID,
        speed=0.0,
        trigger_after_minutes=60.0,
        base_url="http://unused.invalid/api/v1",
        manifest_path=None,
        dry_run=True,
    )


@pytest.fixture
def mixed_offset_db(tmp_path: Path) -> Path:
    """Replay a leg that is strictly increasing in real time but mixes Z and +02:00 offsets.

    Readings, in file order, by real UTC instant: 09:00Z, then 10:00Z (spelled +02:00, so its
    wall-clock hour is *later* than the next reading's), then 11:00Z. Lexicographically the raw
    strings sort as 09:00Z, 11:00Z, 12:00+02:00 — a different order than the instants they name,
    which is exactly the shape that broke `telemetry_for`'s ORDER BY ts before the fix.
    """
    leg = [
        {"ts": "2021-11-09T09:00:00Z", "temp_c": 22.0},
        {"ts": "2021-11-09T12:00:00+02:00", "temp_c": 22.5},
        {"ts": "2021-11-09T11:00:00Z", "temp_c": 23.0},
    ]
    raw_ts = [r["ts"] for r in leg]
    assert sorted(raw_ts) != raw_ts, "fixture must scramble under lexicographic sort"

    leg_path = tmp_path / "leg.json"
    leg_path.write_text(json.dumps(leg), encoding="utf-8")
    db_path = tmp_path / "coldcall.db"
    assert _run_replay(leg_path, db_path) == 0
    return db_path


class TestParseLegTs:
    def test_normalises_z_offset_and_naive_to_aware_utc(self) -> None:
        """Z, an explicit offset, and a naive stamp (assumed UTC) all come back aware.

        `_load_leg` and `replay` both subtract these values; mixing an aware datetime with a
        naive one raises `TypeError` mid-loop, after telemetry has already been written — so
        every input shape must produce something aware, never a bare naive datetime.
        """
        z = _parse_leg_ts("2021-11-09T12:00:00Z")
        offset = _parse_leg_ts("2021-11-09T12:00:00+02:00")
        naive = _parse_leg_ts("2021-11-09T12:00:00")

        assert z.tzinfo is not None
        assert offset.tzinfo is not None
        assert naive.tzinfo is not None

        # A naive stamp is assumed UTC, so it lands on the same instant as the "Z" reading.
        assert naive.astimezone(timezone.utc) == z.astimezone(timezone.utc)
        # Same wall-clock reading as `z`, but +02:00 means the UTC instant is 2h earlier.
        assert offset.astimezone(timezone.utc) == z.astimezone(timezone.utc) - timedelta(hours=2)


class TestReplayTimestampOrdering:
    def test_mixed_offset_leg_comes_back_in_true_chronological_order(
        self, mixed_offset_db: Path
    ) -> None:
        """The headline regression: a leg with mixed offsets must still read back in the order
        the instants actually happened, not the order their raw strings sort in.
        """
        store = IncidentStore(mixed_offset_db)
        rows = store.telemetry_for(SHIPMENT_ID)
        # 09:00Z, then 10:00Z (spelled +02:00), then 11:00Z - true chronological order.
        assert [r["temp_c"] for r in rows] == [22.0, 22.5, 23.0]

    def test_stored_timestamps_are_utc_normalised_regardless_of_input_offset(
        self, mixed_offset_db: Path
    ) -> None:
        """No offset-bearing spelling survives into the column - everything reads back as UTC.

        This is what makes the ordering fix work at all: `telemetry_for` sorts the `ts` column
        as plain text, so mixed offsets in storage would still scramble the read-back order
        even if the write path parsed them correctly on the way in.
        """
        store = IncidentStore(mixed_offset_db)
        rows = store.telemetry_for(SHIPMENT_ID)
        stored_ts = [r["ts"] for r in rows]
        assert stored_ts == [
            "2021-11-09T09:00:00+00:00",
            "2021-11-09T10:00:00+00:00",
            "2021-11-09T11:00:00+00:00",
        ]
        assert not any("+02:00" in ts for ts in stored_ts)


class TestLoadLegRejectsRepeatedInstants:
    def test_mixed_offsets_naming_the_same_instant_twice_is_rejected(self, tmp_path: Path) -> None:
        """`_load_leg` compares PARSED instants, so two different spellings of one instant must
        still be caught as a repeat - the bug was only in what got persisted, not in this check.
        """
        leg = [
            {"ts": "2021-11-09T09:00:00Z", "temp_c": 22.0},
            {"ts": "2021-11-09T11:00:00+02:00", "temp_c": 22.5},  # also 09:00 UTC
        ]
        leg_path = tmp_path / "leg.json"
        leg_path.write_text(json.dumps(leg), encoding="utf-8")

        with pytest.raises(ValueError, match="repeats"):
            _load_leg(leg_path)


class TestOrdinaryLegUnaffected:
    def test_an_all_utc_leg_still_replays_in_order(self, tmp_path: Path) -> None:
        """Guard against the fix breaking the normal path: a leg that was never ambiguous
        about its offsets must still read back in file order with its values intact.
        """
        leg = [
            {"ts": "2021-11-09T09:00:00Z", "temp_c": 21.0},
            {"ts": "2021-11-09T10:00:00Z", "temp_c": 22.0},
            {"ts": "2021-11-09T11:00:00Z", "temp_c": 23.0},
        ]
        leg_path = tmp_path / "leg.json"
        leg_path.write_text(json.dumps(leg), encoding="utf-8")
        db_path = tmp_path / "coldcall.db"

        assert _run_replay(leg_path, db_path) == 0

        store = IncidentStore(db_path)
        rows = store.telemetry_for(SHIPMENT_ID)
        assert [r["temp_c"] for r in rows] == [21.0, 22.0, 23.0]
        assert [r["ts"] for r in rows] == [
            "2021-11-09T09:00:00+00:00",
            "2021-11-09T10:00:00+00:00",
            "2021-11-09T11:00:00+00:00",
        ]
