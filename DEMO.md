# DEMO — the script judges will see

This is the single highest-value artifact in the repo and the one most hackathon repos skip.
It is not documentation of what the product *can* do — it is the exact, rehearsed happy path
that will be shown live. **It must stay runnable at all times** once any demo path exists: if a
change breaks the flow below, fixing it (or rolling the script back to a step that still works)
is higher priority than new features.

Scenarios are numbered `DEMO-####` so they can be cited from `worklog.md`, `STATE.md`, or an
`EXP-####` entry (`grep -rn DEMO-0001 .` finds every mention).

## Non-negotiable beats — every scenario must contain all three

Independent of what the idea turns out to be, `COMPETITION.md` fixes what a qualifying demo has
to show on camera. These are not suggestions; the first is the qualification gate and the third
is a full judging criterion of its own ("Control and safety") that the organizers say nobody
films.

1. **A real tool reached through MCP** — connected to something real, not mocked.
2. **Agent-written code executing in the sandbox** — show *where* it ran.
3. **A pause for human approval before something irreversible** — show the moment it stops
   and asks, and the approval landing.

Plus, for the ~3-minute video as a whole: state the problem, show the agent working, and make
clear where the harness fits. Keep every key and every piece of personal data off screen.

Organizers' framing to design against: *"If it would work just as well as a chat box, change
the project."*


## DEMO-0001 — one pallet, dispositioned, with a human holding the pen

**Status:** runnable as of 2026-08-27. Last rehearsed end to end against TrueForge v0.1.4;
both the deny path and the allow path verified, the allow path leaving commit `1c859fc` on the
public repo. See `EXP-0010`.

### The claim this demo has to land

> Sensors already detect excursions. Nobody automates the decision that follows. ColdCall
> computes the actual regulatory disposition — and then stops, because the signature is not
> the agent's to give.

### Preconditions

Run these **before** recording. All are idempotent and none take arguments you have to think
about.

```sh
npx @truefoundry/trueforge                 # harness up on :8790, Node 22+
uv sync --group dev && uv run pytest       # 107 green — the maths, before you trust it
./scripts/verify_apis.sh                   # every external source, hit for real
./scripts/setup_trueforge.sh               # 5 configured, 0 failed
```

Then check the two things that actually break takes:

- `curl -s localhost:8790/api/v1/settings/skills | jq -r '.data[].manifest.ref'` — the skill
  ref must be a branch that **contains `skills/coldchain-sop`**. Registering it against a ref
  that lacks the path fails the sandbox at init and the agent proceeds without its SOP.
- **Rehearse the run twice.** The git-backed skill fetch is a cold-start race against the
  sandbox's network, and each strand gets its own sandbox, so each one rolls the dice
  separately. It has failed once and cleared on retry (`EXP-0011`).

### Steps

| # | Beat | Command / action | Roughly |
|---|---|---|---|
| 1 | **The problem** | Say it: ~$35B of medicine moves under temperature control; sensors catch the excursion; the *decision* is still a human reading a chart for hours. | 0:00–0:20 |
| 2 | **The excursion, in shipment-time** | `uv run python replay/engine.py --speed 60` — real recorded readings stream in, one leg, and the excursion opens on screen. | 0:20–0:45 |
| 3 | **The fan-out** | `uv run python replay/incident.py` — four strands start in parallel, visible as `thread.created` events. Say: *this is the harness doing the work, not a loop we wrote.* | 0:45–1:05 |
| 4 | **The maths, off-host** | The Stability Analyst clones the repo **inside a Daytona microVM** and runs the deterministic module. Show the verdict JSON: MKT **24.54 °C**, budget **64.35 %**, verdict **`quarantine_retest`**. Say: *this is WHO TRS-999 and USP <1079> arithmetic, in the repo, unit-tested — not an LLM guess. Same numbers on my laptop.* | 1:05–1:45 |
| 5 | **The moment** | The agent attempts a real GitHub write and **the harness stops it.** The banner names the tool, the repo and the branch. Read it aloud, then type `allow`. | 1:45–2:20 |
| 6 | **Receipts** | Show the created branch and the committed deviation record on GitHub — real commit sha, 5,984 bytes, real openFDA label provenance, real value at risk. | 2:20–2:35 |
| 7 | **The stunt** | `./scripts/restart_proof.sh <session-id>` — `kill -9` the harness on camera, restart, and the incident comes back with every event and every verdict intact. Say: *in pharma, the record **is** the product.* | 2:35–2:50 |
| 8 | **Close** | One pallet, decided properly, end to end on TrueForge: sandbox, subagents, skills, approvals, persistence, MCP, generative UI — every one of them load-bearing. Repo and quickstart on screen. | 2:50–3:00 |

### Expected output

At step 4, verbatim from the sandbox:

```json
{
  "verdict": "quarantine_retest",
  "mkt_c": 24.54,
  "budget_consumed_pct": 64.35,
  "margin_pct": 35.65,
  "excursion": { "minutes_total": 1233.3, "minutes_out_of_range": 231.67, "max_c": 27.0 },
  "policy": { "allowed_excursion_hours": 6.0, "source": "ColdCall demo policy — not a regulatory limit" }
}
```

At step 5:

```
========================================================================
  HELD FOR APPROVAL - irreversible action
========================================================================

  call_tool  call_KrBXLw01IaqDYF20vZ8TpDxq
    {
      "mcp_server": "github",
      "tool_name": "create_branch",
      "input": { "owner": "Mulaydm10", "repo": "ColdCall",
                 "branch": "incident/INC-VCC-118-A2231-…" }
    }
```

At step 7: `PASS — the incident record survived a SIGKILL intact.`

### Three things to say out loud, because they are the difference

1. **"The model never decides."** It orchestrates, explains and drafts. The verdict is
   arithmetic anyone can re-run.
2. **"The hours allowance is ours, not the label's."** We checked openFDA: no real drug label
   states a permitted excursion duration. Every record we emit says so.
3. **"This is replayed, real recorded telemetry."** Never call it live.

### Known-broken edges

- **The skill fetch can flake on a cold sandbox** (`EXP-0011`). Mitigation: rehearse twice; if
  a strand reports `Sandbox initialization failed`, re-run rather than narrating around it.
- **Supabase and Stripe are dark**, pending one OAuth login each. The incident driver drops
  unconfigured connectors and says so on screen. If asked: the data layer is behind one
  interface with SQLite as today's default — a backend swap, not a rewrite. Do not claim
  those actions executed.
- **`--auto allow` must not appear on camera.** It approves without a human and prints a
  warning saying so. The gate is the demo.
- **The verdict depends on a policy input.** If a judge asks "what if the allowance were 4
  hours?", the honest answer is that it would `destroy` — and `margin_pct` is in the output
  precisely so that sensitivity is visible rather than hidden.

### Reset procedure

Nothing here is destructive, and every artifact is disposable.

```sh
rm -f data/coldcall.db data/coldcall.db-wal data/coldcall.db-shm   # gitignored; rebuilt on run
git push origin --delete incident/INC-VCC-118-A2231-…              # optional; branch-only
```

Sessions accumulate in TrueForge's SQLite and are harmless — the restart proof reads the newest
by default, so a stale one never breaks the next take. To take from a clean slate, create a new
session by simply re-running step 3.

## Adding a new scenario

Copy the block above, increment to the next `DEMO-####`, and keep the same five headings
(Status, Preconditions, Steps, Expected output, Known-broken edges, Reset procedure). Retire a
scenario by marking its Status line `superseded by DEMO-####` rather than deleting it — the
history of what used to demo cleanly is useful when triaging a regression.
