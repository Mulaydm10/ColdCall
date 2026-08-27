# AGENTS — concurrency rules (vendor-neutral twin of CLAUDE.md)

This file is the non-Claude-specific cold-start entry point: any agent framework that reads an
`AGENTS.md` convention picks this up. It carries the same rules as `CLAUDE.md` for **this
repo's multi-agent concurrency model** specifically. The two files must stay consistent —
`CLAUDE.md` points here rather than duplicating this content, and this file does not restate
`CLAUDE.md`'s ID scheme or read order; see that file for those.

Multiple humans and AI agents work in this repo **at the same time**, under hackathon deadline
pressure. These rules exist so two agents don't silently clobber each other's work or ship
conflicting demo paths.

## Who owns what

- **LOCKED files** (see `GOVERNANCE.md` for the full list): only the Main Agent (`Mulaydm10`)
  applies edits, and every edit is logged in `GOVERNANCE.md`'s audit table. Any agent — human
  or AI — that wants a LOCKED file changed proposes the change; it does not edit it directly.
- **`STATE.md`**: anyone may overwrite it, but only to reflect current reality — never append
  to it, never leave it stale after finishing a unit of work.
- **`worklog.md`**: anyone may append a dated + timestamped entry; nobody edits a past entry.
- **`DEMO.md`**: whoever last verified it runs is implicitly responsible for it not regressing;
  if you touch code a `DEMO-####` scenario depends on, re-run that scenario before yielding.
- **Code / build surfaces**: not yet defined — depend on the stack decision (`ADR-0002`,
  `Q-0002`). Once a stack is chosen, this section must be updated with concrete surface
  ownership (e.g. "frontend", "agent orchestration", "eval harness").

## How to claim work

Before starting on a surface (a file, a feature, a demo scenario), add a row to the **Work
claims** table in `STATE.md`: surface, your name/id, timestamp, status. Check that table before
starting anything non-trivial — a claimed surface means someone else is already in there.
Release your claim (remove or mark done) the moment you stop working on it, even mid-task —
a stale claim blocks everyone else worse than no claim at all.

## The one hard rule

**Any agent finishing a unit of work updates `STATE.md` before yielding.** "Finishing" includes
stopping early, hitting a blocker, or running out of turn budget — not just completing a task.
An agent that yields without updating `STATE.md` leaves the next agent (human or AI) to
re-derive what happened from `worklog.md` alone, which is strictly more expensive.

## Escalation

If two agents' work conflicts (same file, incompatible changes), do not silently pick a winner.
Note the conflict in `STATE.md` under "Blocked" and in a `worklog.md` entry, and leave both
versions discoverable (e.g. a branch or a clearly marked alternate file) until the Main Agent or
a human resolves it.
