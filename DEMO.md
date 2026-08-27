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
# Terminal 1 — the harness is a server. Start it, leave it running, do not wait on it.
npx @truefoundry/trueforge                 # up on :8790, Node 22+
```

```sh
# Terminal 2 — credentials first, then the checks
cp .env.example .env                       # then fill in OPENAI_API_KEY and DAYTONA_API_KEY
uv sync --group dev && uv run pytest       # 130 green — the maths, before you trust it
./scripts/verify_apis.sh                   # every external source, hit for real
./scripts/setup_trueforge.sh               # expect: 5 configured, 0 failed
```

**Both keys are required for this scenario**, and `setup_trueforge.sh` *skips* rather than
fails when one is missing — so a clean checkout reports fewer than 5 configured and the
rehearsed path silently does not exist. Read its output rather than assuming:

- **`OPENAI_API_KEY`** — without it there is no model and no session at all.
- **`DAYTONA_API_KEY`** — without it there is no remote sandbox, so the maths never runs
  off-host and the demo's central claim is unshowable. Needs the **`write:snapshots`** scope
  (`EXP-0005`: a key lacking it is rejected with a misleading "check the credentials").

If the script says `skip` next to either, stop and fix that before going further.

**Reap Daytona first.** This is the single most likely thing to eat a take:

```sh
./scripts/daytona_gc.sh            # dry run: shows sandboxes and disk against the 30 GiB cap
./scripts/daytona_gc.sh --yes      # delete the stopped/archived ones
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
| 4 | **The maths, off-host** | The Stability Analyst clones the repo **inside a Daytona microVM** and runs the deterministic module. Show the verdict JSON: MKT **24.54 °C**, budget **64.35 %**, verdict **`quarantine_retest`**. Say: *this is WHO TRS-999 and USP <1079> arithmetic, in the repo, unit-tested — not an LLM guess. Same numbers on my laptop.* | 1:05–1:40 |
| 5 | **Why it warmed** | Show the `route_context` block. The Route Analyst pulled **real recorded weather at this shipment's own GPS**: outside air peaked at **17.7 °C** while the box hit **27 °C** — a **12.6 °C** median gap, 14 of 14 readings matched. Say: *this was not a hot day. The weather does not account for it, so this is a containment failure — the investigation goes to the packaging and the reefer, not to the lane. Two public datasets, and neither gives you that alone.* | 1:40–2:00 |
| 6 | **The moment** | The agent attempts a real GitHub write and **the harness stops it.** The banner names the tool, the repo and the branch. Read it aloud, then type `allow`. | 2:00–2:25 |
| 7 | **Receipts** | Show the created branch and the committed deviation record on GitHub — real commit sha, real openFDA label provenance, real value at risk, and the root-cause section. | 2:25–2:38 |
| 8 | **The stunt** | `./scripts/restart_proof.sh <session-id>` — `kill -9` the harness on camera, restart, and the incident comes back with every event and every verdict intact. Say: *in pharma, the record **is** the product.* | 2:38–2:50 |
| 9 | **Close** | One pallet, decided properly, end to end on TrueForge: sandbox, subagents, skills, approvals, persistence, MCP, generative UI — every one of them load-bearing. Repo and quickstart on screen. | 2:50–3:00 |

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

At step 5, the root cause:

```json
{
  "attribution": "containment_failure",
  "median_gap_c": 12.6,
  "peak_internal_c": 27.0,
  "peak_ambient_c": 17.3,
  "matched_readings": 14, "total_excursion_readings": 14
}
```

At step 6:

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
4. **"The weather is real, and so is the coordinate."** The GPS comes from the dataset's own
   records, not a plausible-sounding city — an invented location would produce an invented
   root cause. The 5 °C gap threshold that separates containment failure from environmental
   exposure is ours.

### Known-broken edges

- **Daytona's disk quota is the trap, and it lies about itself** (`EXP-0012`). Each run leaves
  five or six ~3 GiB sandboxes behind, and the 30 GiB free tier fills after a few rehearsals.
  When it does, the harness reports `git ls-remote failed ... Connection reset by peer` —
  identical to the transient cold-start race — so you retry, fail again, and debug networking.
  Meanwhile the agent runs **without its SOP** and produces a plausible incident that never
  reaches an approval gate. Run `./scripts/daytona_gc.sh --yes` before every session.
- **The skill fetch can also genuinely flake on a cold sandbox** (`EXP-0011`), independently of
  the quota. `replay/incident.py` now retries once on a fresh session automatically, and if the
  skill fails on every attempt it says so and exits non-zero rather than presenting the run.
  If you see that message, **do not narrate around it** — the run is not trustworthy.
- **Supabase and Stripe are dark**, pending one OAuth login each. The incident driver drops
  unconfigured connectors and says so on screen. If asked: the data layer is behind one
  interface with SQLite as today's default — a backend swap, not a rewrite. Do not claim
  those actions executed.
- **`--auto allow` must not appear on camera.** It approves without a human and prints a
  warning saying so. The gate is the demo.
- **Route context needs network from the sandbox and is opt-in.** If the weather lookup fails,
  the verdict still stands and the record says the cause is *not established* — do not narrate
  a cause the module did not return. If it returns `undetermined`, that is a legitimate finding
  and should be read aloud as one.
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
