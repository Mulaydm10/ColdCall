> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# logs/

Runtime logs from running/testing whatever gets built. Entirely gitignored (see `logs/.gitignore`
— whitelist pattern: everything ignored except this README and the `.gitignore` itself). Do not
commit log output; if a log is worth keeping as evidence, summarize the relevant part into the
matching `experiments/experiment_log.md` row instead.

No fixed naming convention is imposed yet since it depends on the eventual stack — whoever
resolves `ADR-0002` should add one here if it'd help (e.g. per-run directories keyed by
`EXP-####`).
