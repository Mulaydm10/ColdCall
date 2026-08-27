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

---

### 2026-08-27 06:35 CEST — Mulaydm10 + Claude (repo live, PR trail started)

Project named **ColdCall** by the Main Agent. Public repo created at
**https://github.com/Mulaydm10/ColdCall** (MIT, public — the open-source submission requirement),
`main` pushed, and **PR #1** opened from `docs/event-facts` carrying the event-facts work from
the previous entry. The review trail now exists on day 4 rather than day 7.

Deliberate: the docs work was committed to a branch *before* the remote existed, so nothing has
ever been pushed straight to `main` on the remote. `main` holds only the two original scaffold
commits.

README gained the two sections the rules require and neither of which can be back-filled at the
end credibly: `## Qodo Code Review Evidence` (merged-PR link marked TODO until PR #1 lands) and an
**AI assistance disclosure** naming Claude Code and Qodo, with the note that AI-authored commits
carry a `Co-Authored-By` trailer so the split is visible in `git log`. Glossary gained ColdCall,
TrueForge, Qodo and "the three beats"; the LOCKED onboarding prompt now names the project and
points at the repo (logged in `GOVERNANCE.md`).

Blocking on Mulaydm10, in priority order: **install Qodo on the repo** (`Q-0005`, only a human
with repo admin can), the ColdCall idea (`Q-0001`), a model provider key (`Q-0003`), a Daytona
key or a verdict on the local sandbox fallback (`Q-0004`), roster + registration (`Q-0006`).

---

### 2026-08-27 06:55 CEST — Mulaydm10 + Claude (Qodo live, first review resolved)

**Qodo installed** (`Q-0005` resolved). Mulaydm10 signed in and authorised the GitHub App;
installation `Mulaydm10 | Qodo-code-review` reports **Connected / Healthy** with the code-review
toggle on for `ColdCall`. Access was granted across all 30 repos on the account rather than
scoped to this one — deliberate, reversible at github.com/settings/installations, and noted here
so nobody is surprised later.

**First review on PR #1** (triggered with `/agentic_review`, since the PR predated the install):
**4 findings, all Medium, no High.** All four were valid and **all four were fixed rather than
dismissed**:

1. `COMPETITION.md` described the San Francisco day (2026-08-29) in the past tense on 2026-08-27
   — a real factual error that could have cost us an in-person option that is *still two days
   away*. Rewritten as upcoming, with the separate Luma registration called out. LOCKED-file
   edit, logged in `GOVERNANCE.md`.
2. `notes/judging_alignment.md` still marked the public-repo gate "Missing" after this very PR
   created the repo. Now **Done**, pointing at the real URL.
3. Same table marked the AI-assistance disclosure "Missing" while the same PR added it. Now
   **Done**.
4. `README.md` claimed unconditionally that Qodo reviews every PR while `STATE.md` said it was
   not installed. Split into **Policy** (what we always do) and **Status** (what is true today) —
   which is the honest shape regardless of install state, and worth keeping.

Worth recording: three of the four were *staleness* bugs — docs describing a world that changed
while the PR was open. That is the failure mode this repo's STATE-vs-worklog split exists to
prevent, and Qodo caught it in the one place the split doesn't reach: a table inside a PR.
