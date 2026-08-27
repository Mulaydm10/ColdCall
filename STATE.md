# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 09:15 CEST — by Mulaydm10 (+ Claude, acting on their behalf):
full stack installed, configured and verified; three plan assumptions corrected; PR #3's
Qodo review resolved (4 bugs fixed, 4 findings dismissed with reasons).

## Deadline

Deadline: see `COMPETITION.md` → "Deadline" (single source of truth for event facts).
**Time remaining: ~3 days 12 hours** as of 2026-08-27 07:20 CEST / 05:20 UTC.

## Done

**Process (all mandatory gates cleared)**

- Public repo https://github.com/Mulaydm10/ColdCall (MIT); Qodo installed, Healthy, reviewing.
- **PRs #1 and #2 merged**, each with a completed review, recorded decisions, and a clean
  follow-up review against the final code. Zero direct pushes to `main`.
- **PR #3 merged** (2026-08-27 07:10 UTC, 7 commits). Qodo raised 4 bugs and 6 rule violations;
  all 4 bugs fixed, and the re-review against the final code returned **0 bugs**. The 6 rule
  violations were dismissed in-thread with reasons and re-report because the learned rule
  persists — two of them still produced repo changes, because the finding pointed at genuinely
  ambiguous wording even where its conclusion was wrong.
- **Three PRs merged, zero direct pushes to `main` since the remote existed.**

**The judged path is proven, not asserted** (`EXP-0008`)

- OpenAI **`gpt-5`** registered and answering real turns. Note the account has
  `gpt-5`/`gpt-5-mini`/`gpt-5-pro`, **not** the `gpt-5.6-sol` in TrueForge's catalog preset —
  the catalog is a suggestion, the key decides.
- **Daytona `status: ready`.** The replacement key carries `write:snapshots`, which the first
  one lacked. A live turn produced `sandbox: v1:daytona:…` returning **`Linux x86_64 3.13.15`** —
  a genuine remote microVM, not this macOS/arm64 host. Network reachable from inside
  (`github:200`).
- **Git-backed skill mounts and is read.** The agent fetched `coldchain-sop` from GitHub inside
  the sandbox and quoted its governing rule verbatim. Re-verified after the merge with the ref
  pointed back at `main`.
- **GitHub MCP connected — 44 tools live**, authorised with the existing `gh` CLI token rather
  than a newly minted credential.
- `scripts/setup_trueforge.sh` reports **4 configured, 0 failed**.
- Homebrew **git 2.55.0** installed, so the local sandbox fallback can also mount skills — see
  `EXP-0009` for why the Xcode git shim cannot.
- README carries the `## Qodo Code Review Evidence` section and the AI-assistance disclosure.

**Stack — installed and verified, not merely declared**

- `ADR-0002` **Accepted**: Node runs the harness (mandatory), Python computes the regulated
  numbers. Python is `uv`-managed in a project-local `.venv` (3.12; floor 3.11). No global
  installs anywhere.
- `src/coldcall/` — **zero required dependencies**, because it is uploaded into a sandbox and
  runs against a stock interpreter:
  - `mkt.py` — mean kinetic temperature (log-sum-exp, not naive summation) + excursion
    accounting + a release/review/quarantine verdict carrying every input needed to re-derive it.
  - `replay.py` — streaming parser for the 402 MB telemetry array; never loads it into memory,
    and tolerates the truncated tail a range request always produces.
- **47 tests green** (`uv run pytest`), ruff clean. The maths is cross-checked against an
  independently written naive implementation, so an optimisation cannot silently break it.
- `agents/coldcall.agent.json` — validated against the live API (accepted up to the
  unconfigured model provider). Approval gates on every MCP server; Stripe gated at `@all`.
- `skills/coldchain-sop/SKILL.md` — **registered on the running harness and reads back**.
- `scripts/setup_trueforge.sh` — idempotent (PUT throughout), `--dry-run`, names exactly which
  keys are missing. `scripts/verify_apis.sh` — **7/7 sources pass right now**.
