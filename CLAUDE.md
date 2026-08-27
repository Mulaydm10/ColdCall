# ColdCall — cold-start entry point

Event: **The Agent Harness Hackathon** (WeMakeDevs × TrueFoundry × Qodo) — full facts in
`COMPETITION.md`. Project: **ColdCall** — what it does is TODO(Mulaydm10), the idea is pending.
This is an **agentic hackathon** repo worked by humans and AI agents concurrently, under
deadline pressure. If you are an agent picking this up cold, read this file fully, then follow
the read order below. Do not ask a human anything this repo can already answer you.

## Read order (cold agent)

1. `CLAUDE.md` (this file)
2. `STATE.md` — what's true right now (overwritten every session)
3. `VISION.md` — the thesis (LOCKED)
4. `COMPETITION.md` — event facts: deadline, rubric, hard rules (LOCKED)
5. `GOVERNANCE.md` — who owns what, audit trail
6. `AGENTS.md` — concurrency rules for multi-agent work in this repo
7. Recent tail of `worklog.md` — how we got to the current STATE
8. `experiments/experiment_log.md` — what's been tried

## STATE vs worklog — the tie-break rule

`STATE.md` is a live snapshot, overwritten every session. `worklog.md` is append-only dated
history, never edited. **If they disagree about what is true right now, STATE.md wins;
worklog.md explains how we got here.**

## Governance in one paragraph

Main Agent (sole authority over LOCKED files): **Mulaydm10**. A LOCKED file opens with the
banner `> **LOCKED governing file.** Do not edit in place. See \`GOVERNANCE.md\`.` — never edit
one directly; propose the change and let the Main Agent apply it, logging the edit as a row in
`GOVERNANCE.md`'s audit table. `CLAUDE.md` and `STATE.md` are deliberately **not** locked — see
`GOVERNANCE.md` for why.

## Stable ID scheme

One scheme, used everywhere, so `grep -rn '<ID>' .` recovers a thing's full trace:

- `ADR-####` — design/stack decisions, in `design/decisions/`
- `Q-####` — open questions, in `research/open_questions.md`
- `EXP-####` — experiments/spikes, in `experiments/experiment_log.md`
- `DEMO-####` — demo-path scenarios, in `DEMO.md`

## Where the code lives

Public repo (open source is a submission requirement): **https://github.com/Mulaydm10/ColdCall**
(MIT). `main` is the merge target; nothing lands on it except through a Qodo-reviewed PR.

## Canonical commands

**The harness (mandatory, works today):**

```sh
npx @truefoundry/trueforge      # standalone; needs Node 22+ (this machine: 26.5.0)
                                # → http://localhost:8790, API docs at /api/v1/docs
```

Verified running as v0.1.4 on 2026-08-27 (`EXP-0001`). SQLite-backed, no account, nothing to
clone. Do **not** use the `docker compose` route — Docker is not installed here and standalone
is sufficient.

**Project build/test commands: TODO(Mulaydm10) — pending stack selection**
(`design/decisions/ADR-0002-stack-selection.md`, `Q-0002`; its options are now narrowed by
TrueForge being Node/TS). This repo intentionally has no `package.json` or `pyproject.toml`
yet — do not add one outside of finalizing that ADR. **Whoever resolves ADR-0002 must, in the
same change: fill in this section with the real setup/test/lint commands, AND land a green
smoke test.** Until then there is no runnable test baseline — see `tests/README.md`.

**Environment rule — nothing global, ever:**

- **Python → `uv`, in a project-local virtual environment.** `uv venv` + `uv add` / `uv run`.
  Never `pip install` globally or into the system/homebrew interpreter. One-off tools: `uvx`.
- **Node → project-local.** `npx` or a devDependency; never `npm install -g`.
- If a command in this file ever needs a global install to work, the command is wrong.

## Hard rules

### Event rules that bind every commit (from `COMPETITION.md`)

- **Every substantive change goes through a GitHub pull request reviewed by Qodo before merge.
  Direct pushes to `main` do not count as reviewed work** and are worth zero to the judges.
  Branch → PR → Qodo review (`/agentic_review` if it doesn't fire) → fix every valid High
  finding or dismiss it in-thread with a reason → push → follow-up review → a human merges.
- **The agent must run on TrueForge, visibly.** If a change would work just as well behind a
  plain chat box, it is the wrong change.
- **AI-assistant use must be disclosed** in the README, and every participant must be able to
  explain the architecture and the technical decisions. Do not build anything the team cannot
  explain — that is a stated rejection criterion, not a style note.
- **Nothing the agent touches may be someone else's to touch**; no keys or personal data in the
  repo or the demo video.

### Repo rules

- Never edit a LOCKED file in place. Propose the change; Main Agent applies it + logs it.
- `STATE.md` is overwritten, not appended to. `worklog.md` entries are dated **and timestamped**
  (hackathon history moves hourly, not daily) and are never edited after the fact.
- Before yielding a unit of work, update `STATE.md` (see `AGENTS.md` for the claim protocol).
- Never invent a thesis, rubric detail, or result to fill a gap — leave it `TODO(Mulaydm10)`.
- `DEMO.md` must stay runnable at all times once a demo path exists — it is what judges see.

## Vendor-neutral twin

`AGENTS.md` carries the same concurrency rules for non-Claude agent frameworks. The two files
must stay consistent; this file points to it rather than restating its content.

## End-of-session checklist

- [ ] `STATE.md` reflects current reality (overwrite, don't append)
- [ ] `worklog.md` has a dated + timestamped entry for this session
- [ ] Any new experiment has a row in `experiments/experiment_log.md`
- [ ] Any LOCKED-file edit is logged in `GOVERNANCE.md`'s audit table
- [ ] Any work claim in `STATE.md` you finished is released
