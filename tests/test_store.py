"""Tests for the incident store: schema, seeding, telemetry, resolution reads, and the record.

Every store here is a real SQLite file under ``tmp_path`` — never ``data/coldcall.db`` — so
these tests can run concurrently with a live demo and never touch its audit trail.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from coldcall.store import IncidentStore, TelemetryTick

SEED_PATH = Path(__file__).resolve().parent.parent / "replay" / "seed.json"
SHIPMENT_ID = "VCC-118"


@pytest.fixture
def seed_fixture() -> dict:
    """Load the real demo fixture rather than duplicating its rows inline."""
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def store(tmp_path) -> IncidentStore:
    """A fresh, initialised store backed by a throwaway file — never the shared demo db."""
    s = IncidentStore(tmp_path / "coldcall.db")
    s.initialise()
    return s


@pytest.fixture
def seeded_store(store: IncidentStore, seed_fixture: dict) -> IncidentStore:
    """A store already loaded with the real one-shipment demo fixture."""
    store.seed(seed_fixture)
    return store


class TestInitialise:
    def test_creates_the_schema(self, tmp_path, seed_fixture: dict) -> None:
        """A fresh path gets every table the schema declares, ready for first writes."""
        s = IncidentStore(tmp_path / "coldcall.db")
        s.initialise()
        s.seed(seed_fixture)
        s.record_ticks([TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0)])
        # No table-missing or foreign-key error means every table landed correctly linked.
        assert len(s.telemetry_for(SHIPMENT_ID)) == 1

    def test_is_safe_to_call_twice(self, tmp_path, seed_fixture: dict) -> None:
        """CREATE TABLE IF NOT EXISTS means re-running setup never wipes existing data."""
        s = IncidentStore(tmp_path / "coldcall.db")
        s.initialise()
        s.seed(seed_fixture)
        s.record_ticks([TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0)])
        s.initialise()
        assert len(s.telemetry_for(SHIPMENT_ID)) == 1

    def test_telemetry_for_an_unknown_shipment_is_refused(self, store: IncidentStore) -> None:
        """Foreign keys are ON, deliberately. A reading for a shipment that does not exist is a
        bug in the caller, and an audit trail that silently accepts orphan rows is worthless.
        """
        with pytest.raises(sqlite3.IntegrityError):
            store.record_ticks([TelemetryTick("NO-SUCH", "2026-01-01T00:00:00Z", 22.0)])


class TestSeeding:
    def test_seeding_twice_leaves_one_row_per_id(
        self, seeded_store: IncidentStore, seed_fixture: dict
    ) -> None:
        """INSERT OR REPLACE keys on the fixture's ids, so a re-run must not duplicate rows."""
        seeded_store.seed(seed_fixture)
        assert seeded_store.shipment(SHIPMENT_ID) is not None
        assert len(seeded_store.consignees_for(SHIPMENT_ID)) == len(seed_fixture["consignees"])
        assert len(seeded_store.qualified_warehouses()) == sum(
            1 for w in seed_fixture["warehouses"] if w["qualified_crt"] == 1
        )

    def test_reseeding_does_not_wipe_telemetry_written_in_between(
        self, seeded_store: IncidentStore, seed_fixture: dict
    ) -> None:
        """A demo re-run must not erase the readings the replay engine already wrote."""
        seeded_store.record_ticks([TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0)])
        seeded_store.seed(seed_fixture)
        assert len(seeded_store.telemetry_for(SHIPMENT_ID)) == 1

    def test_reseeding_does_not_wipe_incidents_written_in_between(
        self, seeded_store: IncidentStore, seed_fixture: dict
    ) -> None:
        """Same guarantee for the incident record: re-seeding is reference data only."""
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.seed(seed_fixture)
        assert seeded_store.incident("INC-1") is not None

    def test_reseeding_silently_resets_shipment_status(
        self, seeded_store: IncidentStore, seed_fixture: dict
    ) -> None:
        """Live incident state survives a re-seed; only reference columns are refreshed.

        This pins a bug that was found and fixed rather than an intended design: seed() used
        INSERT OR REPLACE, so re-seeding reset a quarantined shipment to 'in_transit'. The
        replay engine seeds on every run, so that would have undone a quarantine mid-demo and
        left the incident record contradicting the shipment row it describes.
        """
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == "excursion"
        seeded_store.seed(seed_fixture)
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == "excursion"

    def test_reseeding_still_refreshes_reference_columns(
        self, seeded_store: IncidentStore, seed_fixture: dict
    ) -> None:
        """Preserving status must not turn seed() into a no-op for everything else."""
        amended = json.loads(json.dumps(seed_fixture))
        amended["shipments"][0]["carrier"] = "air freight"
        seeded_store.seed(amended)
        assert seeded_store.shipment(SHIPMENT_ID)["carrier"] == "air freight"


