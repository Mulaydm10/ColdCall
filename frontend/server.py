"""Local demo server: serves the ColdCall frontend and a small JSON API over the
real ColdCall SQLite incident store (src/coldcall). Stdlib only — no new deps.

Bootstrap seeds the store from replay/seed.json, replays the recorded demo leg into
telemetry, opens incident INC-20260829-6D09F2 and records the verdict computed by the
same deterministic CLI the sandbox runs (coldcall.cli, cross-check included).
"""

from __future__ import annotations

import io
import json
import secrets
import sys
import threading
from contextlib import redirect_stdout
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FE = Path(__file__).resolve().parent
REPO = FE.parent
sys.path.insert(0, str(REPO / "src"))

from coldcall import cli  # noqa: E402
from coldcall.store import IncidentStore, TelemetryTick  # noqa: E402

DB = FE / "data" / "coldcall.db"
LEG = FE / "data" / "selected_leg.json"
INC = "INC-20260829-6D09F2"
SHIP = "VCC-118"

store = IncidentStore(DB)
lock = threading.Lock()
verdict_cache: dict = {}


MAX_BODY = 4096


def _field(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return text.replace(" - ", " \u2013 ")


def _rcpt() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"RCPT-{stamp}-{secrets.token_hex(3).upper()}"


def bootstrap() -> None:
    store.initialise()
    if store.shipment(SHIP) is None:
        store.seed(json.loads((REPO / "replay" / "seed.json").read_text()))
    readings = json.loads(LEG.read_text())
    if not store.telemetry_for(SHIP):
        store.record_ticks(
            TelemetryTick(shipment_id=SHIP, ts=r["ts"], internal_temp_c=r["temp_c"])
            for r in readings
        )
    store.open_incident(INC, SHIP)
    out = FE / "data" / "verdict.json"
    if not out.exists():
        with redirect_stdout(io.StringIO()):
            code = cli.main([
                "--telemetry", str(LEG),
                "--product", str(REPO / "data" / "product_profile.json"),
                "--allowed-excursion-hours", "6",
                "--shipment-id", SHIP, "--lot-id", "A2231",
                "--json-out", str(out),
            ])
        if code not in (0,):
            raise SystemExit(f"verdict computation failed (exit {code})")
    inc = store.incident(INC)
    if inc and inc.get("verdict") is None:
        store.record_verdict(INC, json.loads(out.read_text()))
    verdict_cache.update(json.loads(out.read_text()))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(FE), **kw)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            with lock:
                inc = store.incident(INC)
                self._json({
                    "incident": inc,
                    "shipment": store.shipment(SHIP),
                    "product": store.product_for(SHIP),
                    "consignees": store.consignees_for(SHIP),
                    "warehouses": store.qualified_warehouses(),
                    "value_at_risk_usd": store.value_at_risk_usd(SHIP),
                    "verdict": verdict_cache,
                })
            return
        if self.path.split("?")[0] == "/api/telemetry":
            with lock:
                self._json(store.telemetry_for(SHIP))
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/decision":
            self._json({"error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._json({"error": "bad Content-Length"}, 400)
            return
        if n <= 0 or n > MAX_BODY:
            self._json({"error": "JSON body required"}, 413 if n > MAX_BODY else 400)
            return
        try:
            req = json.loads(self.rfile.read(n))
            if not isinstance(req, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            self._json({"error": "invalid JSON body"}, 400)
            return
        try:
            decision = req.get("decision")
            by = _field(req.get("by"), 80)
            if decision not in ("allow", "deny") or not by:
                self._json({"error": "decision (allow|deny) and by are required"}, 400)
                return
            with lock:
                inc = store.incident(INC)
                decided = inc and (
                    inc.get("closed_at")
                    or any(
                        e.get("kind") in ("disposition_executed", "deny_fallback")
                        for e in inc.get("events") or ()
                    )
                )
                if decided:
                    err = {"error": "a decision is already on the record", "incident": inc}
                    self._json(err, 409)
                    return
                receipt = _rcpt()
                if decision == "allow":
                    store.quarantine(SHIP, INC, receipt)
                    store.record_action(
                        INC, "disposition_executed",
                        f"ALLOW signed by {by} - quarantine at a qualified store executed",
                        receipt,
                    )
                    store.close_incident(INC, by)
                else:
                    reason = _field(req.get("reason"), 200) or "unspecified"
                    store.record_action(
                        INC, "deny_fallback",
                        f"DENY by {by} - reason: {reason} - conservative fallback: "
                        f"shipment stays quarantined pending QA review, nothing executed",
                        receipt,
                    )
                self._json({"receipt": receipt, "incident": store.incident(INC)})
        except Exception:  # keep the demo server alive on bad input
            self._json({"error": "internal error"}, 500)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


if __name__ == "__main__":
    bootstrap()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5757
    print(f"coldcall demo server on 127.0.0.1:{port} (db: {DB})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
