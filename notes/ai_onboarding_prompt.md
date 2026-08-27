> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# AI onboarding prompt (paste-ready)

Paste this verbatim to any new AI agent (Claude Code or otherwise) joining this repo cold.

---

You're joining **ColdCall**, our entry to The Agent Harness Hackathon (see `COMPETITION.md`
for the event facts and `https://github.com/Mulaydm10/ColdCall` for the public repo).
Humans and AI agents work in it concurrently under a hard deadline. Before doing anything:

1. Read `CLAUDE.md` (or `AGENTS.md` if you're not Claude Code) in full — it's short by design
   and is the map to everything else.
2. Read `STATE.md` — the live snapshot of what's true right now. It's overwritten each session,
   not appended to; trust it over old context.
3. Read `VISION.md` and `COMPETITION.md` (both LOCKED) — the thesis and the event facts. If
   either is still full of `TODO(Mulaydm10)`, say so rather than inventing content to fill it.
4. Read `GOVERNANCE.md` to learn which files are LOCKED (edit only via the Main Agent,
   `Mulaydm10`, with every edit logged in its audit table) versus append-only
   (`worklog.md`, `research/prior_art.md`, `research/open_questions.md`,
   `experiments/experiment_log.md`) versus freely live (`STATE.md`, `AGENTS.md`, `DEMO.md`).
5. Skim the tail of `worklog.md` for recent history and `experiments/experiment_log.md`
   (`EXP-####`) for what's already been tried.
6. Before starting non-trivial work, check the Work claims table in `STATE.md` and add your own
   claim — see `AGENTS.md` for the full concurrency protocol.
7. Use the ID scheme everywhere you reference something: `ADR-####` for decisions, `Q-####` for
   open questions, `EXP-####` for experiments, `DEMO-####` for demo scenarios. It's what makes
   `grep -rn '<ID>' .` recover a full trace later.
8. Before you stop — for any reason, including a blocker, not just task completion — update
   `STATE.md` to reflect current reality and append a dated + timestamped entry to `worklog.md`.

If the stack is still undecided (check `design/decisions/ADR-0002-stack-selection.md`), do not
assume one. There is no `pyproject.toml`/`package.json`/`Makefile` yet on purpose.
