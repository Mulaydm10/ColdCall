# ColdCall

**ColdCall** — our entry to **The Agent Harness Hackathon** (WeMakeDevs × TrueFoundry × Qodo,
2026-08-24 → 2026-08-30). Event facts live in `COMPETITION.md`. What ColdCall actually does is
TODO(Mulaydm10) — the idea is being supplied; this repo is the infrastructure it lands into.
Worked concurrently by humans and AI agents under deadline pressure. Every file here
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

Start the agent harness every submission must run on (needs Node 22+):

```sh
npx @truefoundry/trueforge   # → http://localhost:8790
```

Then add a model provider (Settings → Models), connect tools (Settings → Connectors), and a
sandbox (Settings → Sandbox providers).

Project build/run/test commands: TODO(Mulaydm10) — pending stack selection
(`design/decisions/ADR-0002-stack-selection.md`, `Q-0002`). See `CLAUDE.md`'s "Canonical
commands", which must be filled in the same change that resolves ADR-0002. Any Python work runs
under **`uv` in a project-local venv** — never a global install.

## Qodo Code Review Evidence

> Required by the hackathon: see `COMPETITION.md` → "Required process". This section must
> contain a link to at least one **merged** pull request with meaningful ColdCall code, one or
> two sentences on what Qodo surfaced and what we changed or intentionally dismissed, and a PR
> history showing the completed review, our decisions, and a follow-up review against the final
> code. The public PR link is the required evidence — screenshots cannot replace it.

- **Representative merged PR:** TODO(Mulaydm10) — fill once PR #1 is reviewed and merged.
- **What Qodo surfaced, and what we did:** TODO(Mulaydm10).
- **PR history:** https://github.com/Mulaydm10/ColdCall/pulls?q=is%3Apr

Every substantive change in this repo goes through a branch → pull request → Qodo review →
follow-up review → human merge. Direct pushes to `main` do not count as reviewed work.

## AI assistance disclosure

Required by the hackathon rules (AI coding assistants are allowed, but their use must be
disclosed, and every participant must be able to explain the architecture and the technical
decisions behind the submission).

- **Claude Code (Anthropic, Opus 5)** is used throughout as a pair-programmer and for repo
  research, documentation, and scaffolding. AI-authored commits carry a
  `Co-Authored-By: Claude` trailer, so the split is visible in `git log`.
- **Qodo** reviews every pull request, as the event requires.
- Architecture and technical decisions are recorded by a human in `design/decisions/`
  (`ADR-####`) and are owned by the team, not by the assistant.

## End-of-session checklist

- [ ] `STATE.md` reflects current reality
- [ ] `worklog.md` has a dated + timestamped entry
- [ ] New experiments logged in `experiments/experiment_log.md`
- [ ] LOCKED-file edits logged in `GOVERNANCE.md`'s audit table
- [ ] Work claims in `STATE.md` released
