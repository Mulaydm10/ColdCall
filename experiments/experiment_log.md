# Experiment log (schema-locked header, append-only rows)

Add a row per attempt worth remembering. Never edit or delete a past row — if an experiment is
revisited, add a new row referencing the old `EXP-####` id rather than editing it in place.

| ID | Date | What was tried | Result | Decision | Links |
|---|---|---|---|---|---|
| EXP-0001 | 2026-08-27 | Boot TrueForge standalone locally: `npx @truefoundry/trueforge` | **Works.** v0.1.4, SQLite at `~/Library/Application Support/trueforge/db/`, serves http://localhost:8790 (HTTP 200), API docs `/api/v1/docs`. Logs a **local sandbox fallback** available on darwin (bash + python3.14) alongside the documented Daytona provider. Auth disabled in standalone. | Use standalone `npx` route for the whole event; skip the docker-compose route (Docker not installed and not needed). Open `Q-0004` on whether the local fallback is enough for the sandbox judging beat. | `COMPETITION.md` → Required technology; `Q-0004` |
