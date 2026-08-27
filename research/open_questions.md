# Open questions (append-only, Q-#### ids)

Register a question the moment it blocks something. Never delete a row; when a question
resolves, add a **Resolved** note with date + link/answer rather than removing it — the record
of what we didn't know, and when we learned it, is worth keeping.

| ID | Question | Raised | Status | Resolution |
|---|---|---|---|---|
| Q-0001 | What is this project's actual thesis? (see `VISION.md`, all sections TODO) | 2026-08-27 | Open | — |
| Q-0002 | Which stack — Python, TypeScript/Next.js, or both? (see `design/decisions/ADR-0002-stack-selection.md`) | 2026-08-27 | **Resolved 2026-08-27** | Polyglot with a hard line: Node runs the harness (mandatory, not a choice), Python 3.11+ under `uv` computes the regulated numbers inside the sandbox. `ADR-0002` Accepted; 43 tests green. |
| Q-0003 | Which model provider + API key does TrueForge get? (BYO — SF OpenAI credits don't apply to us) | 2026-08-27 | Open | — |
| Q-0004 | Daytona sandbox API key — do we need one, or does TrueForge's local sandbox fallback satisfy the "code runs in a sandbox" judging beat? | 2026-08-27 | **Resolved 2026-08-27 — no Daytona key needed** | Standalone TrueForge falls back to a built-in `LocalSandboxProvider` when no Daytona record exists (`EXP-0007`). Capabilities reports sandbox **and** skills enabled with zero providers configured. The `["daytona"]` enum governs what may be *configured*, not what the runtime falls back to. Daytona stays deliberately unconfigured, since a stored-but-broken record would suppress the fallback. |
| Q-0005 | Public GitHub repo name + Qodo installation on it (both need a human with repo admin) | 2026-08-27 | **Resolved 2026-08-27** | Repo: https://github.com/Mulaydm10/ColdCall (public, MIT). Qodo GitHub App installed by Mulaydm10 across the account's repos; ColdCall shows Healthy + code review on, and reviewed PR #1. |
| Q-0006 | Team roster + is registration (the Google Form) completed? | 2026-08-27 | Open | — |
| Q-0007 | Which real product label do we judge the replayed shipment against? The verified dataset is ambient logistics (~22–30 °C), not refrigerated — a 2–8 °C label quarantines every leg trivially, a real 15–25 °C USP controlled-room-temperature label produces a genuine release/review/quarantine spread. See `ADR-0003`. | 2026-08-27 | Open | — |
| Q-0008 | Supabase project + MCP URL and access token; Stripe **test-mode** key; GitHub token for the MCP connector. All three are real integrations the plan depends on and none can be created by an agent. | 2026-08-27 | Open | — |
| Q-0009 | The repo now contains a working cold-chain agent (SOP skill, agent instructions, MKT maths) while `VISION.md` is still `TODO`. The mission was inferred from the supplied tech stack, not agreed as the thesis. Confirm, amend, or discard it when `Q-0001` resolves — and if the real thesis differs, say explicitly what of this survives. | 2026-08-27 | Open | — |
