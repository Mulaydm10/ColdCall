# STATE — live snapshot (overwritten every session, NOT locked)

This file is a snapshot of *right now*, not a history. It is overwritten wholesale each time
someone updates it — never appended to. For history, see `worklog.md`. **Tie-break rule: if
this file and `worklog.md` disagree about what is currently true, this file wins; the worklog
explains how we got here.**

Last updated: 2026-08-27 07:45 CEST — by Mulaydm10 (+ Claude, acting on their behalf):
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
2. **OpenAI API key** (`Q-0003`) — the harness runs but cannot think. One line in `.env`.
3. **Daytona API key** (`Q-0004`) — blocks *two* judged features at once: sandboxed execution
   is a scored criterion, and skills refuse to load without a sandbox. Highest-value key.
4. **Supabase / Stripe test-mode / GitHub tokens** (`Q-0008`) — the three real integrations.
   None can be created by an agent.
5. **Which product label to judge against** (`Q-0007`) — the verified dataset is ambient
   (~22–30 °C), so a 2–8 °C label quarantines everything trivially while a real 15–25 °C
   controlled-room-temperature label gives a genuine spread. Decision shapes the demo.

## Next intended step

1. Mulaydm10: drop `OPENAI_API_KEY` and `DAYTONA_API_KEY` into `.env`, then
   `./scripts/setup_trueforge.sh`. That converts the harness from configured to *working*.
2. Mulaydm10: supply the idea → `VISION.md`, then `DEMO-0001`.
3. Then: first end-to-end run of the agent against the replayed telemetry, filmed.

## Latest experiment

`EXP-0004` — full pipeline on real telemetry: 3 818 readings, 6 devices, a genuine
release/review/quarantine spread against a real label. See `experiments/experiment_log.md`.

## Work claims

Claim a surface before starting on it; release it here the moment you yield. An agent that
finishes a unit of work updates this table (and the sections above) before stopping — see
`AGENTS.md` for the full protocol.

| Surface | Claimed by | Since | Status |
|---|---|---|---|
| _(none claimed)_ | — | — | — |
