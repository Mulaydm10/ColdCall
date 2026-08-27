"""The incident store: inventory, telemetry, consignees, and the incident record itself.

Why SQLite, and why that is not a compromise
--------------------------------------------
The build spec puts this data in Supabase, reached over its remote MCP connector. That
connector is OAuth (``dcr``) — a browser login, not an API token — and it is deferred by the
Main Agent, so it is not available to configure unattended.

Rather than stub it, the schema and every access path live here behind one interface, with
stdlib ``sqlite3`` as the working default. Two consequences worth being explicit about:

* Nothing here is mocked. These are real tables taking real writes, readable by the agent
  from inside the sandbox and by a human with the ``sqlite3`` CLI.
* Switching to Supabase is a change of backend, not a rewrite. The schema below is the one in
  the spec's Appendix B, expressed in portable SQL, so the same DDL seeds either.

The columns are the spec's, with two additions that the disposition layer needs and Appendix B
did not have: ``incidents.margin_pct`` and ``incidents.policy_json``. An incident record that
does not carry the policy in force when the verdict was reached cannot be re-derived later,
which defeats the point of keeping the record at all.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["SCHEMA", "IncidentStore", "TelemetryTick"]

#: Appendix B of the build spec, in portable SQL. Deliberately free of Postgres-only syntax
#: (no ``generated always as identity``, no ``timestamptz``) so the same DDL seeds SQLite
#: today and Supabase the moment its connector is authorised.
SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  storage_min_c REAL NOT NULL,
  storage_max_c REAL NOT NULL,
  excursion_min_c REAL,
  excursion_max_c REAL,
  excursion_allowance_hours REAL NOT NULL,
  allowance_source TEXT NOT NULL,
  label_provenance TEXT,
  unit_value_usd REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS shipments (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(id),
  lot_id TEXT NOT NULL,
  units INTEGER NOT NULL,
  origin TEXT, destination TEXT, carrier TEXT,
  status TEXT NOT NULL DEFAULT 'in_transit'
);

CREATE TABLE IF NOT EXISTS telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shipment_id TEXT NOT NULL REFERENCES shipments(id),
  ts TEXT NOT NULL,
  internal_temp_c REAL NOT NULL,
  ambient_temp_c REAL,
  door_open INTEGER DEFAULT 0,
  route_stage TEXT
);
CREATE INDEX IF NOT EXISTS telemetry_shipment_ts ON telemetry(shipment_id, ts);

CREATE TABLE IF NOT EXISTS consignees (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL REFERENCES shipments(id),
  name TEXT, email TEXT, units_expected INTEGER
);

CREATE TABLE IF NOT EXISTS warehouses (
  id TEXT PRIMARY KEY,
  name TEXT, city TEXT,
  qualified_crt INTEGER NOT NULL DEFAULT 0,
  distance_km REAL
);

CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL REFERENCES shipments(id),
  opened_at TEXT NOT NULL,
  verdict TEXT,
  mkt_c REAL,
  budget_consumed_pct REAL,
  margin_pct REAL,
  policy_json TEXT,
  approved_by TEXT, approved_at TEXT,
  closed_at TEXT
);

-- Every state change, appended, never updated. The incident row is the current answer; this
-- is how it got there. A regulated record needs both.
CREATE TABLE IF NOT EXISTS incident_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT NOT NULL REFERENCES incidents(id),
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT,
  receipt TEXT
);
CREATE INDEX IF NOT EXISTS incident_events_incident ON incident_events(incident_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class TelemetryTick:
    """One reading as the replay engine emits it."""

    shipment_id: str
    ts: str
    internal_temp_c: float
    ambient_temp_c: float | None = None
    door_open: bool = False
    route_stage: str | None = None


class IncidentStore:
    """Every read and write the agent and the replay engine need, in one place.

    Not a general ORM and deliberately so: the surface here is exactly the operations the SOP
    calls for, which keeps the Supabase swap small and keeps a stray ``DELETE`` from being
    reachable at all.
    """

    def __init__(self, path: str | Path = "data/coldcall.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # The replay engine writes while the agent reads. WAL lets that happen without the
        # reader blocking, which otherwise shows up as a stalled demo rather than an error.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialise(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ---- seeding -----------------------------------------------------------------

    def seed(self, fixture: dict[str, Any]) -> None:
        """Load products, shipments, consignees and warehouses from a fixture document.

        Idempotent: re-seeding replaces the reference rows and leaves telemetry and incidents
        alone, so a demo can be re-run without wiping the audit trail it just produced.
        """
        with self._conn() as conn:
            for product in fixture.get("products", []):
                conn.execute(
                    "INSERT OR REPLACE INTO products (id, name, storage_min_c, storage_max_c,"
                    " excursion_min_c, excursion_max_c, excursion_allowance_hours,"
                    " allowance_source, label_provenance, unit_value_usd)"
                    " VALUES (:id, :name, :storage_min_c, :storage_max_c, :excursion_min_c,"
                    " :excursion_max_c, :excursion_allowance_hours, :allowance_source,"
                    " :label_provenance, :unit_value_usd)",
                    product,
                )
            for shipment in fixture.get("shipments", []):
                # Upsert every column EXCEPT status. A shipment's status is live incident
                # state, not reference data: `INSERT OR REPLACE` here would silently reset a
                # quarantined shipment to 'in_transit' on the next seed. The replay engine
                # seeds on every run, so that is not a theoretical hazard — it would undo a
                # quarantine mid-demo and leave the incident record contradicting the
                # shipment row it describes.
                conn.execute(
                    "INSERT INTO shipments (id, product_id, lot_id, units, origin,"
                    " destination, carrier, status)"
                    " VALUES (:id, :product_id, :lot_id, :units, :origin, :destination,"
                    " :carrier, :status)"
                    " ON CONFLICT(id) DO UPDATE SET"
                    " product_id = excluded.product_id, lot_id = excluded.lot_id,"
                    " units = excluded.units, origin = excluded.origin,"
                    " destination = excluded.destination, carrier = excluded.carrier",
                    shipment,
                )
            for consignee in fixture.get("consignees", []):
                conn.execute(
                    "INSERT OR REPLACE INTO consignees (id, shipment_id, name, email,"
                    " units_expected) VALUES (:id, :shipment_id, :name, :email, :units_expected)",
                    consignee,
                )
            for warehouse in fixture.get("warehouses", []):
                conn.execute(
                    "INSERT OR REPLACE INTO warehouses (id, name, city, qualified_crt,"
                    " distance_km) VALUES (:id, :name, :city, :qualified_crt, :distance_km)",
                    warehouse,
                )

    # ---- telemetry ---------------------------------------------------------------

    def record_ticks(self, ticks: Iterable[TelemetryTick]) -> int:
        rows = [
            (
                t.shipment_id,
                t.ts,
                t.internal_temp_c,
                t.ambient_temp_c,
                int(t.door_open),
                t.route_stage,
            )
            for t in ticks
        ]
        if not rows:
            return 0
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO telemetry (shipment_id, ts, internal_temp_c, ambient_temp_c,"
                " door_open, route_stage) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def telemetry_for(self, shipment_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT ts, internal_temp_c AS temp_c, ambient_temp_c, door_open, route_stage"
                " FROM telemetry WHERE shipment_id = ? ORDER BY ts",
                (shipment_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    # ---- reference reads the strands make ----------------------------------------

    def product_for(self, shipment_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT p.* FROM products p JOIN shipments s ON s.product_id = p.id"
                " WHERE s.id = ?",
                (shipment_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def shipment(self, shipment_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def consignees_for(self, shipment_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM consignees WHERE shipment_id = ? ORDER BY name", (shipment_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def qualified_warehouses(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM warehouses WHERE qualified_crt = 1 ORDER BY distance_km"
            )
            return [dict(row) for row in cur.fetchall()]

    def value_at_risk_usd(self, shipment_id: str) -> float:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT s.units * p.unit_value_usd AS value FROM shipments s"
                " JOIN products p ON p.id = s.product_id WHERE s.id = ?",
                (shipment_id,),
            )
            row = cur.fetchone()
            return float(row["value"]) if row and row["value"] is not None else 0.0

    # ---- the incident record -----------------------------------------------------

    def open_incident(self, incident_id: str, shipment_id: str) -> bool:
        """Open an incident and flag the shipment.

        Fully idempotent, including the audit trail: a second call on the same incident id is
        a no-op and appends nothing. The event log is append-only and is meant to be
        trustworthy, so a duplicate ``opened`` event would be a small lie about what happened.

        Returns True if this call opened the incident, False if it already existed.
        """
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO incidents (id, shipment_id, opened_at)"
                " VALUES (?, ?, ?)",
                (incident_id, shipment_id, _now()),
            )
            if cursor.rowcount == 0:
                return False
            conn.execute(
                "UPDATE shipments SET status = 'excursion' WHERE id = ? AND status = 'in_transit'",
                (shipment_id,),
            )
            conn.execute(
                "INSERT INTO incident_events (incident_id, ts, kind, detail)"
                " VALUES (?, ?, 'opened', ?)",
                (incident_id, _now(), f"excursion on {shipment_id}"),
            )
            return True

    def record_verdict(self, incident_id: str, verdict_json: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE incidents SET verdict = ?, mkt_c = ?, budget_consumed_pct = ?,"
                " margin_pct = ?, policy_json = ? WHERE id = ?",
                (
                    verdict_json.get("verdict"),
                    verdict_json.get("mkt_c"),
                    verdict_json.get("budget_consumed_pct"),
                    verdict_json.get("margin_pct"),
                    json.dumps(verdict_json.get("policy", {})),
                    incident_id,
                ),
            )
            conn.execute(
                "INSERT INTO incident_events (incident_id, ts, kind, detail)"
                " VALUES (?, ?, 'verdict', ?)",
                (incident_id, _now(), json.dumps(verdict_json)),
            )

    def record_action(self, incident_id: str, kind: str, detail: str, receipt: str) -> None:
        """Log an executed action and its receipt.

        ``receipt`` is not optional by accident. The SOP's rule is that an action without a
        receipt did not happen, and a store that let one be logged without one would quietly
        undermine the audit trail it exists to keep.
        """
        if not receipt:
            raise ValueError(
                f"refusing to log action {kind!r} with no receipt: an action without a "
                "receipt did not happen"
            )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO incident_events (incident_id, ts, kind, detail, receipt)"
                " VALUES (?, ?, ?, ?, ?)",
                (incident_id, _now(), kind, detail, receipt),
            )

    def quarantine(self, shipment_id: str, incident_id: str, receipt: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE shipments SET status = 'quarantined' WHERE id = ?", (shipment_id,))
        self.record_action(incident_id, "quarantine", f"{shipment_id} -> quarantined", receipt)

    def close_incident(self, incident_id: str, approved_by: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE incidents SET approved_by = ?, approved_at = ?, closed_at = ?"
                " WHERE id = ?",
                (approved_by, _now(), _now(), incident_id),
            )
            conn.execute(
                "INSERT INTO incident_events (incident_id, ts, kind, detail)"
                " VALUES (?, ?, 'closed', ?)",
                (incident_id, _now(), f"approved by {approved_by}"),
            )

    def incident(self, incident_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
            row = cur.fetchone()
            if not row:
                return None
            record = dict(row)
            events = conn.execute(
                "SELECT ts, kind, detail, receipt FROM incident_events"
                " WHERE incident_id = ? ORDER BY id",
                (incident_id,),
            ).fetchall()
            record["events"] = [dict(e) for e in events]
            return record
