# ADR-0002: Stack selection

Status: Proposed (constraints narrowed 2026-08-27 — see "Hard constraints discovered")
Owner: TODO(Mulaydm10)
Date: 2026-08-27

## Context

The technical stack for this project is explicitly undecided as of scaffold creation. This ADR
exists so the decision, once made, has a permanent record — and so that until it's made, no
file in this repo silently presumes an answer. Registered as `Q-0002` in
`research/open_questions.md`.

## Hard constraints discovered 2026-08-27 (narrow the options)

`COMPETITION.md` is now filled in, and it removes most of the freedom this ADR assumed:

- **TrueForge is mandatory** and is a **Node.js 22+** program (`npx @truefoundry/trueforge`,
  verified running as v0.1.4, `EXP-0001`). Node is therefore in the stack no matter what.
- An agent is defined by a single **`agent.json`** — model, instructions, connectors. The
  minimum-viable project is configuration, not a codebase.
- The harness is drivable three ways: **chat UI**, **HTTP API**, or a **TypeScript library**.
  Only the last two produce code a judge can read, and "Technical excellence" plus "Use of
  sponsor tools" are two of six equally weighted criteria — a chat-UI-only project has almost
  no repo to score.
- The **Best UI** track (an iPad *per team member*) is only reachable with our own frontend,
  which points at TypeScript end to end.
- Custom tooling reaches the agent as an **MCP server**, which can be written in any language —
  this is the one place Python is genuinely free to appear.

So the live question is no longer "Python or TypeScript" but: **TypeScript-only (harness library
+ our own UI), or TypeScript + a Python MCP server / sandbox payload where Python's ecosystem
actually earns its place.**

**If any Python is used it must run under `uv` in a project-local virtual environment — never a
global install.** See `CLAUDE.md` → "Canonical commands".

## Options considered

- **Python** — pros: TODO(Mulaydm10) (e.g. ML/agent-framework ecosystem maturity, team
  familiarity); cons: TODO(Mulaydm10) (e.g. frontend/demo-polish speed).
- **TypeScript / Next.js** — pros: TODO(Mulaydm10) (e.g. fast path to a polished, deployable
  demo UI, Vercel deploy story); cons: TODO(Mulaydm10) (e.g. team familiarity, agent-tooling
  maturity for the chosen approach).
- **Both / polyglot** (e.g. Python backend or agent core + TS frontend) — pros:
  TODO(Mulaydm10); cons: added integration surface and time cost under a hard deadline.

## Decision criteria

TODO(Mulaydm10) — at minimum, weigh: team's existing familiarity, what `COMPETITION.md`'s
judging rubric actually rewards (a slick demo UI vs. a robust agent core), time-to-first-working
`DEMO-####` scenario, and maturity of the agent/tool ecosystem for whichever approach the idea
in `VISION.md` needs once that's filled in.

## Decision

Not yet made.

## Consequences

Whoever resolves this ADR must, in the same change: move Status to `Accepted`, fill in
`CLAUDE.md`'s "Canonical commands" section with real setup/test/lint commands, add whatever
minimal toolchain config the chosen stack needs, and land a green smoke test (see
`tests/README.md` — there is currently no runnable test baseline).

## Related

`Q-0002`, `ADR-0001`
