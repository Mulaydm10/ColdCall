# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-25 08:20 UTC — **`main` carries M1–M5 + M8/M9 (PR #11 merged); the
corpus benchmark is in flight.** Rehearsals 3 and 4 both reach the approval gate and execute
for real. Remaining human items: the governance edit, optional logins, and the video. New
work: a multi-dataset robustness corpus (`corpus/`) on branch `feat/corpus-benchmark`.

## Deadline

See `COMPETITION.md` → "Deadline" (single source of truth for event facts).

## The thesis

**Detection is solved; the decision is not.** On a temperature excursion ColdCall computes the
regulatory disposition — release / quarantine-retest / destroy — from deterministic,
unit-tested Python, explains *why* the load warmed from a historical weather archive, computes
the whole thing **twice** by different numerical routes, assembles an evidence bundle, and
**halts for a human before any irreversible action**. The LLM gathers, orchestrates, explains
and drafts. The LLM never decides.

`VISION.md` is LOCKED and still a placeholder — the thesis is proposed in
`proposals/VISION.md` for the Main Agent to apply and log in `GOVERNANCE.md`. That is the one
governance item outstanding; see the table below.

## Done — `main` carries M1 through M5

**Process.** Public repo (MIT). **10 PRs merged, zero direct pushes to `main`.** Every merge
carried a completed Qodo review with findings fixed or dismissed in-thread; Devin acted as
second reviewer and merged. Across the stack Qodo raised roughly **50 findings over six
rounds**, several of them real defects rather than lint — a regulatory bug in the core maths,
an approval gate that could authorise a call nobody could read, and a retry that could repeat
an irreversible action.

**The judged path, proven end to end** (`EXP-0010`, `EXP-0017`):

- excursion → orchestrator computes the verdict in a **real Daytona microVM** → four strands
  fan out for context → generative-UI evidence bundle → **approval gate** → executed action
  with a checkable receipt.
- Latest rehearsal: deny path **168 s**, allow path **191 s**, producing branch
  `incident/INC-20260827T162354Z-VCC-118-A2231` and commit **`6ccb0bd`** — a 5 878-byte,
  11-section deviation record carrying route context and the independent cross-check.
- The record survives `kill -9`: `./scripts/restart_proof.sh` compares a SHA-256 digest of
  every event's content **and** of the harness config, and passes.

**The numbers, from real data, not tuned.** Zenodo `10.5281/zenodo.7907515`, device
`DD:33:04:13:34:CD`, judged against the real openFDA amoxicillin label with the allowance fixed
before scoring: **MKT 24.54 °C, 64.35 % of budget consumed → `quarantine_retest`**, margin
35.65 pp. Route context: outside air peaked at **17.3 °C** across matched readings while the
consignment reached **27 °C** — a **12.6 °C** median gap → `containment_failure`, marked
**`qualified`** because the GPS predates the excursion by 18.9 h.

**230 tests green, ruff clean, `verify_apis.sh` 9/9, `setup_trueforge.sh` idempotent**
(`5 configured, 2 skipped, 0 failed` on two consecutive runs).

## Needs Mulaydm10 — nothing technical is blocked on it

Everything below needs a browser, an account, or a camera. **None of it was attempted.**

| # | What | Exact steps | What it blocks |
|---|---|---|---|
| 1 | **Apply `proposals/VISION.md`** | Copy its body into `VISION.md` — it is LOCKED, so only you may — then add a row to `GOVERNANCE.md`'s audit table naming the file, the date and the reason. | Nothing technical. Qodo keeps re-reporting "the thesis is fabricated" until it is done: correct by its rule, wrong on the facts. |
| 2 | **Record the ~3-minute video** | Follow `DEMO.md` → `DEMO-0001` exactly; it carries per-beat timings, the expected output at each step, and the three things to say out loud. **Reap Daytona first** (`./scripts/daytona_gc.sh --yes`) and rehearse once before rolling. | Submission. |
| 3 | **Supabase connector** *(optional)* | TrueForge :8790 → Settings → Connectors → supabase → Connect. **OAuth (`dcr`) — a browser login, not a token to paste.** Needs a project at supabase.com. | Nothing. The incident store runs on stdlib SQLite and the demo works without it; this swaps the backend. |
| 4 | **Stripe connector** *(optional)* | Same route, **test mode only**. Also OAuth. | Nothing — the exposure figure comes from `replay/seed.json` today. |
| 5 | **Slack / notification webhook** *(optional)* | Create at api.slack.com/messaging/webhooks (app → Incoming Webhooks → add to a channel), then set `COLDCALL_NOTIFY_WEBHOOK` in `.env`. | Nothing — consignee notification is not part of `DEMO-0001`. |
| 6 | **Optional prize tracks** | Star `truefoundry/trueforge` (10 s, free draw); publish a blog post anywhere and link it in the submission; SF day at luma.com/agent-harness. | Nothing. |

**`GITHUB_TOKEN` is required and is not optional.** Without it the connector is skipped and the
approval gate has **no tool to call**, so the demo's centrepiece silently does not happen rather
than failing loudly. `.env.example` and `DEMO-0001` both say so now.

## Blocked

Nothing.

## In flight

`feat/corpus-benchmark` (Devin, PR #13) — a multi-dataset robustness corpus: the deterministic
CLI run unmodified over **206 legs across 5 real public datasets** (Zenodo LL1 pharma logger 48,
strawberry truck 54, mango air-cargo 62, COVID ULT container tests 39, SOFIE food-chain 3),
0 FAIL/DRIFT, independent cross-check agreeing on every leg. All five datasets integrated.
All five Qodo findings on #13 fixed with tests: round 1 (demo-window fidelity, silent pin
drops, timeout handling — 4796af5) and round 2 (strawberry CSV conversion now atomic
temp-then-rename; converter runs via the project env with `--python 3.12` — d90c617), all
threads resolved in-thread with evidence. Evidence in `corpus/RESULTS.md`; verdicts are
regression pins, see `corpus/README.md`. Awaiting Qodo's next pass, then a human merge.

## Next intended step

1. Land the corpus PR(s) once Qodo and Devin clear them.
2. Mulaydm10 works the table above — items 1 and 2 matter; 3–6 do not.
3. Submit.

**Do not re-run platform setup unprompted.** It is configured and verified; the script is
idempotent and exists for re-verification after a restart, not as a step.

## Work claims

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| `corpus/` (all five datasets, harness, PR #13) | Devin | 2026-08-25 07:10 UTC | done — awaiting Qodo re-review + merge |
