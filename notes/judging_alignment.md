# Judging alignment

Maps each rubric criterion from `COMPETITION.md` → "Judging rubric" to the concrete artifact in
this repo that satisfies it. This is what stops the team building something judges never
actually score — if a criterion has no row, or its row has no artifact, that's a gap to close
before submission, not after.

**Six criteria, weighted equally.** The demo is scored as hard as the code. Weights and criterion
text are not restated here beyond the table; `COMPETITION.md` is the source of truth.

| # | Rubric criterion | Weight | Satisfied by (artifact/file/demo step) | Status |
|---|---|---|---|---|
| 01 | Potential impact | 1/6 | `VISION.md` → "Who for" + "What working looks like"; opening 20s of the demo video | Blocked on `Q-0001` (idea) |
| 02 | Creativity and originality | 1/6 | `VISION.md` → "Why isn't this already solved"; `research/prior_art.md` | Blocked on `Q-0001` |
| 03 | Technical excellence | 1/6 | The repo itself: green test baseline (`tests/`), README a stranger can run, `design/decisions/` ADRs | Not started — pending `ADR-0002` |
| 04 | Use of sponsor tools | 1/6 | **TrueForge central**: MCP connector + sandbox + approval gate + subagents visible in `DEMO-0001`. **Qodo**: the `## Qodo Code Review Evidence` README section + the PR trail | Harness verified running; Qodo installed and reviewing (PR #1). TrueForge side blocked on `Q-0001` |
| 05 | Control and safety | 1/6 | The approval-pause step of `DEMO-0001`, filmed; sandbox execution step, filmed | Blocked on `Q-0001` + `Q-0004` |
| 06 | Presentation | 1/6 | The ~3-minute demo video + `DEMO.md` script it is rehearsed from | Blocked on `Q-0001` |

## Non-rubric requirements that still gate the submission

These are not scored criteria but a submission is incomplete without them — see
`COMPETITION.md` → "Submission format" and "Hard rules".

| Requirement | Satisfied by | Status |
|---|---|---|
| Public, open-source repo | https://github.com/Mulaydm10/ColdCall (public, MIT) | **Done** |
| README with setup steps a stranger can follow | `README.md` → Quickstart | TODO, pending `ADR-0002` |
| ~3-minute demo video | `submissions/` | Not started |
| Write-up: what the agent does + how it uses TrueForge | `submissions/` | Not started |
| `## Qodo Code Review Evidence` section | `README.md` | **Done** — links merged PR #1, states what Qodo surfaced and what we changed, and points at the follow-up-review trail |
| AI-assistant use disclosed | `README.md` → "AI assistance disclosure" | **Done** — names Claude Code and Qodo; AI-authored commits carry a `Co-Authored-By` trailer |
| No keys / personal data in repo or video | `.gitignore` secrets block; demo rehearsal check | Guarded in `.gitignore`; re-check before filming |

## Optional prizes (cheap, do not skip)

| Prize | Action | Status |
|---|---|---|
| Calling Card (Logitech MX Master 3) | **Star https://github.com/truefoundry/trueforge** — no project required, draw entry | Not done |
| Field report (Keychron) | Blog post, published anywhere, link in submission | Not started |
| Radio traffic (swag ×10) | Post progress publicly, tag WeMakeDevs + TrueFoundry + Qodo | Not started |

Update this file every time `COMPETITION.md`'s rubric table changes, and again whenever a
`DEMO-####` scenario changes what it actually shows.
