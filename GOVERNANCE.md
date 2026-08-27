# GOVERNANCE

## Main Agent

**Mulaydm10** holds sole authority over LOCKED files: applying edits to them, and approving any
change another human or agent proposes against one. No other agent — human or AI — edits a
LOCKED file directly.

## Team

TODO(Mulaydm10) — full roster lives in `COMPETITION.md` (single source of truth for event/team
facts); this file only states who holds locked-file authority, not the full team list.

## File categories

**LOCKED** (banner + edits only via Main Agent + every edit logged in the audit table below):

- `VISION.md`
- `COMPETITION.md`
- `research/README.md`
- `design/README.md`
- `experiments/README.md`
- `logs/README.md`
- `notes/ai_onboarding_prompt.md`
- `tests/README.md`

**Deliberately NOT locked** — their value depends on staying current, which locking would defeat:

- `CLAUDE.md` — auto-loaded cold-start entry point; must always reflect the live scheme.
- `STATE.md` — a live snapshot by design; overwritten every session.
- `AGENTS.md` — operational concurrency rules; evolves as the team's working pattern does.
- `DEMO.md` — the demo script; must track whatever the product actually does, live, at all times.

Their absence from the LOCKED list above is intentional, not an oversight.

**Append-only** (never edit or delete a past entry; new content goes at the end):

- `worklog.md`
- `research/prior_art.md`
- `research/open_questions.md`
- `experiments/experiment_log.md` (header/schema is fixed; only rows are appended)

## Audit table

Every LOCKED-file edit — **including this scaffold's own initial authorship** — is logged here.
Initial authorship by the Main Agent (or an agent acting on their behalf) is expected and
correct, not a violation; logging it models the right behavior for whoever edits next.

| Date | File | Change | Author | Notes |
|---|---|---|---|---|
| 2026-08-27 | `VISION.md` | Initial authorship (scaffold, all-TODO) | Mulaydm10 | Registers Q-0001 |
| 2026-08-27 | `COMPETITION.md` | Initial authorship (scaffold, all-TODO) | Mulaydm10 | Event facts pending |
| 2026-08-27 | `research/README.md` | Initial authorship (scaffold) | Mulaydm10 | Defines prior_art/open_questions rules |
| 2026-08-27 | `design/README.md` | Initial authorship (scaffold) | Mulaydm10 | Defines ADR process |
| 2026-08-27 | `experiments/README.md` | Initial authorship (scaffold) | Mulaydm10 | Defines EXP-#### log schema |
| 2026-08-27 | `logs/README.md` | Initial authorship (scaffold) | Mulaydm10 | Defines runtime-log convention |
| 2026-08-27 | `notes/ai_onboarding_prompt.md` | Initial authorship (scaffold) | Mulaydm10 | Paste-ready cold-start prompt |
| 2026-08-27 | `tests/README.md` | Initial authorship (scaffold) | Mulaydm10 | No baseline yet; pending ADR-0002 |
| 2026-08-27 | `COMPETITION.md` | Filled all event facts from official sources (deadline, TrueForge/Qodo requirements, rubric, tracks, hard rules) | Mulaydm10 (via Claude, on their behalf) | Replaces scaffold TODOs; sourced from event overview/rules/schedule/resources + kick-off guide |
