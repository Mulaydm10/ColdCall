# ADR-0004: How the four specialists are actually implemented

Status: Accepted
Owner: Mulaydm10
Date: 2026-08-27

## Context

The plan calls for four named specialist subagents — Stability Analyst, Logistics Scout,
Compliance Officer, Exposure Accountant — fanned out in parallel. The obvious reading is that
TrueForge has a subagent registry where each is declared with its own name, tools and prompt.

**It does not.** Verified against this build's OpenAPI spec and the docs: `AgentSpec` has no
subagent registry field. The only mechanism is `config.dynamic_sub_agents.enabled`, and it is
exactly what it sounds like — the root agent calls a built-in `create_sub_agent` tool at
runtime, writes each subagent's instructions itself, and runs them in parallel. Three further
constraints matter:

- subagents **share the root's tools and sandbox**; they cannot be given a narrower toolset
  declaratively;
- they **cannot talk to the user** — approvals still pause them, but they surface through the root;
- they **cannot nest**. One level of delegation, full stop.

## Options considered

- **Declare four agents and orchestrate them ourselves** over the sessions API. Gives real
  isolation and per-agent tool scoping, but we would be rebuilding the fan-out the harness
  already does — and "the harness is doing the work" is the qualification gate. Building around
  a feature to reimplement it is the exact failure mode the judges screen for.
- **Drop the four-specialist framing** and let the agent decompose freely. Loses a structure
  that is genuinely useful, and makes the demo harder to narrate.
- **Name the specialists in the root agent's instructions** and let dynamic subagents carry them.

## Decision

**Name them in the instructions.** The root agent's prompt describes four strands — stability,
logistics, compliance, exposure — each with one job and one question to answer, and dynamic
subagents execute them in parallel.

The four names survive as a vocabulary for the operator and the demo narration; what changes is
that they are a *pattern the agent follows*, not four config objects. This is what the harness
supports, and using it as designed is what the rubric rewards.

## Consequences

- Specialist behaviour lives in `agents/coldcall.agent.json`'s `instructions` and in the
  `coldchain-sop` skill, not in a registry. Changing a specialist is a prompt change.
- We cannot give the compliance strand read-only tools while the exposure strand writes:
  tool scoping is per-agent, not per-subagent. Approval gating on `mcp_servers[]` remains the
  real safety boundary, and that boundary is unaffected by which strand triggers it.
- Nothing may assume nested delegation. A strand cannot spawn its own helpers.
- The demo should show the fan-out happening rather than assert it, since the specialists are
  no longer visible as static configuration.

## Related

`ADR-0002`, `DEMO-0001`
