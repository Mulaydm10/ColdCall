# ColdCall frontend

The demo site: eight routes (Home, Overview, How it works, Console, Incidents, Evidence,
Decision room, Sources) over the real ColdCall incident store.

## Run locally (live mode)

```sh
python3 frontend/server.py          # → http://127.0.0.1:5757/ColdCall.dc.html
```

Stdlib only — no new dependencies. On startup the server seeds the SQLite store from
`replay/seed.json`, replays the recorded demo leg (`data/selected_leg.json`) into telemetry,
opens incident `INC-20260829-6D09F2`, and records the verdict computed by the same
deterministic CLI the sandbox runs (`coldcall.cli`, cross-check included). Allow/Deny in the
Decision room write real receipts to the store and survive restarts.

API:

- `GET /api/state` — incident, shipment, product, consignees, warehouses, value at risk, verdict
- `GET /api/telemetry` — the recorded readings
- `POST /api/decision` — `{"decision": "allow"|"deny", "by": "...", "reason": "..."}`

## Static hosting (Vercel)

The site degrades gracefully when the API is absent: it renders the same recorded DEMO-0001
state from built-in fixtures, and the Decision room signature flow works in-page (no receipt
is persisted). Deploy this directory as a static site; `vercel.json` rewrites `/` to the page.

## Honesty notes

- The Console and the How-it-works pipeline replay the recorded DEMO-0001 run; they are not a
  live stream from a running TrueForge session.
- The corpus rows on Incidents/Evidence are the real benchmark results (`corpus/RESULTS.md`).
- Market figures on the Overview carry their sources; see the Sources route.
