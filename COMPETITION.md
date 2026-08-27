> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# COMPETITION

This is the **single source of truth for event facts**. Every other file (README, DEMO.md,
notes/judging_alignment.md, STATE.md) links here rather than restating any of these fields —
if you catch a date, rubric weight, or rule duplicated elsewhere, delete the duplicate and
replace it with a link to the relevant heading below.

Sourced 2026-08-27 from the official pages (overview / rules / schedule / resources) and the
official kick-off guide. Where a fact appears in more than one place and they agree, it is
stated once here.

## Event

- **Name:** The Agent Harness Hackathon ("Give AI models a License to act"; internal theme
  name "File TF-007", Bond-themed)
- **Host / organizer:** WeMakeDevs, in collaboration with **TrueFoundry** (main sponsor,
  agent harness) and **Qodo** (main sponsor, code review). OpenAI is model partner
  (SF-only credits).
- **Event page:** https://www.wemakedevs.org/hackathons/trueforge
  - Rules: https://www.wemakedevs.org/hackathons/trueforge/rules
  - Schedule: https://www.wemakedevs.org/hackathons/trueforge/schedule
  - Resources: https://www.wemakedevs.org/hackathons/trueforge/resources
  - Kick-off guide (read first): https://www.wemakedevs.org/blogs/agent-harness-hackathon-kick-off
- **Registration:** https://forms.gle/dNHFh7wH8uJj4bZH8 — free; the stream link and the
  submission form are delivered through it.
- **Help:** WeMakeDevs Discord https://discord.gg/wemakedevs · TrueForge issues
  https://github.com/truefoundry/trueforge/issues
- **Mode:** Online from anywhere. An optional in-person day ran in San Francisco on
  2026-08-29 (separate Luma registration; $50 OpenAI credits to attendees only).

## Deadline

- **Date:** 2026-08-30 (Sunday)
- **Time:** 20:00
- **Timezone:** **London (BST)** = **19:00 UTC** = 21:00 CEST (local time on this machine).

Event window opened 2026-08-24 08:00 London (07:00 UTC). Only other scheduled item:
a TrueFoundry live stream on LinkedIn, 2026-08-26 15:00 UTC (already passed).

`STATE.md`'s "Time remaining" line is computed from this section — update both together.

## Required technology (hard gate)

**The agent must run on TrueForge**, TrueFoundry's open-source agent harness. This is the
rule that decides whether a project qualifies at all: *"A judge has to be able to see the
harness doing real work rather than sitting under a thin wrapper around a model call."*
The organizers' own test: **if it would work just as well as a chat box, change the project.**

- Version verified running locally: **TrueForge v0.1.4** (standalone), 2026-08-27.
- Start: `npx @truefoundry/trueforge` → http://localhost:8790 (needs **Node.js 22+**;
  SQLite-backed, no account, nothing to clone). API docs at `/api/v1/docs`.
- Heavier route: `git clone git@github.com:truefoundry/trueforge.git && docker compose up`.
- Drivable three ways: **chat UI**, **HTTP API**, or a **TypeScript library**.
- An agent is a single **`agent.json`**: a model, its instructions, and the connectors it may use.
- Docs: https://trueforge.dev · models https://trueforge.dev/models#configuring-a-standard-provider
  · MCP https://trueforge.dev/mcp-servers
- Example agents to copy (ten in the cookbook):
  https://github.com/truefoundry/trueforge/tree/examples/agent-cookbook/examples
- **Model key is BYO** — any provider (OpenAI, Anthropic, Gemini, DeepSeek, any
  OpenAI-compatible endpoint). The $50 OpenAI credits were in-person SF only.
- **Sandbox provider: Daytona** (Settings → Sandbox providers, needs a Daytona API key).
  A local sandbox fallback also exists in standalone mode, but Daytona is the documented path.

### What the harness handles (the surface judges score you on using)

MCP connectors incl. OAuth + 40 built-in tools and web search · isolated **sandbox** for
agent-written code · **human approval pause** before sensitive actions · **subagents** ·
persistent sessions that survive reconnects/restarts · any model, switchable in the UI ·
git-backed `SKILL.md` **skills** · scales SQLite → Postgres+Redis.

### The three beats every submission must visibly show

1. A **real tool reached** through MCP — connected, not mocked.
2. **Agent-written code executing in the sandbox.**
3. A **pause for human approval** before anything irreversible.

## Required process: Qodo code review (applies to every submission)

Not just the code-quality track — **every** submission, solo or team.

- One teammate with repo admin: sign in at https://app.qodo.ai/signin → Integrations → SaaS →
  GitHub → Add installation → authorise the hackathon repo. One installation covers the whole
  team; teammates need no accounts. 14-day trial, no card. Free for open source.
- **Every substantive change goes through a GitHub pull request reviewed by Qodo before merge.
  Direct pushes to `main` do not count as reviewed work.**
- Loop: branch → PR → Qodo review (automatic; else comment `/agentic_review`) → fix every valid
  **High**-severity finding, or dismiss it *in the Qodo thread with a reason* → push → follow-up
  review → a human merges. Medium/Low are an engineering call.
- Optional helper: `npx skills add qodo-ai/qodo-skills/skills`, then the `qodo-pr-resolver`
  skill resolves findings from a coding agent.
- Docs: https://docs.qodo.ai/code-review/use-qodo-in-prs ·
  https://docs.qodo.ai/code-review/comment-anatomy · https://docs.qodo.ai/agent-skills
