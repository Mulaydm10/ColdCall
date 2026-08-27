# ADR-0002: Stack selection

Status: **Accepted** 2026-08-27
Owner: Mulaydm10
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

**Polyglot, split along a hard line: Node runs the agent, Python computes the numbers.**

Node/TypeScript is not really a choice — TrueForge is a Node 22+ program and it is mandatory,
so the harness layer is Node whatever else we do. The decision is what runs *inside* the
sandbox, and that is Python, for one reason: the verdict on a shipment is regulated arithmetic
that has to be reproducible and auditable by someone who does not trust the agent. That code
belongs in a tested module with fixtures, not in a model's reasoning and not in glue.

The line between them:

| Layer | Language | Why |
|---|---|---|
| Agent harness, connectors, approvals, generative UI | Node (TrueForge, as given) | Mandatory; not ours to choose |
| Agent definition | `agent.json` | Configuration, not code |
| Stability maths + telemetry replay | Python 3.11+, stdlib only | Runs in the Daytona sandbox; must import with nothing installed |
| Data/analysis helpers | Python, `data` extra (httpx, pandas) | Never imported by sandbox code |

**Python is managed exclusively with `uv` in a project-local `.venv`.** No global installs, no
`pip` into the system interpreter. The venv is created with `uv venv --python 3.12`; the floor
is 3.11 so the module still imports on whatever interpreter a sandbox image happens to ship.

The `coldcall` package has **zero required dependencies** on purpose. It is uploaded into a
sandbox and executed against a stock Python, so anything it imports must already be there.
`httpx` and `pandas` live in an optional `data` extra that sandbox code never touches.

## Consequences

- `pyproject.toml` + `uv.lock` are committed; `.venv/` is not.
- Test baseline is green: `uv run pytest` — 43 tests covering the maths (including a
  cross-check against an independently written naive implementation) and the streaming replay.
- `CLAUDE.md`'s "Canonical commands" section is filled in, as this ADR required.
- No `package.json`: we consume TrueForge through `npx` and configure it over HTTP with
  `scripts/setup_trueforge.sh`. Nothing in this repo needs a Node build, and adding one would
  be a build surface with no build in it. Revisit only if we write a custom TypeScript client.
- The sandbox is a hard dependency for two judged features at once — skills require it, and
  "code runs somewhere safe" is a scored criterion — so a Daytona key is on the critical path.

## Consequences

Whoever resolves this ADR must, in the same change: move Status to `Accepted`, fill in
`CLAUDE.md`'s "Canonical commands" section with real setup/test/lint commands, add whatever
minimal toolchain config the chosen stack needs, and land a green smoke test (see
`tests/README.md` — there is currently no runnable test baseline).

## Related

`Q-0002`, `ADR-0001`
