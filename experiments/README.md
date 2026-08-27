> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# experiments/

`experiment_log.md` tracks every non-trivial attempt/spike worth remembering — a prompt
strategy that didn't work, an architecture tried and abandoned, an approach that worked
better than expected. The header/schema is fixed (LOCKED); rows are append-only. Each entry
gets a stable `EXP-####` id so it can be cited from `worklog.md`, `STATE.md`'s "Latest
experiment" line, or an ADR — `grep -rn 'EXP-0003' .` should recover the full trace.

Under hackathon time pressure this log should stay terse — one row per attempt, not a full
research write-up. The point is preventing the team (or an agent) from re-trying something
that already failed, not producing a paper trail.
