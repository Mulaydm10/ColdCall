# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 06:55 CEST — by Mulaydm10 (+ Claude, acting on their behalf):
Qodo installed and reviewing; PR #1's first review resolved.

## Deadline

Deadline: see `COMPETITION.md` → "Deadline" (single source of truth for event facts).
**Time remaining: ~3 days 14 hours** as of 2026-08-27 06:20 CEST / 04:20 UTC.
Event window opened 2026-08-24 — we are entering **day 4 of 7**.

## Done

- Repo scaffold created.
- **Event facts researched and written into `COMPETITION.md`** (LOCKED; logged in
  `GOVERNANCE.md` audit table) from the official overview/rules/schedule/resources pages and
  the kick-off guide.
- **TrueForge v0.1.4 verified running locally** — `npx @truefoundry/trueforge`, standalone,
  SQLite, serving http://localhost:8790 (HTTP 200), API docs at `/api/v1/docs`.
  Node 26.5.0 on this machine satisfies the Node 22+ requirement.
  Log: `<scratchpad>/trueforge.log`. It also reports a **local sandbox fallback** available
  on darwin, in addition to the documented Daytona provider.
- Judging rubric mirrored into `notes/judging_alignment.md` (6 equally weighted criteria).
- **Project named `ColdCall`.** Public repo created and pushed:
  **https://github.com/Mulaydm10/ColdCall** (MIT) — satisfies the open-source submission
  requirement. `main` is the merge target.
- **PR #1 open** — https://github.com/Mulaydm10/ColdCall/pull/1 (branch `docs/event-facts`).
  This starts the Qodo review trail. Nothing has been pushed directly to `main` since the
  remote existed.
- README now carries the two mandatory sections: `## Qodo Code Review Evidence` (merged-PR link
  pending PR #1 merging) and the AI assistance disclosure required by rule 12.
- **Qodo installed and connected** to `Mulaydm10/ColdCall` — installation Healthy, code-review
  toggle on. It reviewed PR #1 and raised **4 findings, all Medium, no High**; all four were
  valid staleness/accuracy bugs in the docs and **all four are fixed**, not dismissed.
- Qodo Agent Skills installed (`qodo-pr-resolver`, `qodo-get-rules`); only `skills-lock.json`
  is committed.

## In flight

- Nothing being actively edited. Awaiting the project idea from Mulaydm10 to fill `VISION.md`.

## Blocked

Ordered by what unblocks the most:

1. **The project idea / thesis** (`Q-0001`, `VISION.md`) — Mulaydm10 is supplying it. Blocks
   `DEMO.md`, `research/prior_art.md`, and the final shape of `ADR-0002`.
2. **PR #1 not merged yet** — fixes for the first review are pushed; awaiting the follow-up
   review, then a human merge. The README's `## Qodo Code Review Evidence` section cannot name a
   merged PR until that lands.
4. **No model provider API key configured in TrueForge** (`Q-0003`) — the harness runs but
   cannot think without one. BYO key; the SF OpenAI credits do not apply to us.
5. **No Daytona sandbox key** (`Q-0004`) — sandboxed code execution is one of the three beats
   judges must see. Local fallback may cover the demo; unverified.
6. **Stack not formally decided** (`Q-0002`, `ADR-0002`) — largely constrained now by TrueForge
   being Node/TS with `agent.json` agents; final call waits on the idea.

## Next intended step

1. Land PR #1: follow-up Qodo review, then merge, then fill the README's evidence section with
   the merged link and a line on what Qodo surfaced.
2. Mulaydm10: supply the ColdCall idea → `VISION.md` gets drafted and applied, `DEMO-0001`
   becomes writable, `ADR-0002` can close.
3. Mulaydm10: model provider key (`Q-0003`) so the harness can actually think.
4. Optional but time-boxed: the San Francisco day is **2026-08-29** and still upcoming — decide
   whether to attend (separate Luma registration, attendee-only OpenAI credits).

## Latest experiment

`EXP-0001` — booted TrueForge v0.1.4 standalone; serves on :8790, HTTP 200. See
`experiments/experiment_log.md`.

## Work claims

Claim a surface before starting on it; release it here the moment you yield. An agent that
finishes a unit of work updates this table (and the sections above) before stopping — see
`AGENTS.md` for the full protocol.

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| _(none claimed)_ | — | — | — |
