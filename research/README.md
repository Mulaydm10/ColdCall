> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# research/

Two files, both append-only (add rows/entries at the end; never edit or delete a past one):

- **`prior_art.md`** — what already exists that's adjacent to this idea, and specifically why
  each thing falls short of it. This is what makes `VISION.md`'s "why isn't this already
  solved" section defensible instead of asserted.
- **`open_questions.md`** — unresolved questions, each with a stable `Q-####` id. Register a
  question the moment it blocks something, even if the answer is "ask a human" — an
  unregistered blocker is invisible to the next agent that picks this repo up.

Cite `Q-####` ids from `worklog.md`, ADRs, or `STATE.md`'s Blocked section wherever relevant so
`grep -rn 'Q-0001' .` recovers the full trace of a question from raised to resolved.
