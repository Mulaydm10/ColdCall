---
name: repo-evidence
description: How ColdCall proves a claim. Load before reporting any result, at any stage of any task.
---

# Evidence discipline

This skill replaces `coldchain-sop`, which encoded a mission that was inferred rather than
agreed and was cleared on 2026-08-27 (`ADR-0006`). It exists partly to keep the git-backed skill
path mounted and proven while the thesis is pending — but its content is not filler. It is the
one rule this repo has actually enforced on itself all along, and it is domain-neutral, so it
survives whatever ColdCall turns out to be.

## The rule

**A claim is worth nothing until it is backed by something a human can re-run.**

Not "the API returned 200". Not "the config was accepted". Those say a call was well-formed,
which is a different statement from the thing working.

| Instead of | Report |
|---|---|
| "The sandbox is configured" | What it printed. `Linux x86_64` from a macOS host proves remote execution; `status: ready` does not. |
| "The skill is registered" | The agent quoting the skill's contents back. |
| "The data source works" | The response field you actually need, asserted on — not the HTTP status. |
| "The tests pass" | The count, and what would have to break for them to fail. |

## What to do when you cannot get evidence

Say so, plainly, and say what you tried. An honest "I could not verify this" is worth more than
a confident sentence that a judge, a reviewer, or the next agent then has to disprove.

Never close the gap by inventing a number, a citation, or a result. If a fact is missing, it
stays `TODO(Mulaydm10)` — that is a repo rule in `CLAUDE.md`, not a preference.

## Two failure modes this repo has actually hit

Both are recorded in `experiments/experiment_log.md`; both cost real time.

1. **Propagating a subagent's finding that contradicted a log.** A research agent concluded from
   a settings schema that a capability did not exist. The boot log said otherwise. The schema
   governed what could be *configured*, not what the runtime *fell back to*. When two sources
   disagree, read the source before repeating either.

2. **Inferring the job from the toolbox.** A whole working mission was reverse-engineered from a
   list of APIs, then had to be torn out. Tools tell you what is *possible*, never what is
   *wanted*. Ask; do not deduce.
