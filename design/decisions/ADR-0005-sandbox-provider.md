# ADR-0005: Daytona is the sandbox we demo, local is the fallback we keep quiet

Status: Accepted
Owner: Mulaydm10
Date: 2026-08-27

## Context

`EXP-0007` established that standalone TrueForge falls back to a built-in `LocalSandboxProvider`
when no Daytona provider is configured, and that this satisfies the harness technically: with
zero providers configured, `GET /api/v1/capabilities` reports both `sandbox.enabled: true` and
`skill.enabled: true`, and this machine's boot log confirms local support.

That made Daytona look optional. Judged against what the *rules literally say*, it is: no
hackathon rule names Daytona. The binding requirement is the judging criterion —

> **Control and safety** — Does the agent run its code somewhere safe and stop for a human
> before anything irreversible?

— plus the submission requirement that a judge see "code run in the sandbox".

**But the rules are not the whole story, and this is the point of this ADR.**

1. **The official documentation does not acknowledge any local sandbox.** `trueforge.dev`
   states plainly: *"Daytona is the only sandbox provider supported today. Support for
   additional providers is planned."* The event's own kick-off guide walks every participant
   through Step 5, "Add a sandbox", and that step is Daytona. The local fallback is real but
   **undocumented** — it exists in the bundle, not in anything a judge will read.
2. **A judge checking our sandbox claim will check it against the docs.** If the settings page
   shows no sandbox provider configured, the honest-looking conclusion from the outside is that
   we skipped the sandbox — and "Control and safety" is one of six equally weighted criteria.
   We would be relying on a judge reading TrueForge's source to award us that mark.
3. **The local provider is weaker on the merits, not just on optics.** It runs on the host
   under a sandbox root with its own venv. That is meaningful isolation, but it is not a remote
   microVM, and the criterion asks whether generated code runs *somewhere safe*. Daytona is the
   stronger answer to the question actually being asked.

## Decision

**Configure Daytona and demo on Daytona.** Treat the local fallback strictly as an emergency
continuity path — something that keeps a demo alive if Daytona is unreachable mid-event, never
the thing we present as our sandbox story.

## The operational trap this creates

From `EXP-0007`, and it is worth stating loudly because it is counter-intuitive:

**The local fallback applies only when *no* Daytona record is stored.** `resolveSandboxProvider`
returns the stored Daytona provider whenever one exists, and only falls through to
`LocalSandboxProvider` when the store is empty. So a configured-but-broken Daytona provider is
**strictly worse than none** — the harness will use it and fail, rather than falling back.

Which means the emergency path is not automatic. Recovering to it requires *removing* the
Daytona record, and TrueForge 0.1.4 exposes no DELETE for sandbox providers. In practice, mid
demo, that means stopping the harness and clearing the row from the SQLite store at
`~/Library/Application Support/trueforge/db/db.sqlite`. **Rehearse this before demo day rather
than discovering it during one.**

## What the key must carry

The supplied key (2026-08-27) is valid and can create sandboxes — verified against Daytona
directly, `POST /api/sandbox` returned 200 and produced a real sandbox. It fails only because it
lacks **`write:snapshots`**: TrueForge's `buildImage()` registers its sandbox image
(`tfy.jfrog.io/tfy-images/trueforge-sandbox:0dab475…`) as a Daytona snapshot, Daytona returns
403, and `isDaytonaAuthError` maps *any* 401/403 to the misleading message "Daytona rejected the
API key — check the credentials".

**Daytona API key permissions are fixed at creation and cannot be edited** — the dashboard
exposes deletion, not modification. So a key without that scope has to be recreated with it.
The event's own kick-off guide hints at this in one easily-missed phrase: *"Create a Daytona API
key with the required permissions."*

## Consequences

- `DAYTONA_API_KEY` returns to being **required**, not opt-in, in `.env.example` and in the
  setup script's reporting.
- `scripts/setup_trueforge.sh` already exits non-zero when the provider is rejected, which is
  the correct behaviour under this decision: an unconfigured sandbox is now a real failure.
- The local fallback stays undocumented in anything judge-facing, and is described here and in
  `DEMO.md`'s reset procedure only as continuity.
- `DEMO-0001` must show sandboxed execution visibly, since the criterion is scored on what the
  judge sees.

## Related

`EXP-0005`, `EXP-0007`, `Q-0004`, `ADR-0002`
