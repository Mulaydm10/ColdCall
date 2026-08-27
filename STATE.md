# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 10:40 CEST — by Mulaydm10 (+ Claude, acting on their behalf):
**the inferred cold-chain mission was cleared** (`ADR-0006`) so it cannot bias the real thesis;
PR #4's Qodo review resolved (0 bugs on re-review) and awaiting merge.

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
  runs against a stock interpreter. **Empty of domain logic as of `ADR-0006`** — see the reset
  below.
- **2 tests green** (`uv run pytest`), ruff clean. Down from 47: 45 of those tested the inferred
  mission and went with it. The two that remain prove the toolchain and guard the reset.
- `agents/coldcall.agent.json` — platform wiring only. Approval gates on every MCP server;
  Stripe gated at `@all`. Its `instructions` are deliberately mission-free.
- `skills/repo-evidence/SKILL.md` — replaces `coldchain-sop`. Domain-neutral, so the proven
  git-backed skill mount survives the reset. **Must be re-registered against `main` after the
  reset PR merges** — TrueForge fetches skills from GitHub at the registered ref, never from
  the working tree.
- `scripts/setup_trueforge.sh` — idempotent (PUT throughout), `--dry-run`, names exactly which
  keys are missing. `scripts/verify_apis.sh` — **7/7 sources pass right now**.
- TrueForge v0.1.4 running on :8790.

**The inferred mission was cleared** (`ADR-0006`)

Before supplying the idea, Mulaydm10 asked whether the repo carried assumptions about it. It
carried them in twenty files, so they were removed: the MKT/stability maths, the telemetry
replay, their 45 tests, the `coldchain-sop` skill, and the agent's instructions. The platform —
harness, sandbox, connectors, Qodo loop, scripts, toolchain — is domain-neutral and untouched.
`ADR-0006` records what went, what stayed, and the one command that restores it all. Honest
caveat recorded there: "cold-chain" was traceable to the tech stack Mulaydm10 themselves
supplied, not purely to the project name; what was invented on top of it was the *mission*.

**Three plan assumptions corrected** (see Blocked/`worklog.md` for what this changes)

1. The **VCC-CPLD dataset does not exist** on Zenodo — substituted, `ADR-0003`.
2. **Named specialist subagents are not a TrueForge feature** — `ADR-0004`.
3. There is **no configurable local sandbox** — Daytona is the only provider, and skills need it.

## In flight

- Nothing being actively edited. **Two PRs open, both awaiting a human merge:** #4 (docs;
  re-review returned 0 bugs) and #5 (the `ADR-0006` mission reset, based on #4's branch rather
  than `main` so the diff stays clean — merge #4 first). Awaiting the idea.

## Blocked

1. **The ColdCall idea itself** (`Q-0001`, `VISION.md`) — Mulaydm10 is supplying it. This is now
   the **only** thing blocking product work. The repo no longer encodes a guess at it: the
   inferred cold-chain mission was removed under `ADR-0006`, and `Q-0009` is closed as discarded.
   Do not re-derive a mission from the tools, APIs or dataset that are wired up — they say what
   is possible, never what is wanted. `DEMO-0001` waits on the same answer.
2. **Which product label to judge against** (`Q-0007`) — the verified dataset is ambient
   (~22–30 °C), so a tight refrigerated threshold flags every leg trivially while a realistic
   ambient one gives a genuine spread. **Only live if the real thesis turns
   out to use that dataset** — it was carried over with `ADR-0003` and may well be moot.

**Not on this list, deliberately:** the Supabase and Stripe connector logins (`Q-0008`).
Mulaydm10 parked them — see the Deferred backlog below. They gate creating the *full* `coldcall`
agent, whose manifest references both, but nothing on the critical path is waiting on them today.

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

The harness is already configured and working — `OPENAI_API_KEY` and `DAYTONA_API_KEY` are in
`.env`, `./scripts/setup_trueforge.sh` reports 4 configured / 0 failed, and a real agent turn has
run on a Daytona microVM. **Do not repeat that setup.** Re-run the script only to re-verify after
a machine restart; it is idempotent.

1. Merge PR #4 (re-review: **0 bugs**), then PR #5.
2. Mulaydm10: supply the idea → `VISION.md`, then `DEMO-0001`.
3. Re-register the `repo-evidence` skill against `main`, and write the agent's real
   instructions once the thesis exists.
4. Then: first end-to-end run of the agent, filmed.

## Latest experiment

`EXP-0008` — the whole judged path verified end to end on Daytona: remote Linux microVM,
sandboxed execution, git skill mounted from GitHub. See `experiments/experiment_log.md`. Still
valid after the reset: every capability it proved is platform, not mission.

## Work claims

Claim a surface before starting on it; release it here the moment you yield. An agent that
finishes a unit of work updates this table (and the sections above) before stopping — see
`AGENTS.md` for the full protocol.

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| _(none claimed)_ | — | — | — |
