# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 12:30 CEST — **the thesis arrived.** ColdCall is a pharmaceutical
cold-chain *disposition* agent. The disposition math runs green on real telemetry against a
real drug label. Build is underway against `coldchain-build-spec.md`.

> **Note on this file's history.** PRs #4 and #5 merged in the order #5 then #4, so #4's older
> `STATE.md` landed on top of #5's newer one. Nothing was lost — this rewrite supersedes both.

## Deadline

Deadline: see `COMPETITION.md` → "Deadline" (single source of truth for event facts).

## The thesis (new — this is what changed)

**Detection is solved; the decision is not.** On a temperature excursion, ColdCall computes the
regulatory disposition — release / quarantine-retest / destroy — from deterministic,
unit-tested Python, assembles an evidence bundle, and **halts for a human before any
irreversible action**. The LLM gathers, orchestrates, explains and drafts. The LLM never
decides.

Full thesis proposed in `proposals/VISION.md`. **`VISION.md` is LOCKED and still empty** —
Main Agent applies the proposal and logs it in `GOVERNANCE.md`.

`Q-0001` is answered. `Q-0007` (which product label to judge against) is answered: the real
openFDA amoxicillin label, 20–25 °C, excursions permitted 15–30 °C.

## Done

**Process**

- Public repo (MIT); Qodo installed and reviewing. **PRs #1–#5 merged, zero direct pushes to
  `main`.** Every merge carried a completed review with findings fixed or dismissed in-thread.

**Platform, proven not asserted** (`EXP-0008`)

- TrueForge v0.1.4 on `:8790`. OpenAI **`gpt-5`** answering real turns (the account has
  `gpt-5`/`-mini`/`-pro`, *not* the catalog's `gpt-5.6-sol`).
- **Daytona verified** — a live turn returned `Linux x86_64 3.13.15` from a real remote microVM.
- **Git-backed skill mounts and is read** by the agent inside the sandbox.
- **GitHub MCP — 44 tools live.** `scripts/setup_trueforge.sh`: 4 configured, 0 failed.
  `scripts/verify_apis.sh`: 7/7 sources pass.

**The disposition core — running on real data**

- `src/coldcall/mkt.py` — MKT (time-weighted, log-sum-exp), excursion accounting, stability
  budget. Restored from `3e01090`; kept over the spec's Appendix C reference, which is
  unweighted and numerically naive.
- `src/coldcall/disposition.py` — the decision layer: `release` / `quarantine_retest` /
  `destroy`, Arrhenius potency estimate, margin-to-threshold reporting, policy recorded
  alongside every verdict.
- `src/coldcall/plot.py` — excursion chart as stdlib SVG. **No matplotlib**, deliberately: the
  payload must import against a stock sandbox interpreter.
- `src/coldcall/cli.py` — the sandbox entry point. Derives reading durations from timestamps
  rather than assuming a flat interval.
- **72 tests green**, ruff clean. Sandbox-payload import is proven by subprocess under `-I`.

**The demo case is real and was not tuned**

Zenodo 7907515, device `DD:33:04:13:34:CD` — 20.3 h, 64 readings, one contiguous 231.7 min
excursion peaking at 27 °C. Judged against the real openFDA amoxicillin label with a 6 h
allowance fixed *before* scoring: **MKT 24.54 °C, 64.35% of budget consumed →
`quarantine_retest`**. Selection and runners-up documented in `replay/SHIPMENT.md`.

**Verified, and it constrains what we may claim:** no real openFDA label states a permitted
excursion *duration*. Labels pairing an excursion range with hours describe post-reconstitution
in-use stability — a different allowance. The hours figure is ColdCall policy, stamped as such
into every emitted record.

## In flight

Building the spec end to end. Milestone PRs open as each lands; Devin AI merges.

**M3 is complete** — one incident runs end to end against the live harness, including the
approval gate and an executed action with a checkable receipt (`EXP-0010`). Deny → the agent
reported the denial and stopped; allow → branch `incident/INC-VCC-118-A2231-…` with the
deviation record committed as `1c859fc`.

**M2 is complete** — the incident world exists: `src/coldcall/store.py` (Appendix B's schema in
portable SQL over stdlib `sqlite3`), `replay/engine.py` (streams the real leg on compressed
shipment-time and opens the incident on a sustained excursion), `src/coldcall/report.py` (the
deviation record, numbers filled deterministically), the real `coldchain-sop` skill, and the
orchestrator's real instructions.

## Blocked

Nothing is blocking the critical path.

## Deferred backlog (scheduled, not blocked)

| Item | What it needs | Blocks |
|---|---|---|
| **Supabase connector** | One browser login: Settings → Connectors → supabase → Connect. **OAuth (`dcr`), not a token.** | Real inventory writes. Data layer is built behind one interface with SQLite-in-sandbox as today's default, so this is a config flip, not a rewrite. |
| **Stripe connector** | Same, test mode only. Also OAuth. | Reship order + refund actions. Same drop-in arrangement. |
| **`tests/README.md`** | LOCKED; its layout table names files that changed. | Nothing |
| **San Francisco day / blog post / star TrueForge repo** | Optional prize tracks | Nothing |

## Next intended step

1. Agent manifest + orchestrator instructions against the real thesis; SOP skill reconciled.
2. Replay engine → excursion webhook → incident session; four strands fan out.
3. Approval gate + executed actions with receipts; deny path.
4. Generative-UI incident board; restart-mid-incident proof; README + demo script.

**Do not re-run platform setup.** It is configured and verified; the script is idempotent and
exists for re-verification after a restart, not as a step.

## Work claims

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| `src/coldcall/`, `tests/` | Claude (autonomous run) | 2026-08-27 12:30 CEST | active |
