# DEMO — the script judges will see

This is the single highest-value artifact in the repo and the one most hackathon repos skip.
It is not documentation of what the product *can* do — it is the exact, rehearsed happy path
that will be shown live. **It must stay runnable at all times** once any demo path exists: if a
change breaks the flow below, fixing it (or rolling the script back to a step that still works)
is higher priority than new features.

Scenarios are numbered `DEMO-####` so they can be cited from `worklog.md`, `STATE.md`, or an
`EXP-####` entry (`grep -rn DEMO-0001 .` finds every mention).

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