- **Judges may inspect other substantive merges to confirm Qodo review was part of the build
  rather than a one-time submission step.** The public PR link is the required evidence;
  screenshots cannot replace it.

## Submission format

Submitted through the event site by the deadline above. Every submission must include:

1. A **public, open-source source-code repository** (judges must be able to read *and run* it).
2. A **clear README with setup steps** that works on a stranger's machine.
3. A **demo video of about three minutes** showing the agent working.
4. A **short write-up** of what the agent does and how it uses TrueForge.
5. A **`## Qodo Code Review Evidence`** section in the README containing: a link to at least one
   representative **merged** PR with meaningful hackathon code; one or two sentences on what Qodo
   surfaced and what was changed or intentionally dismissed; and a PR history showing the
   completed review, the decisions, and a **follow-up review against the final code**.
6. A link to the blog post, if entering that prize.

`submissions/README.md` stages these deliverables.

## Judging rubric

**Six criteria, weighted equally** (the organizers state "the demo is scored as hard as the
code"). No published numeric weights beyond "equal", so each is treated as 1/6.

| Criterion | Weight | Notes |
|---|---|---|
| Potential impact | 1/6 | Does the agent do a clear, useful job someone would actually hand over? |
| Creativity and originality | 1/6 | An inventive job to give an agent, or an inventive way of doing it. |
| Technical excellence | 1/6 | Is the implementation complete, reliable, and well structured? |
| Use of sponsor tools | 1/6 | Is TrueForge *central* rather than a thin wrapper — and did Qodo review the PRs on the way there? |
| Control and safety | 1/6 | Does it run code somewhere safe and stop for a human before anything irreversible? |
| Presentation | 1/6 | Does the demo clearly explain the problem, the agent working, and where the harness fits? |

Mirrored into `notes/judging_alignment.md` against the artifact that satisfies each row.

## Tracks and prizes

$10,000 total. Every submission is automatically considered for all three judged tracks, but
**one team can win at most one track**. Nothing to opt into.

| Track | Prize | Awarded for |
|---|---|---|
| Double-O (TrueFoundry) | NVIDIA DGX Spark, $5,000 | **Best Use of TrueForge** — real MCP tools, sandboxed execution, human approvals, subagents, persistent sessions |
| Q Branch (Qodo) | Mac Mini, $1,000 | **Best Code Quality** — judged on the Qodo review trail; a repo a stranger could clone, understand, extend |
| Savile Row | Apple iPad **to every team member** | **Best UI** — shows what the agent is doing, what it waits on, what it did; asks before the irreversible step. Judged on the demo video and the running project, not a screenshot |
| Field report | Keychron keyboard (one writer) | **Best blog post** — publish anywhere, add the link to the submission |
| Radio traffic | Swag ×10 | Best social posts while building; tag WeMakeDevs, TrueFoundry, Qodo |
| Calling Card | Logitech MX Master 3 | Draw — **just star https://github.com/truefoundry/trueforge**, no project needed |
| Universal Exports | Job interview at TrueFoundry | Top projects; judges pass names on. Not conditional on winning a track |

## Team roster

TODO(Mulaydm10) — solo or up to 4 people; each participant may be on only one team.
Confirm the roster and whether registration (the Google Form above) has been completed.
Main Agent / locked-file authority is `Mulaydm10` — see `GOVERNANCE.md`.

## Hard rules

Full text: https://www.wemakedevs.org/hackathons/trueforge/rules — registering means agreeing
to these plus the WeMakeDevs Code of Conduct.

- **Free to enter**, online from anywhere. Solo or team of ≤4; one team per participant.
- **Must run on TrueForge** (see "Required technology" above) — the qualification gate.
- **Every substantive change through a Qodo-reviewed PR**; direct pushes to `main` don't count.
- **Must be open source** — a public repo judges can read and run.
- **Anything the agent touches has to be yours to touch.** Connect only tools, data, and
  accounts you own or have permission to use. Keep keys, private, personal, and
  login-protected information out of the repo *and* out of the demo video.
- **The project must be built during the window.** Discussing ideas, taking notes, planning
  architecture, and preparing diagrams beforehand is allowed; the *coding and design work*
  must happen between 2026-08-24 08:00 London and the deadline. Pre-existing code may not be
  the project itself.
- **Frameworks, open-source libraries, public APIs, templates, third-party tools, and publicly
  available assets are allowed.** Only original work completed during the hackathon is judged.
- **AI coding assistants are allowed, but their use must be disclosed.**
- **Participants must understand the submitted code** and be able to explain the agent, the
  architecture, and the technical decisions. Projects entirely AI-generated without meaningful
  participant contribution, verification, or technical understanding **may be rejected**.
- IP belongs to the participant or team that created it; teams should agree ownership internally
  before submitting.
- Harassment, discrimination, plagiarism, or attempts to manipulate judging → disqualification.

## Open-ended by design

Beyond the TrueForge and Qodo requirements the challenge is open: a developer tool, an internal
assistant, a research desk, an incident responder, a data pipeline, or anything else worth
handing to an agent, in any domain. Organizers' guidance: **pick one narrow job an agent can
finish end to end** — "one narrow job done end to end scores better than a platform with three
half-finished features."

Their six example ideas (not requirements): approval-gated assistant (Gmail/Slack) · analytics
agent (your database) · code review agent (GitHub) · research desk (web search) · incident
responder (your cloud, flagged "hero project") · untrusted code runner (the sandbox).
