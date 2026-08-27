# ColdCall — cold-start entry point

Event: **The Agent Harness Hackathon** (WeMakeDevs × TrueFoundry × Qodo) — full facts in
`COMPETITION.md`. Project: **ColdCall** — what it does is TODO(Mulaydm10), the idea is pending.
This is an **agentic hackathon** repo worked by humans and AI agents concurrently, under
deadline pressure. If you are an agent picking this up cold, read this file fully, then follow
the read order below. Do not ask a human anything this repo can already answer you.

## Read order (cold agent)

1. `CLAUDE.md` (this file)
2. `STATE.md` — what's true right now (overwritten every session)
3. `VISION.md` — the thesis (LOCKED)
4. `COMPETITION.md` — event facts: deadline, rubric, hard rules (LOCKED)
5. `GOVERNANCE.md` — who owns what, audit trail
6. `AGENTS.md` — concurrency rules for multi-agent work in this repo
7. Recent tail of `worklog.md` — how we got to the current STATE
8. `experiments/experiment_log.md` — what's been tried

## STATE vs worklog — the tie-break rule

`STATE.md` is a live snapshot, overwritten every session. `worklog.md` is append-only dated
history, never edited. **If they disagree about what is true right now, STATE.md wins;
worklog.md explains how we got here.**

## Governance in one paragraph

Main Agent (sole authority over LOCKED files): **Mulaydm10**. A LOCKED file opens with the
banner `> **LOCKED governing file.** Do not edit in place. See \`GOVERNANCE.md\`.` — never edit
one directly; propose the change and let the Main Agent apply it, logging the edit as a row in
`GOVERNANCE.md`'s audit table. `CLAUDE.md` and `STATE.md` are deliberately **not** locked — see
`GOVERNANCE.md` for why.

## Stable ID scheme

Each kind of thing is **defined once**, in one canonical place:

| ID | The thing it names | Defined in |
|---|---|---|
| `ADR-####` | A design/stack decision | `design/decisions/ADR-####-*.md` |
| `Q-####` | An open question | `research/open_questions.md` |
| `EXP-####` | An experiment/spike | `experiments/experiment_log.md` |
| `DEMO-####` | A demo-path scenario | `DEMO.md` |

**Cite these IDs freely from anywhere else in the repo — that is the entire point of the
scheme.** A commit message, a `STATE.md` blocker, a worklog entry, a code comment, or another
ADR should all name the relevant ID, so that `grep -rn 'ADR-0003' .` recovers the full trace of
a decision: where it was made, what it blocked, what it changed, and when.

The table above says where each ID is *defined*, never where it may be *mentioned*. A rule that
confined mentions to the canonical file would defeat the traceability the scheme exists for.
Only the canonical file may allocate a new number.

## Layout

| Path | What |
|---|---|
| `src/coldcall/` | Dependency-free Python: stability maths (`mkt.py`), streaming telemetry replay (`replay.py`). Runs inside the sandbox, so it must import against a stock interpreter. |
| `tests/` | pytest suite, 43 tests |
| `agents/coldcall.agent.json` | The agent manifest: model, instructions, MCP servers with their approval gates, skills, harness features |
| `skills/coldchain-sop/` | Git-backed `SKILL.md` the harness loads at runtime |
| `scripts/` | Idempotent setup + a real pre-demo API check |
| `data/samples/` | Gitignored; re-fetchable telemetry sample |

## Where the code lives

Public repo (open source is a submission requirement): **https://github.com/Mulaydm10/ColdCall**
(MIT). `main` is the merge target; nothing lands on it except through a Qodo-reviewed PR.

## Canonical commands

**The harness (mandatory, works today):**

```sh
npx @truefoundry/trueforge      # standalone; needs Node 22+ (this machine: 26.5.0)
                                # → http://localhost:8790, API docs at /api/v1/docs
```

Verified running as v0.1.4 on 2026-08-27 (`EXP-0001`). SQLite-backed, no account, nothing to
clone. Do **not** use the `docker compose` route — Docker is not installed here and standalone
is sufficient.

