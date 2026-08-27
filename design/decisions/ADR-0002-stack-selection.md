# ADR-0002: Stack selection

Status: Proposed
Owner: TODO(Mulaydm10)
Date: 2026-08-27

## Context

The technical stack for this project is explicitly undecided as of scaffold creation. This ADR
exists so the decision, once made, has a permanent record — and so that until it's made, no
file in this repo silently presumes an answer. Registered as `Q-0002` in
`research/open_questions.md`.

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
