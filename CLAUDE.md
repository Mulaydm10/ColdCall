# tru — cold-start entry point

TODO(Mulaydm10): real event/project name. This is an **agentic hackathon** repo worked by
humans and AI agents concurrently, under deadline pressure. If you are an agent picking this
up cold, read this file fully, then follow the read order below. Do not ask a human anything
this repo can already answer you.

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

## Canonical commands

**TODO(Mulaydm10) — pending stack selection.** The stack (Python / TypeScript-Next.js / both)
is explicitly undecided; see `design/decisions/ADR-0002-stack-selection.md` (open, `Q-0002`).
This repo intentionally has no `pyproject.toml`, `package.json`, or `Makefile` yet — do not add
one outside of finalizing that ADR. **Whoever resolves ADR-0002 must, in the same change: fill
in this section with the real setup/test/lint commands, AND land a green smoke test.** Until
then there is no runnable test baseline — see `tests/README.md`.

## Hard rules

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
