> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# design/

Architecture and decision records live here. `decisions/` holds Architecture Decision Records
(ADRs), one file per decision, numbered `ADR-####` — never renumbered, never deleted. A
superseded ADR stays in place with its Status line updated to `Superseded by ADR-####`; the
history of what we used to believe is worth keeping.

## Writing an ADR

Copy `decisions/ADR-0000-template.md`, take the next `ADR-####`, fill it in. Status starts at
`Proposed`; move to `Accepted` once the Main Agent signs off (log the sign-off as a
`worklog.md` entry citing the ADR id), or `Rejected` with the reason kept in the file.

An ADR with an undecided owner or open decision criteria is normal mid-hackathon — leave it
`Proposed` rather than forcing a premature `Accepted`. What's not normal is silently acting as
if a `Proposed` ADR were settled; check status before building on top of one.