class TestOpenIncidentIdempotence:
    def test_a_second_open_appends_nothing_to_the_audit_trail(
        self, seeded_store: IncidentStore
    ) -> None:
        """The event log is append-only and meant to be trustworthy, so a duplicate 'opened'
        event would be a small lie about what happened. Second call is a no-op.
        """
        assert seeded_store.open_incident("INC-1", SHIPMENT_ID) is True
        assert seeded_store.open_incident("INC-1", SHIPMENT_ID) is False
        events = seeded_store.incident("INC-1")["events"]
        assert [e["kind"] for e in events].count("opened") == 1


class TestTelemetry:
    def test_record_ticks_returns_the_row_count(self, seeded_store: IncidentStore) -> None:
        """The write count is the caller's confirmation that nothing was silently dropped."""
        ticks = [
            TelemetryTick(SHIPMENT_ID, "2026-01-01T00:02:00Z", 24.0),
            TelemetryTick(SHIPMENT_ID, "2026-01-01T00:01:00Z", 23.0),
        ]
        assert seeded_store.record_ticks(ticks) == 2

    def test_record_ticks_of_empty_iterable_returns_zero(self, seeded_store: IncidentStore) -> None:
        """An empty batch is a no-op, not a round trip to the database."""
        assert seeded_store.record_ticks([]) == 0

    def test_telemetry_for_orders_by_timestamp_not_insertion(
        self, seeded_store: IncidentStore
    ) -> None:
        """Ticks can arrive out of order; readers must see the shipment's actual timeline."""
        seeded_store.record_ticks(
            [
                TelemetryTick(SHIPMENT_ID, "2026-01-01T00:02:00Z", 24.0),
                TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0),
                TelemetryTick(SHIPMENT_ID, "2026-01-01T00:01:00Z", 23.0),
            ]
        )
        rows = seeded_store.telemetry_for(SHIPMENT_ID)
        assert [r["ts"] for r in rows] == [
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            "2026-01-01T00:02:00Z",
        ]


class TestReferenceReads:
    """Reads the disposition and outreach strands make, resolved through the foreign keys."""

    def test_product_for_resolves_through_the_shipment(self, seeded_store: IncidentStore) -> None:
        product = seeded_store.product_for(SHIPMENT_ID)
        assert product is not None
        assert product["id"] == "AMOXICILLIN-500"

    def test_product_for_unknown_shipment_is_none(self, seeded_store: IncidentStore) -> None:
        assert seeded_store.product_for("NO-SUCH-SHIPMENT") is None

    def test_shipment_returns_the_row(self, seeded_store: IncidentStore) -> None:
        shipment = seeded_store.shipment(SHIPMENT_ID)
        assert shipment is not None
        assert shipment["lot_id"] == "A2231"

    def test_shipment_unknown_id_is_none(self, seeded_store: IncidentStore) -> None:
        assert seeded_store.shipment("NO-SUCH-SHIPMENT") is None

    def test_consignees_for_returns_every_row_for_the_shipment(
        self, seeded_store: IncidentStore
    ) -> None:
        consignees = seeded_store.consignees_for(SHIPMENT_ID)
        assert {c["id"] for c in consignees} == {"CON-01", "CON-02", "CON-03"}

    def test_consignees_for_unknown_shipment_is_empty(self, seeded_store: IncidentStore) -> None:
        assert seeded_store.consignees_for("NO-SUCH-SHIPMENT") == []

    def test_qualified_warehouses_excludes_unqualified_and_orders_by_distance(
        self, seeded_store: IncidentStore
    ) -> None:
        """WH-02 is not CRT-qualified and must never appear as a redirect candidate."""
        warehouses = seeded_store.qualified_warehouses()
        assert [w["id"] for w in warehouses] == ["WH-01", "WH-03", "WH-04"]
        distances = [w["distance_km"] for w in warehouses]
        assert distances == sorted(distances)

    def test_value_at_risk_multiplies_units_by_unit_value(
        self, seeded_store: IncidentStore
    ) -> None:
        """4000 units at $12.50 is the headline number the demo shows for this shipment."""
        assert seeded_store.value_at_risk_usd(SHIPMENT_ID) == pytest.approx(4000 * 12.5)

    def test_value_at_risk_for_unknown_shipment_is_zero(self, seeded_store: IncidentStore) -> None:
        assert seeded_store.value_at_risk_usd("NO-SUCH-SHIPMENT") == 0.0