- TrueForge v0.1.4 running on :8790.

**Three plan assumptions corrected** (see Blocked/`worklog.md` for what this changes)

1. The **VCC-CPLD dataset does not exist** on Zenodo — substituted, `ADR-0003`.
2. **Named specialist subagents are not a TrueForge feature** — `ADR-0004`.
3. There is **no configurable local sandbox** — Daytona is the only provider, and skills need it.

## In flight

- Nothing being actively edited. PR open with all of the above; awaiting the idea.

## Blocked

1. **The ColdCall idea itself** (`Q-0001`, `VISION.md`) — Mulaydm10 is supplying it.
   **Read this before trusting anything cold-chain-shaped in the repo:** the supplied tech stack
   named cold-chain telemetry, MKT maths and a quarantine write, so a working mission was
   inferred from it in order to verify the setup against something concrete. That mission is
   **provisional, not agreed** — `VISION.md` is deliberately still `TODO`, and the two places
   that encode the assumption (`skills/coldchain-sop/SKILL.md` and `agents/coldcall.agent.json`)
   both carry a banner saying so. Confirm, amend or discard it when the thesis lands; tracked as
   `Q-0009`. `DEMO-0001` waits on the same answer.
2. **Supabase and Stripe need one browser click each** (`Q-0008`). Both are registered with the
   correct config and returning valid authorize URLs, but they authenticate by **OAuth (`dcr`)**,
   not by an API token — there was never a token to generate. Someone must click Connect in
   Settings → Connectors and log in; Supabase needs a project, Stripe needs test mode. Until
   then the full `coldcall` agent will not create, because its manifest references both.
3. **Which product label to judge against** (`Q-0007`) — the verified dataset is ambient
   (~22–30 °C), so a 2–8 °C label quarantines everything trivially while a real 15–25 °C
   controlled-room-temperature label gives a genuine spread. Decision shapes the demo.

## Deferred backlog (scheduled, not blocked)

Work Mulaydm10 has explicitly parked. Not blockers — do not report these as blocking, and do
not do them unprompted.

| Item | What it needs | Why it was deferred | Blocks |
|---|---|---|---|
| **Supabase connector** | One browser login: Settings → Connectors → supabase → Connect. Needs a Supabase project. It is **OAuth (`dcr`), not an API token** — there is no token to generate. | Deferred by Mulaydm10 2026-08-27; not on the critical path until the idea lands | Creating the full `coldcall` agent (its manifest references supabase) |
| **Stripe connector** | Same, in **test mode only**. Also OAuth, not a token. | Same | Same |
| **San Francisco day** | Separate Luma registration, https://luma.com/agent-harness | Optional; 2026-08-29, attendee-only OpenAI credits | Nothing |
| **Blog post** | Publish anywhere, link in submission | Optional prize (Keychron) | Nothing |
| **Star TrueForge repo** | https://github.com/truefoundry/trueforge — 10 seconds | Free draw entry (MX Master 3), no project needed | Nothing |

## Next intended step

1. Mulaydm10: drop `OPENAI_API_KEY` and `DAYTONA_API_KEY` into `.env`, then
   `./scripts/setup_trueforge.sh`. That converts the harness from configured to *working*.
2. Mulaydm10: supply the idea → `VISION.md`, then `DEMO-0001`.
3. Then: first end-to-end run of the agent against the replayed telemetry, filmed.

## Latest experiment

`EXP-0008` — the whole judged path verified end to end on Daytona: remote Linux microVM,
sandboxed execution, git skill mounted from GitHub. See `experiments/experiment_log.md`.

## Work claims

Claim a surface before starting on it; release it here the moment you yield. An agent that
finishes a unit of work updates this table (and the sections above) before stopping — see
`AGENTS.md` for the full protocol.

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| _(none claimed)_ | — | — | — |
