# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-28 — **the build is finished and the project is in its demo phase.**
`main` is at `7aca120`. PRs #1–#11 all merged. The only open PR is **#12**, this
documentation handoff itself — no code is in flight. Everything that remains needs a human.

## Deadline

See `COMPETITION.md` → "Deadline" (single source of truth for event facts).

## Where this stands

**Code complete.** 230 tests green, ruff clean, `scripts/verify_apis.sh` **9/9**,
`scripts/setup_trueforge.sh` idempotent (`5 configured, 2 skipped, 0 failed` on consecutive
runs). Eleven PRs merged with zero direct pushes to `main`; every one carried a completed Qodo
review with findings fixed or dismissed in-thread, and Devin as second reviewer.

**The judged path is proven, not asserted** (`EXP-0010`, `EXP-0017`):

excursion → the orchestrator computes the verdict in a **real Daytona microVM** → strands fan
out across the four specialist roles for context → generative-UI evidence bundle → **approval
gate** → executed action with a checkable receipt. Four roles is the design; the number of
strands a given run actually spawns has varied 0–5 (`EXP-0019`) and is not guaranteed — see the
traps below. Deny stops the agent; allow produced branch
`incident/INC-20260827T162354Z-VCC-118-A2231` and commit **`6ccb0bd`** — a 5 878-byte,
11-section deviation record. The record survives `kill -9`.

**The demo numbers, from real data, with the policy fixed before scoring:**
MKT **24.54 °C**, **64.35 %** of budget consumed → **`quarantine_retest`**, margin 35.65 pp.
Route context: ambient peaked **17.3 °C** across matched readings while the consignment reached
**27 °C** — a **12.6 °C** median gap → **`containment_failure`**, marked **`qualified`**
because the GPS predates the excursion by 18.9 h.

## Needs Mulaydm10 — this is the whole remaining list

Everything here needs a browser, an account, or a camera. **None of it has been attempted.**

| # | What | Exact steps | What it blocks |
|---|---|---|---|
| 1 | **Apply `proposals/VISION.md`** | Copy its body into `VISION.md` — it is LOCKED, so only you may — then add a row to `GOVERNANCE.md`'s audit table naming the file, the date and the reason. | Nothing technical. Qodo keeps re-reporting "the thesis is fabricated" until it is done: correct by its rule, wrong on the facts. |
| 2 | **Record the ~3-minute video** | `DEMO.md` → `DEMO-0001` has per-beat timings, the expected output at each step, and the three things to say out loud. **Read the two traps below first.** | Submission. |
| 3 | **Supabase connector** *(optional)* | TrueForge :8790 → Settings → Connectors → supabase → Connect. **OAuth (`dcr`) — a browser login, not a token.** Needs a project at supabase.com. | Nothing. The store runs on stdlib SQLite; this swaps the backend. |
| 4 | **Stripe connector** *(optional)* | Same route, **test mode only**. Also OAuth. | Nothing — the exposure figure comes from `replay/seed.json`. |
| 5 | **Slack webhook** *(optional)* | api.slack.com/messaging/webhooks → app → Incoming Webhooks → add to a channel; set `COLDCALL_NOTIFY_WEBHOOK` in `.env`. | Nothing — not part of `DEMO-0001`. |
| 6 | **Prize tracks** *(optional)* | Star `truefoundry/trueforge` (free draw); publish a blog post and link it; SF day at luma.com/agent-harness. | Nothing. |

## Before you record — two traps, both seen in rehearsal

1. **Reap Daytona first: `./scripts/daytona_gc.sh --yes`.** A full quota reports a *network*
   error, not a disk error (`EXP-0012`), so it is easy to misdiagnose mid-take. Each run leaves
   several ~3 GiB sandboxes behind against a 30 GiB ceiling.
2. **Rehearse until one take shows BOTH the fan-out and the approval gate.** Neither is
   guaranteed on a given run (`EXP-0019`): strand count has varied 0–5, and the route-context
   weather fetch intermittently fails from inside the sandbox. The code handles that correctly —
   it warns and preserves the verdict — but the *why it warmed* beat can be absent. **Never
   narrate a cause the record does not contain.** Gating runs took 168 s, 191 s and 403 s.

**`GITHUB_TOKEN` is required, not optional.** Without it the connector is skipped and the
approval gate has **no tool to call**: the centrepiece silently does not happen rather than
failing loudly. `./scripts/verify_apis.sh` now checks it can actually *push*, not merely
authenticate.

## Blocked

Nothing.

## In flight

**PR #12** — this handoff, documentation only. It is the last thing not on `main`; once it
merges, `main` carries the final state. No code work is in flight.

## Next intended step

1. Mulaydm10 works items 1 and 2 above. 3–6 are optional and block nothing.
2. Submit.

**Do not re-run platform setup unprompted**, and do not re-verify the platform unprompted — it
is configured and proven. The scripts are idempotent and exist for re-checking after a restart,
not as steps.

## Work claims

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| _(none)_ | — | — | — |