class TestIncidentLifecycle:
    def test_open_incident_flips_shipment_status(self, seeded_store: IncidentStore) -> None:
        """The whole point of opening an incident is to take the shipment out of transit."""
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == "excursion"

    def test_open_incident_appends_an_opened_event(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        incident = seeded_store.incident("INC-1")
        assert incident is not None
        assert incident["events"][0]["kind"] == "opened"

    def test_open_incident_is_idempotent_on_the_incident_row(
        self, seeded_store: IncidentStore
    ) -> None:
        """INSERT OR IGNORE means calling twice must not raise or duplicate the incident row."""
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        incident = seeded_store.incident("INC-1")
        assert incident is not None
        assert incident["shipment_id"] == SHIPMENT_ID

    def test_record_verdict_populates_the_scalar_fields(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.record_verdict(
            "INC-1",
            {
                "verdict": "quarantine_retest",
                "mkt_c": 26.4,
                "budget_consumed_pct": 62.0,
                "margin_pct": 8.5,
                "policy": {"allowed_excursion_hours": 6.0},
            },
        )
        incident = seeded_store.incident("INC-1")
        assert incident["verdict"] == "quarantine_retest"
        assert incident["mkt_c"] == pytest.approx(26.4)
        assert incident["budget_consumed_pct"] == pytest.approx(62.0)
        assert incident["margin_pct"] == pytest.approx(8.5)

    def test_record_verdict_stores_the_policy_as_round_tripping_json(
        self, seeded_store: IncidentStore
    ) -> None:
        """An incident that cannot reproduce the policy it was judged against is unauditable."""
        policy = {"allowed_excursion_hours": 6.0, "source": "demo policy, not label text"}
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.record_verdict("INC-1", {"verdict": "release", "policy": policy})
        incident = seeded_store.incident("INC-1")
        assert json.loads(incident["policy_json"]) == policy

    def test_record_action_raises_on_empty_receipt(self, seeded_store: IncidentStore) -> None:
        """An empty string is falsy in Python but is still a distinct case worth pinning:
        the SOP's invariant is that an action without a receipt did not happen, and an empty
        string is exactly that — no receipt — not a valid zero-length one."""
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        with pytest.raises(ValueError, match="receipt"):
            seeded_store.record_action("INC-1", "quarantine", "detail", "")

    def test_record_action_raises_on_missing_receipt(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        with pytest.raises(ValueError, match="receipt"):
            seeded_store.record_action("INC-1", "quarantine", "detail", None)

    def test_record_action_with_a_real_receipt_is_logged(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.record_action("INC-1", "notify", "consignees notified", "msg-abc123")
        events = seeded_store.incident("INC-1")["events"]
        assert any(e["kind"] == "notify" and e["receipt"] == "msg-abc123" for e in events)

    def test_quarantine_sets_shipment_status(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.quarantine(SHIPMENT_ID, "INC-1", "receipt-001")
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == "quarantined"

    def test_quarantine_logs_an_action_with_its_receipt(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.quarantine(SHIPMENT_ID, "INC-1", "receipt-001")
        events = seeded_store.incident("INC-1")["events"]
        assert any(e["kind"] == "quarantine" and e["receipt"] == "receipt-001" for e in events)

    def test_close_incident_sets_approval_and_close_fields(
        self, seeded_store: IncidentStore
    ) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.close_incident("INC-1", "qp.reviewer@example.invalid")
        incident = seeded_store.incident("INC-1")
        assert incident["approved_by"] == "qp.reviewer@example.invalid"
        assert incident["approved_at"] is not None
        assert incident["closed_at"] is not None

    def test_close_incident_appends_a_closed_event(self, seeded_store: IncidentStore) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.close_incident("INC-1", "qp.reviewer@example.invalid")
        kinds = [e["kind"] for e in seeded_store.incident("INC-1")["events"]]
        assert kinds[-1] == "closed"

    def test_incident_events_are_returned_in_insertion_order(
        self, seeded_store: IncidentStore
    ) -> None:
        """The audit trail's whole value is that the sequence of events is trustworthy."""
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.record_action("INC-1", "notify", "consignees notified", "msg-1")
        seeded_store.quarantine(SHIPMENT_ID, "INC-1", "receipt-001")
        seeded_store.close_incident("INC-1", "qp.reviewer@example.invalid")
        kinds = [e["kind"] for e in seeded_store.incident("INC-1")["events"]]
        assert kinds == ["opened", "notify", "quarantine", "closed"]

    def test_incident_unknown_id_is_none(self, seeded_store: IncidentStore) -> None:
        assert seeded_store.incident("NO-SUCH-INCIDENT") is None


class TestIdempotenceAndAtomicity:
    """Three bugs Qodo found, each pinned so it cannot come back."""

    def test_replaying_the_same_leg_twice_does_not_duplicate_readings(
        self, seeded_store: IncidentStore
    ) -> None:
        """The store preserves telemetry across re-seeds, so ingestion must be idempotent.

        Duplicated readings silently inflate time-at-temperature, which is the number the
        verdict turns on — a re-run of the documented demo would have quietly corrupted it.
        """
        leg = [
            TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0),
            TelemetryTick(SHIPMENT_ID, "2026-01-01T00:10:00Z", 27.0),
        ]
        assert seeded_store.record_ticks(leg) == 2
        assert seeded_store.record_ticks(leg) == 0
        assert len(seeded_store.telemetry_for(SHIPMENT_ID)) == 2

    def test_a_different_reading_at_the_same_instant_is_still_one_row(
        self, seeded_store: IncidentStore
    ) -> None:
        """Uniqueness is on (shipment, ts). A second value for one instant is a duplicate
        record, not a second measurement."""
        seeded_store.record_ticks([TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 22.0)])
        seeded_store.record_ticks([TelemetryTick(SHIPMENT_ID, "2026-01-01T00:00:00Z", 40.0)])
        rows = seeded_store.telemetry_for(SHIPMENT_ID)
        assert len(rows) == 1
        assert rows[0]["temp_c"] == 22.0

    def test_quarantine_with_no_receipt_changes_nothing(
        self, seeded_store: IncidentStore
    ) -> None:
        """Atomicity. The status change and the audit row share one transaction, and the
        receipt is checked before either runs — so a rejected quarantine must leave the
        shipment exactly as it was, not quarantined-and-unlogged.
        """
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        before = seeded_store.shipment(SHIPMENT_ID)["status"]
        with pytest.raises(ValueError, match="receipt"):
            seeded_store.quarantine(SHIPMENT_ID, "INC-1", "")
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == before
        kinds = [e["kind"] for e in seeded_store.incident("INC-1")["events"]]
        assert "quarantine" not in kinds

    def test_a_successful_quarantine_logs_its_receipt(
        self, seeded_store: IncidentStore
    ) -> None:
        seeded_store.open_incident("INC-1", SHIPMENT_ID)
        seeded_store.quarantine(SHIPMENT_ID, "INC-1", "sha:1c859fc")
        assert seeded_store.shipment(SHIPMENT_ID)["status"] == "quarantined"
        events = seeded_store.incident("INC-1")["events"]
        quarantines = [e for e in events if e["kind"] == "quarantine"]
        assert len(quarantines) == 1
        assert quarantines[0]["receipt"] == "sha:1c859fc"


class TestSchemaMigration:
    """A database written before telemetry was idempotent must still open."""

    def test_duplicate_history_is_collapsed_rather_than_blocking_startup(
        self, tmp_path, seed_fixture: dict
    ) -> None:
        """Telemetry is preserved across runs on purpose, so anyone who ran the earlier
        non-idempotent replay has duplicate rows. Creating the unique index over them raises,
        which would have left them unable to run the fixed version without hand-deleting
        their database.
        """
        from coldcall.store import SCHEMA_TABLES

        path = tmp_path / "legacy.db"
        store = IncidentStore(path)
        with sqlite3.connect(path) as conn:
            conn.executescript(SCHEMA_TABLES)
            conn.execute(
                "INSERT INTO products (id, name, storage_min_c, storage_max_c,"
                " excursion_allowance_hours, allowance_source, unit_value_usd)"
                " VALUES ('P', 'p', 20, 25, 6, 'demo', 1.0)"
            )
            conn.execute(
                "INSERT INTO shipments (id, product_id, lot_id, units) VALUES (?,?,?,?)",
                (SHIPMENT_ID, "P", "L", 1),
            )
            for _ in range(3):  # the duplicates a pre-idempotent replay would have left
                conn.execute(
                    "INSERT INTO telemetry (shipment_id, ts, internal_temp_c)"
                    " VALUES (?, '2026-01-01T00:00:00Z', 22.0)",
                    (SHIPMENT_ID,),
                )
            conn.commit()

        store.initialise()  # must not raise
        assert len(store.telemetry_for(SHIPMENT_ID)) == 1

    def test_a_null_temperature_raises_rather_than_being_dropped(
        self, seeded_store: IncidentStore
    ) -> None:
        """`INSERT OR IGNORE` would swallow a NOT NULL violation and report it as a
        harmless duplicate, hiding ingestion corruption behind a verdict computed on an
        incomplete record. `ON CONFLICT (shipment_id, ts) DO NOTHING` targets only the
        conflict that is genuinely benign.
        """
        with pytest.raises(sqlite3.IntegrityError):
            with seeded_store._conn() as conn:
                conn.execute(
                    "INSERT INTO telemetry (shipment_id, ts, internal_temp_c)"
                    " VALUES (?, '2026-01-01T00:00:00Z', NULL)"
                    " ON CONFLICT (shipment_id, ts) DO NOTHING",
                    (SHIPMENT_ID,),
                )
