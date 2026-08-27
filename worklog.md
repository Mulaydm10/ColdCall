# Worklog — append-only dated + timestamped history

Rules: append only, never edit or delete a past entry, never reorder. Newest entry at the
bottom. Every entry is dated **and timestamped** (hackathon history moves hourly, not daily) —
"2026-08-27 05:51 CEST", not just "2026-08-27". This is the "how we got here" log; for "what's
true right now" see `STATE.md` — if the two ever disagree, `STATE.md` wins.

Entries should cite `EXP-####` / `ADR-####` / `Q-####` / `DEMO-####` ids where relevant so
`grep -rn '<ID>' .` recovers the full trace.

---

### 2026-08-27 05:51 CEST — Mulaydm10 (scaffold)

Initial repo scaffold created: governance (`GOVERNANCE.md`), cold-start entry point
(`CLAUDE.md`), live snapshot (`STATE.md`), vision placeholder (`VISION.md`, registers `Q-0001`),
competition-facts placeholder (`COMPETITION.md`), demo script skeleton (`DEMO.md`),
agent-concurrency rules (`AGENTS.md`), ADR log with `ADR-0001` (scaffold's own choices, Accepted)
and `ADR-0002` (stack selection, Proposed, registers `Q-0002`), plus research/experiments/notes/
tests/submissions/logs/scratch scaffolding. No project work has started; event name, thesis, and
stack are all still `TODO(Mulaydm10)`.

---

### 2026-08-27 06:25 CEST — Mulaydm10 + Claude (event research + harness bring-up)

**Event identified and documented.** Read the official overview, rules, schedule and resources
pages plus the kick-off guide, and filled `COMPETITION.md` (LOCKED — applied on the Main Agent's
instruction, logged in `GOVERNANCE.md`'s audit table). It is **The Agent Harness Hackathon**
(WeMakeDevs × TrueFoundry × Qodo), window 2026-08-24 08:00 → **2026-08-30 20:00 London
(19:00 UTC)**. At time of writing: **~3d 14h remaining, day 4 of 7**. $10k in prizes across
three judged tracks (one per team max), six equally weighted judging criteria.

**Two hard gates found**, both now written into `CLAUDE.md`'s hard rules:
1. The agent **must run on TrueForge** and a judge must see the harness doing real work — a
   real MCP tool reached, agent-written code run in a sandbox, and a pause for human approval
   before anything irreversible. "If it would work just as well as a chat box, change the
   project."
2. **Every substantive change must land through a Qodo-reviewed pull request**; direct pushes
   to `main` do not count as reviewed work, and judges inspect the trail across the build, not
   just the final merge. This is our biggest exposure — we are on day 4 with zero PRs, no
   remote, and Qodo not installed (`Q-0005`).

**`EXP-0001` — TrueForge booted locally and works.** `npx @truefoundry/trueforge` brings up
v0.1.4 standalone on http://localhost:8790 (HTTP 200), SQLite-backed, auth disabled, API docs
at `/api/v1/docs`. Node 26.5.0 satisfies the Node 22+ floor. It also reports a **local sandbox
fallback** on darwin alongside the documented Daytona provider — raised as `Q-0004` since the
sandbox beat is judged. Docker route skipped (not installed, not needed).

**`ADR-0002` narrowed but not closed.** TrueForge being Node/TS with `agent.json` agents, plus
the Best UI track needing our own frontend, pushes the answer toward TypeScript end to end;
Python's free slot is a custom MCP server. Final call waits on the idea (`Q-0001`).

**Standing environment rule recorded** (`CLAUDE.md` → Canonical commands): all Python runs under
**`uv` in a project-local virtual environment**, Node stays project-local, nothing installed
globally.

Also: rubric mirrored into `notes/judging_alignment.md` with a second table for the non-scored
submission gates (public repo, ~3-min video, `## Qodo Code Review Evidence` README section,
**AI-assistant-use disclosure**) and a third for the cheap optional prizes; new questions
`Q-0003`–`Q-0006` registered; `DEMO.md` given the three non-negotiable on-camera beats;
`.gitignore` extended for `.playwright-mcp/`.

Still blocked on Mulaydm10 for: the project idea (`Q-0001`), a public GitHub repo + Qodo install
(`Q-0005`), a model provider key (`Q-0003`), a Daytona key (`Q-0004`), and roster/registration
confirmation (`Q-0006`).
