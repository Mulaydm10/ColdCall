# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 06:20 CEST — by Mulaydm10 (+ Claude, acting on their behalf):
event facts researched and landed in `COMPETITION.md`; TrueForge running locally.

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

## In flight

- Nothing being actively edited. Awaiting the project idea from Mulaydm10 to fill `VISION.md`.

## Blocked

Ordered by what unblocks the most:

1. **The project idea / thesis** (`Q-0001`, `VISION.md`) — Mulaydm10 is supplying it. Blocks
   `DEMO.md`, `research/prior_art.md`, and the final shape of `ADR-0002`.
2. **Public GitHub repo does not exist yet** (`Q-0005`). There is no git remote; the repo is
   local-only on `main` with 2 direct commits. The hackathon requires a *public* repo AND that
   every substantive change land through a **Qodo-reviewed pull request** — so the remote must
   exist before any further real work is committed. Needs a repo name decision (currently `tru`).
3. **Qodo not installed** (`Q-0005`) — requires Mulaydm10 to sign in at app.qodo.ai with GitHub
   admin on the repo. An agent cannot do this step. **Highest-risk item:** judges check that the
   Qodo trail runs through the build, not just the final merge, and we are on day 4 with zero PRs.
4. **No model provider API key configured in TrueForge** (`Q-0003`) — the harness runs but
   cannot think without one. BYO key; the SF OpenAI credits do not apply to us.
5. **No Daytona sandbox key** (`Q-0004`) — sandboxed code execution is one of the three beats
   judges must see. Local fallback may cover the demo; unverified.
6. **Stack not formally decided** (`Q-0002`, `ADR-0002`) — largely constrained now by TrueForge
   being Node/TS with `agent.json` agents; final call waits on the idea.

## Next intended step

1. Mulaydm10: supply the idea → `VISION.md` gets drafted and applied.
2. Mulaydm10: create/confirm the public GitHub repo + install Qodo on it (both need a human).
3. Then: first branch + PR immediately, to start the Qodo review trail on day 4 rather than day 7.

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
