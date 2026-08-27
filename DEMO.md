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

## DEMO-0001 — TODO(Mulaydm10): scenario name

Status: **not yet defined** — depends on `VISION.md` (`Q-0001`) and the stack decision
(`ADR-0002`, `Q-0002`) landing first.

**Preconditions** (what must already be running/seeded before starting):
- TODO(Mulaydm10)

**Steps** (click-by-click or command-by-command; number every step):
1. TODO(Mulaydm10)

**Expected output at each step:**
- TODO(Mulaydm10) — be specific enough that a rehearsing teammate can tell "worked" from
  "silently didn't" without guessing.

**Known-broken edges to avoid** (don't click here, don't type this, this input crashes it):
- TODO(Mulaydm10)

**Reset procedure** (how to get back to a clean demo state after a run-through or a failed
attempt, fast, mid-event):
- TODO(Mulaydm10)

## Adding a new scenario

Copy the block above, increment to the next `DEMO-####`, and keep the same five headings
(Status, Preconditions, Steps, Expected output, Known-broken edges, Reset procedure). Retire a
scenario by marking its Status line `superseded by DEMO-####` rather than deleting it — the
history of what used to demo cleanly is useful when triaging a regression.
