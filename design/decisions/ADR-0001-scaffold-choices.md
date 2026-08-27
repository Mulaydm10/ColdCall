# ADR-0001: This scaffold's own governance and file structure

Status: Accepted
Owner: Mulaydm10
Date: 2026-08-27

## Context

This repo will be worked by both humans and AI agents, concurrently, under hackathon deadline
pressure. Two requirements had to be satisfied simultaneously: an agent picking the repo up
cold must be able to reconstruct full project state without asking a human, and a human under
deadline must be able to find the one thing they need in under 15 seconds. A scaffold with
unused directories trains agents to ignore structure, so the design also had to prune
aggressively rather than including every plausible folder.

## Options considered

- **Reuse the ML-competition scaffold (`comp-setup`) as-is** — has the LOCKED-file/governance
  pattern and onboarding-prompt habit already, but is hardcoded to leaderboard/task/submission
  artifacts and a fixed platform+GPU target, none of which fit an agentic software hackathon
  with an undecided stack.
- **Reuse the research-project scaffold (`research-setup`) as-is** — has the three-piece
  cold-start pattern (`CLAUDE.md` / `STATE.md` / `worklog.md`) and the stable-ID-scheme habit,
  but is framed around long-horizon inquiry (papers, experiments-as-science) rather than a
  fixed-deadline build-and-demo event.
- **Blend both, add a hackathon-specific layer, hand-write every file** — take the cold-start
  three-piece pattern and ID scheme from research-setup, the LOCKED-banner/audit-table and
  onboarding-prompt habit from comp-setup, and add what neither has: `COMPETITION.md` as the
  single source of truth for event facts, `DEMO.md` as the rehearsed judge-facing script,
  `AGENTS.md` for explicit multi-agent concurrency rules, and hourly-timestamped worklog entries
  instead of daily ones.

## Decision

Blend both, as the third option. Neither existing blueprint fits an agentic hackathon on its
own — one over-fits to ML competitions, the other to open-ended research — and hand-writing
avoids the CLI unwinding it would otherwise take to strip GPU/platform/task-numbering
assumptions back out.

## Consequences

- `CLAUDE.md` / `STATE.md` / `AGENTS.md` / `DEMO.md` are deliberately **not** LOCKED (see
  `GOVERNANCE.md`) because their entire value is staying current; everything else structural
  (`VISION.md`, `COMPETITION.md`, the three `*/README.md` files, the onboarding prompt) is
  LOCKED with edits routed through the Main Agent and logged in the audit table.
- The stack is explicitly left undecided (`ADR-0002`) — this repo has no `pyproject.toml`,
  `package.json`, `Makefile`, or language-specific `src/` tree yet, and none should be added
  outside of resolving that ADR.
- `ideas/` was deliberately omitted — the project idea is treated as decided (even though its
  content is still `TODO`), so ideation scaffolding would be dead weight.
- No `data/`, `models/`, `notebooks/` — those presume an ML pipeline this hackathon may not
  have; add them later only if the chosen idea/stack actually needs them.

## Related

`Q-0001`, `Q-0002`, `ADR-0002`