**Project setup and tests** (stack settled in `ADR-0002`: Node runs the agent, Python computes
the numbers):

```sh
uv venv --python 3.12 .venv     # project-local; never a global install
uv sync --group dev             # pytest, pytest-cov, ruff
uv run pytest                   # 43 tests, green
uv run ruff check .             # lint
```

**Configure the harness and check the data path** — both idempotent, safe to re-run:

```sh
cp .env.example .env            # then fill in the keys; .env is gitignored
./scripts/setup_trueforge.sh    # model provider, Daytona sandbox, MCP servers, skills
./scripts/setup_trueforge.sh --dry-run   # show what it would do, change nothing
./scripts/verify_apis.sh        # every external source, hit for real
```

`scripts/verify_apis.sh` is the pre-demo check: it calls each API and asserts on the response,
so green means the data path works *now*, not that it worked when the README was written.

**Qodo review loop (mandatory — see `COMPETITION.md`):**

```sh
npx skills add qodo-ai/qodo-skills/skills   # already installed; skills-lock.json is committed
```

Gives this repo the `qodo-pr-resolver` and `qodo-get-rules` skills for working through Qodo
findings on a PR branch. The expanded skills (`.agents/`, `.claude/`) are gitignored — only the
lockfile is committed, so the install is reproducible. If Qodo does not review a PR on its own,
comment `/agentic_review` on it.

**Environment rule — nothing global, ever:**

- **Python → `uv`, in a project-local virtual environment.** `uv venv` + `uv add` / `uv run`.
  Never `pip install` globally or into the system/homebrew interpreter. One-off tools: `uvx`.
- **Node → project-local.** `npx` or a devDependency; never `npm install -g`. There is no
  `package.json` and that is deliberate (see `ADR-0002`) — TrueForge is consumed via `npx` and
  configured over HTTP.
- If a command in this file ever needs a global install to work, the command is wrong.

## Hard rules

### Event rules that bind every commit (from `COMPETITION.md`)

- **Every substantive change goes through a GitHub pull request reviewed by Qodo before merge.
  Direct pushes to `main` do not count as reviewed work** and are worth zero to the judges.
  Branch → PR → Qodo review (`/agentic_review` if it doesn't fire) → fix every valid High
  finding or dismiss it in-thread with a reason → push → follow-up review → a human merges.
- **The agent must run on TrueForge, visibly.** If a change would work just as well behind a
  plain chat box, it is the wrong change.
- **AI-assistant use must be disclosed** in the README, and every participant must be able to
  explain the architecture and the technical decisions. Do not build anything the team cannot
  explain — that is a stated rejection criterion, not a style note.
- **Nothing the agent touches may be someone else's to touch**; no keys or personal data in the
  repo or the demo video.

### Repo rules

- Never edit a LOCKED file in place. Propose the change; Main Agent applies it + logs it.
- `STATE.md` is overwritten, not appended to. `worklog.md` entries are dated **and timestamped**
  (hackathon history moves hourly, not daily) and are never edited after the fact.
- Before yielding a unit of work, update `STATE.md` (see `AGENTS.md` for the claim protocol).
- Never invent a thesis, rubric detail, or result to fill a gap — leave it `TODO(Mulaydm10)`.
- `DEMO.md` must stay runnable at all times once a demo path exists — it is what judges see.

## Vendor-neutral twin

`AGENTS.md` carries the same concurrency rules for non-Claude agent frameworks. The two files
must stay consistent; this file points to it rather than restating its content.

## End-of-session checklist

- [ ] `STATE.md` reflects current reality (overwrite, don't append)
- [ ] `worklog.md` has a dated + timestamped entry for this session
- [ ] Any new experiment has a row in `experiments/experiment_log.md`
- [ ] Any LOCKED-file edit is logged in `GOVERNANCE.md`'s audit table
- [ ] Any work claim in `STATE.md` you finished is released
