# ADR-0006: Clear the inferred cold-chain mission before the thesis lands

Status: Accepted
Owner: Mulaydm10
Date: 2026-08-27

## Context

`VISION.md` has been `TODO(Mulaydm10)` since the repo was created. To verify the platform against
something concrete, a working mission was **inferred** — a pharmaceutical cold-chain agent that
investigates temperature excursions and prepares a deviation record. It was banner-marked as
provisional (`Q-0009`) and never written into `VISION.md`.

Mulaydm10 then asked, before supplying the real idea, whether the repo carried assumptions about
it. It did — twenty files. They directed that the idea-derived ones be removed.

**Where the assumption actually came from, stated honestly, because it changes what should go.**
It was not purely a guess from the name. The tech stack Mulaydm10 supplied on 2026-08-27 named a
*"VCC-CPLD dataset (Zenodo, 445K real cold-chain records)"* and openFDA drug labels. So
"cold-chain" is traceable to their own input. What was **not** in that stack, and was invented on
top of it, is the mission narrative: mean kinetic temperature, USP <1079> stability budgets, a
release/review/quarantine verdict, a quality team signing a deviation record. The stack also
named Stripe test-mode, which a pharmaceutical QA agent has almost no use for — a signal, read too
late, that the real idea is probably not the one that was inferred.

Two separate things were at risk, and only one of them is about files:

1. **The repo pulls.** 47 tests and a working pipeline are an argument for bending a new idea to
   fit them.
2. **The agent pulls.** Any assistant reading this repo cold inherits the framing whether or not
   `VISION.md` is empty.

## Decision

**Remove everything that encodes a mission. Keep everything that encodes the platform.**

Removed:

| Path | Why |
|---|---|
| `src/coldcall/mkt.py` | MKT / stability-budget maths. Regulated pharma arithmetic; meaningless outside temperature-controlled goods. |
| `src/coldcall/replay.py` | Streaming telemetry replay, typed `Reading(celsius, minutes)` to feed the above. |
| `tests/test_mkt.py`, `tests/test_replay.py` | Their 45 tests. |
| `skills/coldchain-sop/SKILL.md` | The inferred SOP, in full. |
| The `instructions` string in `agents/coldcall.agent.json` | Described the inferred agent. |

Kept, because none of it depends on the idea: the TrueForge harness, the Daytona sandbox
provider, the GitHub MCP connector and its approval gates, the Qodo review loop, the PR
discipline, `scripts/setup_trueforge.sh`, `scripts/verify_apis.sh`, the `uv` toolchain, and the
dependency-free-payload constraint on `src/coldcall/`.

Kept deliberately despite naming cold chain: **`ADR-0003` and the verified dataset.** The dataset
was Mulaydm10's input, the substitution decision was real work, and ADRs are historical record —
rewriting one to match a later reset would be falsifying the trail. `ADR-0003` now reads as
"here is a real, verified dataset we found", which is true and useful whatever the idea is.

`skills/coldchain-sop` is replaced by `skills/repo-evidence`, not simply deleted. The git-backed
skill mount is a judged capability that was proven working (`EXP-0008`); deleting the only skill
would break the registration and force re-proving it. The replacement carries the repo's actual
evidence rule, which is domain-neutral.

## Consequences

- `uv run pytest` drops from 47 tests to 2. That is the honest number: 45 of them tested a
  mission nobody agreed to. `tests/test_package.py` keeps the canonical command green and guards
  the reset — it fails if domain logic reappears before a thesis exists.
- The harness's skill registration must be repointed from `coldchain-sop` to `repo-evidence`.
  TrueForge fetches skills from GitHub at the registered ref, never from the working tree, so
  this only works once the branch is merged — re-register against `main` after merge, or against
  the branch to test earlier.
- `tests/README.md` is LOCKED and its layout table now names deleted files. The correction is
  proposed, not applied; Main Agent applies and logs it.
- **Restoring is one command**, if the real idea turns out to be cold-chain after all:
  `git checkout 3e01090 -- src/coldcall tests skills/coldchain-sop`. Nothing is lost, and the
  full history stays in the log. This is why removal was preferred to an `attic/` directory: the
  code is equally recoverable either way, but only removal stops it biasing what comes next.
- `Q-0009` closes as **discarded**. `Q-0001` (the thesis) remains the one real blocker.

## The rule this establishes

**Domain logic follows the thesis; it never precedes it.** Building a mission to have something
to test against is defensible under deadline — but it must be torn out before the real idea
arrives, not argued into compatibility with it.
