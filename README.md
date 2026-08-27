# tru

TODO(Mulaydm10): real event/project name goes here once known. This is an agentic-hackathon
repo, worked concurrently by humans and AI agents under deadline pressure. Every file here
exists to serve one of two goals: (1) an agent picking this repo up cold can reconstruct full
project state without asking a human, or (2) a human under deadline can find the one thing they
need in under 15 seconds. If a file doesn't serve one of those, it shouldn't be here — flag it.

## Start here

Cold-start entry point: **`CLAUDE.md`** (Claude Code agents) / **`AGENTS.md`** (any other agent
framework — the two are kept consistent). Paste-ready onboarding prompt for a brand-new agent:
**`notes/ai_onboarding_prompt.md`**.

## Read order

1. `CLAUDE.md` — entry point, rules, ID scheme
2. `STATE.md` — what's true right now
3. `VISION.md` — the thesis (LOCKED)
4. `COMPETITION.md` — event facts: deadline, rubric, hard rules (LOCKED)
5. `GOVERNANCE.md` — who owns what
6. `AGENTS.md` — multi-agent concurrency rules
7. Recent `worklog.md` entries
8. `experiments/experiment_log.md`

## Repo map

| Path | What it is |
|---|---|
| `CLAUDE.md` | Cold-start entry point (Claude Code) |
| `AGENTS.md` | Cold-start entry point (vendor-neutral) + concurrency rules |
| `STATE.md` | Live snapshot — overwritten, not append-only |
| `worklog.md` | Append-only dated + timestamped history |
| `VISION.md` | LOCKED — the thesis |
| `COMPETITION.md` | LOCKED — event facts: deadline, rubric, roster, hard rules |
| `DEMO.md` | The demo script judges will see — must stay runnable |
| `GOVERNANCE.md` | Locking rules + audit table |
| `research/` | Prior art + open questions (`Q-####`) |
| `design/decisions/` | ADRs (`ADR-####`), including the open stack decision |
| `experiments/` | Experiment log (`EXP-####`) |
| `notes/` | Onboarding prompt, glossary, judging-rubric alignment |
| `submissions/` | Staged deliverables (repo link / demo video / devpost link) |
| `tests/` | Test conventions — no baseline yet, see `tests/README.md` |
| `logs/`, `scratch/` | Gitignored working directories |

## Quickstart

TODO(Mulaydm10) — pending stack selection (`design/decisions/ADR-0002-stack-selection.md`,
`Q-0002`). There is no build/run/test command yet; see `CLAUDE.md`'s "Canonical commands"
section, which must be filled in the same change that resolves ADR-0002.

## End-of-session checklist

- [ ] `STATE.md` reflects current reality
- [ ] `worklog.md` has a dated + timestamped entry
- [ ] New experiments logged in `experiments/experiment_log.md`
- [ ] LOCKED-file edits logged in `GOVERNANCE.md`'s audit table
- [ ] Work claims in `STATE.md` released
