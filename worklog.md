# Worklog — append-only dated + timestamped history

Rules: append only, never edit or delete a past entry, never reorder. Newest entry at the
bottom. Every entry is dated **and timestamped** (hackathon history moves hourly, not daily) —
"2026-08-27 05:51 CEST", not just "2026-08-27". This is the "how we got here" log; for "what's
true right now" see `STATE.md` — if the two ever disagree, `STATE.md` wins.

Entries should cite `EXP-####` / `ADR-####` / `Q-####` / `DEMO-####` ids where relevant so
`grep -rn '<ID>' .` recovers the full trace.

---

### 2026-08-27 05:51 CEST — Mulaydm10 (scaffold)

Initial repo scaffold created: governance (`GOVERNANCE.md`), cold-start entry point
(`CLAUDE.md`), live snapshot (`STATE.md`), vision placeholder (`VISION.md`, registers `Q-0001`),
competition-facts placeholder (`COMPETITION.md`), demo script skeleton (`DEMO.md`),
agent-concurrency rules (`AGENTS.md`), ADR log with `ADR-0001` (scaffold's own choices, Accepted)
and `ADR-0002` (stack selection, Proposed, registers `Q-0002`), plus research/experiments/notes/
tests/submissions/logs/scratch scaffolding. No project work has started; event name, thesis, and
stack are all still `TODO(Mulaydm10)`.

---

### 2026-08-27 06:25 CEST — Mulaydm10 + Claude (event research + harness bring-up)

**Event identified and documented.** Read the official overview, rules, schedule and resources
pages plus the kick-off guide, and filled `COMPETITION.md` (LOCKED — applied on the Main Agent's
instruction, logged in `GOVERNANCE.md`'s audit table). It is **The Agent Harness Hackathon**
(WeMakeDevs × TrueFoundry × Qodo), window 2026-08-24 08:00 → **2026-08-30 20:00 London
(19:00 UTC)**. At time of writing: **~3d 14h remaining, day 4 of 7**. $10k in prizes across
three judged tracks (one per team max), six equally weighted judging criteria.

**Two hard gates found**, both now written into `CLAUDE.md`'s hard rules:
1. The agent **must run on TrueForge** and a judge must see the harness doing real work — a
   real MCP tool reached, agent-written code run in a sandbox, and a pause for human approval
   before anything irreversible. "If it would work just as well as a chat box, change the
   project."
2. **Every substantive change must land through a Qodo-reviewed pull request**; direct pushes
   to `main` do not count as reviewed work, and judges inspect the trail across the build, not
   just the final merge. This is our biggest exposure — we are on day 4 with zero PRs, no
   remote, and Qodo not installed (`Q-0005`).

**`EXP-0001` — TrueForge booted locally and works.** `npx @truefoundry/trueforge` brings up
v0.1.4 standalone on http://localhost:8790 (HTTP 200), SQLite-backed, auth disabled, API docs
at `/api/v1/docs`. Node 26.5.0 satisfies the Node 22+ floor. It also reports a **local sandbox
fallback** on darwin alongside the documented Daytona provider — raised as `Q-0004` since the
sandbox beat is judged. Docker route skipped (not installed, not needed).

**`ADR-0002` narrowed but not closed.** TrueForge being Node/TS with `agent.json` agents, plus
the Best UI track needing our own frontend, pushes the answer toward TypeScript end to end;
Python's free slot is a custom MCP server. Final call waits on the idea (`Q-0001`).

**Standing environment rule recorded** (`CLAUDE.md` → Canonical commands): all Python runs under
**`uv` in a project-local virtual environment**, Node stays project-local, nothing installed
globally.

Also: rubric mirrored into `notes/judging_alignment.md` with a second table for the non-scored
submission gates (public repo, ~3-min video, `## Qodo Code Review Evidence` README section,
**AI-assistant-use disclosure**) and a third for the cheap optional prizes; new questions
`Q-0003`–`Q-0006` registered; `DEMO.md` given the three non-negotiable on-camera beats;
`.gitignore` extended for `.playwright-mcp/`.

Still blocked on Mulaydm10 for: the project idea (`Q-0001`), a public GitHub repo + Qodo install
(`Q-0005`), a model provider key (`Q-0003`), a Daytona key (`Q-0004`), and roster/registration
confirmation (`Q-0006`).

---

### 2026-08-27 06:35 CEST — Mulaydm10 + Claude (repo live, PR trail started)

Project named **ColdCall** by the Main Agent. Public repo created at
**https://github.com/Mulaydm10/ColdCall** (MIT, public — the open-source submission requirement),
`main` pushed, and **PR #1** opened from `docs/event-facts` carrying the event-facts work from
the previous entry. The review trail now exists on day 4 rather than day 7.

Deliberate: the docs work was committed to a branch *before* the remote existed, so nothing has
ever been pushed straight to `main` on the remote. `main` holds only the two original scaffold
commits.

README gained the two sections the rules require and neither of which can be back-filled at the
end credibly: `## Qodo Code Review Evidence` (merged-PR link marked TODO until PR #1 lands) and an
**AI assistance disclosure** naming Claude Code and Qodo, with the note that AI-authored commits
carry a `Co-Authored-By` trailer so the split is visible in `git log`. Glossary gained ColdCall,
TrueForge, Qodo and "the three beats"; the LOCKED onboarding prompt now names the project and
points at the repo (logged in `GOVERNANCE.md`).

Blocking on Mulaydm10, in priority order: **install Qodo on the repo** (`Q-0005`, only a human
with repo admin can), the ColdCall idea (`Q-0001`), a model provider key (`Q-0003`), a Daytona
key or a verdict on the local sandbox fallback (`Q-0004`), roster + registration (`Q-0006`).

---

### 2026-08-27 06:55 CEST — Mulaydm10 + Claude (Qodo live, first review resolved)

**Qodo installed** (`Q-0005` resolved). Mulaydm10 signed in and authorised the GitHub App;
installation `Mulaydm10 | Qodo-code-review` reports **Connected / Healthy** with the code-review
toggle on for `ColdCall`. Access was granted across all 30 repos on the account rather than
scoped to this one — deliberate, reversible at github.com/settings/installations, and noted here
so nobody is surprised later.

**First review on PR #1** (triggered with `/agentic_review`, since the PR predated the install):
**4 findings, all Medium, no High.** All four were valid and **all four were fixed rather than
dismissed**:

1. `COMPETITION.md` described the San Francisco day (2026-08-29) in the past tense on 2026-08-27
   — a real factual error that could have cost us an in-person option that is *still two days
   away*. Rewritten as upcoming, with the separate Luma registration called out. LOCKED-file
   edit, logged in `GOVERNANCE.md`.
2. `notes/judging_alignment.md` still marked the public-repo gate "Missing" after this very PR
   created the repo. Now **Done**, pointing at the real URL.
3. Same table marked the AI-assistance disclosure "Missing" while the same PR added it. Now
   **Done**.
4. `README.md` claimed unconditionally that Qodo reviews every PR while `STATE.md` said it was
   not installed. Split into **Policy** (what we always do) and **Status** (what is true today) —
   which is the honest shape regardless of install state, and worth keeping.

Worth recording: three of the four were *staleness* bugs — docs describing a world that changed
while the PR was open. That is the failure mode this repo's STATE-vs-worklog split exists to
prevent, and Qodo caught it in the one place the split doesn't reach: a table inside a PR.

---

### 2026-08-27 07:20 CEST — Mulaydm10 + Claude (stack installed, configured, verified)

The required tech stack was supplied and is now installed, configured and — the part that
matters — **verified by use rather than by reading documentation**. Two research agents ran in
parallel against the live APIs and the running harness's own OpenAPI spec while the Python
side was built inline.

**Three things in the plan turned out not to be true.** Finding them now cost an afternoon;
finding them on submission day would have cost the submission.

1. **The VCC-CPLD dataset (Zenodo, "445K real cold-chain records") does not exist.** Zero hits
   for the exact identifier on Zenodo's API; broader searches surface only market reports and
   electronics documentation where CPLD means Complex Programmable Logic Device. Substituted
   Zenodo 7907515 "Shipments Sensors readings" (DOI 10.5281/zenodo.7907515, CC-BY-4.0, ~402 MB
   of real per-reading telemetry), verified resolving and verified parsing. `ADR-0003`.
   We do **not** claim 445 000 records, because we have not counted them.
2. **TrueForge has no named-subagent registry.** `AgentSpec` has no such field; the only
   mechanism is `config.dynamic_sub_agents`, where the root agent writes each subagent's
   instructions at runtime. Subagents also share the root's tools and **cannot nest**. So the
   four specialists become a pattern in the instructions rather than four config objects —
   which is the harness working as designed, and using it as designed is what the rubric
   rewards. `ADR-0004`.
3. **There is no configurable local sandbox.** The boot log's "Local sandbox fallback is
   available" line is misleading: `SandboxProviderManifest.type` is the single-value enum
   `["daytona"]`, and `GET /settings/sandbox-providers` 404s until one is configured. Since
   **skills require a sandbox**, a Daytona key now blocks two judged features at once.

Two smaller corrections worth recording because they cost real time: `require_approval_for_tools`
lives on each `mcp_servers[]` entry, not at the top level of `agent.json`; and `PUT` goes to the
**collection** route (`/api/v1/settings/skills`), not `/settings/skills/{name}` — the per-name
route is read-only and 404s on a write, which the published docs get wrong. Everything scripted
here is written against the live OpenAPI spec, never the docs.

**What was built.** `ADR-0002` is Accepted: Node runs the harness because it must, Python
computes the regulated numbers because a verdict a model reasoned its way to cannot be audited.
`src/coldcall/` has zero required dependencies on purpose — it is uploaded into a sandbox and
must import against a stock interpreter. `mkt.py` implements mean kinetic temperature with
log-sum-exp rather than naive summation, because the exponentials involved are around 1e-16 and
precision matters exactly where a borderline shipment gets decided. `replay.py` streams the
402 MB array instead of loading it, and tolerates the truncated tail a range request always
produces. 43 tests, green, with the maths cross-checked against an independently written naive
implementation so that an optimisation cannot silently break it.

One test failed honestly and got fixed honestly: a docstring claimed ΔH/R comes out to *exactly*
10 000 K. It is 9 999.91 with the CODATA gas constant. The claim was wrong, not the constant,
so the claim changed.

**`EXP-0004`, the finding that shapes the demo.** Running the real telemetry through the real
maths against a 2–8 °C biologic label quarantines every leg immediately — the cargo is ambient
(~22–30 °C), so that comparison is trivially true and tells a judge nothing. Against a real USP
controlled-room-temperature label (15–25 °C), which is what the goods actually are and which
openFDA supplies for real products, the same data gives a genuine spread: two legs need review,
four quarantine. The borderline verdict is the one worth showing. Raised as `Q-0007`.

Harness state right now: TrueForge v0.1.4 on :8790, the `coldchain-sop` skill registered and
reading back, `agents/coldcall.agent.json` validated by the API up to the unconfigured model
provider, and `scripts/verify_apis.sh` passing 7 of 7 sources. Missing: the keys
(`Q-0003`, `Q-0004`, `Q-0008`) and the idea (`Q-0001`).

---

### 2026-08-27 07:45 CEST — Mulaydm10 + Claude (PR #3 review resolved)

Qodo reviewed the stack PR: **4 bugs, 6 rule violations**. Four fixed, four dismissed with
reasons, and two of the dismissals produced repo changes anyway because the finding pointed at
genuinely ambiguous wording even where its conclusion was wrong.

**The four bugs were real, and two of them could have corrupted a verdict.**

1. `stability_budget()` forwarded the caller's iterable to two consumers that each normalise
   independently — so a generator was exhausted by the excursion pass and the MKT pass received
   an empty series and raised. Normalise once, pass the sequence to both.
2. `to_readings()` assigned an invented minute to the final reading, which nothing measures the
   duration of, and to duplicate timestamps. On a short leg that invented exposure can move the
   MKT and therefore the verdict. Both cases are now dropped rather than defaulted. Of a
   duplicated pair the *later* reading survives, so a logger fault can never hide a hot reading —
   the only direction of that error which is dangerous.
3. `setup_trueforge.sh` counted successes and skips but not failures, and the skill step
   swallowed its own error with `|| true`, so a wholly unconfigured harness could exit 0. It now
   counts failures, reports them, and exits non-zero. A setup script that lies about success is
   worse than one that fails loudly.
4. `iter_telemetry(limit=0)` yielded one point because the limit was checked after the yield.

Re-verified the real-data pipeline after the duration fix: readings now equal points minus one,
and every verdict is unchanged. 47 tests green, ruff clean.

**Findings 5–8 were dismissed, and the wording that caused them was fixed.** Qodo learned a rule
that `ADR-####`/`Q-####`/`EXP-####`/`DEMO-####` may appear *only* in their canonical files, and
flagged every citation in `STATE.md`, the worklog and the ADRs. That inverts the scheme: the
whole point is that `grep -rn 'ADR-0003' .` recovers a decision's full trace. But the rule was
learned from a `CLAUDE.md` table terse enough to read either way, so the table now states
explicitly that it says where each ID is *defined*, never where it may be *mentioned*, and that
only the canonical file may allocate a number.

**Finding 4 dismissed, likewise with a clarification.** It held that editing a LOCKED file in
place is non-compliant even with an audit row, and wanted "a generated replacement or versioned
synchronization mechanism". No such requirement exists — the audit table *is* the mechanism.
`GOVERNANCE.md` now spells out the compliant path, including that an agent may apply the
keystroke on the Main Agent's instruction when the audit row attributes it, which is delegation
of the typing and not of the authority.

**Finding 9 was right, and is the one worth reading.** It observed that the repo now contains a
fully specified cold-chain pharmaceutical agent while `VISION.md` still says the thesis has not
been supplied and must stay `TODO`. That is a real inconsistency and not a false positive: the
mission was inferred from the tech stack Mulaydm10 supplied, so it is not invented out of
nothing, but nor is it agreed. Resolved by making the provisional status explicit and traceable
rather than by arguing it away — `skills/coldchain-sop/SKILL.md` and
`agents/coldcall.agent.json` both open with a banner stating that they encode a working
assumption pending the real thesis, `STATE.md` says the same in its blockers, and `Q-0009`
tracks confirming, amending or discarding it. `VISION.md` remains untouched and empty, which was
the rule the finding was defending.

### 2026-08-27 07:55 CEST — follow-up review on PR #3

**0 bugs.** All four fixes confirmed against the final code. The six rule violations re-report
unchanged, which is expected: they were dismissed in-thread with reasons rather than fixed,
and the learned rule that produced four of them still exists in Qodo.

Briefly attempted to correct that learned rule at source, in Qodo's Review standards, so it
stops firing on every future PR. Abandoned it: the rules table does not expose its contents to
automation, and the dashboard reports 44 passed / 0 detected violations, so the rule is not
editable from there. Not worth more time — dismissing in-thread is the documented compliant
path, it is done, and the `CLAUDE.md` clarification landed in this PR may well cause the rule to
be re-learned correctly on the next one. Noting it here so nobody re-treads the same ground.

---

### 2026-08-27 08:20 CEST — Daytona: required after all (`ADR-0005`)

Reversing the conclusion of the previous entry, on Mulaydm10's direction and on evidence that
supports it.

`EXP-0007` was technically correct — standalone TrueForge does fall back to a built-in
`LocalSandboxProvider`, and with zero providers configured the harness reports both
`sandbox.enabled: true` and `skill.enabled: true`. What that finding missed is that **being
technically satisfied is not the same as being credited**. Checked against the sources a judge
will actually read:

- `trueforge.dev` states *"Daytona is the only sandbox provider supported today."* The local
  fallback appears nowhere in the documentation — it exists in the bundle only.
- The event's own kick-off guide makes "Add a sandbox" Step 5, and that step is Daytona.
- No hackathon rule names Daytona, so this is not a literal requirement. But "Control and
  safety" is one of six equally weighted criteria, and with no sandbox provider configured the
  reasonable outside conclusion is that we skipped the sandbox. Relying on a judge reading
  TrueForge's source to award that mark is not a plan.
- On the merits too: the local provider runs on the host under a sandbox root. Real isolation,
  but not a remote microVM, and the criterion asks whether generated code runs *somewhere safe*.

So: **demo on Daytona; keep the local fallback as undocumented continuity only.** `ADR-0005`
records this, and `.env.example` plus the setup script now treat `DAYTONA_API_KEY` as required
rather than opt-in.

The operational trap from `EXP-0007` survives the reversal and gets louder, because it is
counter-intuitive: the fallback applies **only when no Daytona record is stored**. A
configured-but-broken provider is strictly worse than none — the harness uses it and fails
instead of falling back — and TrueForge exposes no DELETE for sandbox providers, so recovering
means stopping the harness and clearing the row from the SQLite store. That needs rehearsing
before demo day, not discovering during one.

What the key needs: **`write:snapshots`**. The key supplied today is valid and created a real
sandbox when called directly; it fails only because `buildImage()` registers TrueForge's sandbox
image as a Daytona snapshot and the key lacks that scope. Daytona maps this to 403 and
TrueForge maps any 401/403 to "Daytona rejected the API key", which sends you looking at the
wrong thing. Daytona key permissions are fixed at creation, so the key has to be recreated. The
kick-off guide's Step 5 does say *"Create a Daytona API key with the required permissions"* —
easy to read past, and the only place the requirement is hinted at.

---

### 2026-08-27 09:15 CEST — PR #3 merged; platform work complete

PR #3 merged at 07:10 UTC (7 commits, 0 bugs on the re-review against final code). Third merge,
still zero direct pushes to `main`. Branch deleted locally and on the remote.

**Skill ref restored to `main` and re-verified.** `skills/coldchain-sop/SKILL.md` only existed on
the feature branch, so the skill registration had been pointed at that branch to work at all.
With the merge it is on `main`, the registration points back there, and a fresh session confirms
the agent still fetches and reads it — quoting *"You do not compute the verdict. The maths module
does."* from inside a Daytona sandbox. Worth recording that TrueForge fetches skills **from
GitHub at the registered ref, never from the working tree**: editing `SKILL.md` locally changes
nothing until it is pushed to that ref.

**GitHub connector: no new credential minted.** The GitHub MCP endpoint accepted the token the
`gh` CLI already holds (scopes `repo`, `workflow`, `read:org`), so that was reused rather than
creating another long-lived secret. 44 tools now exposed to the agent.

**Supabase and Stripe: the premise was wrong, and this is worth flagging loudly** because the
original plan and this repo both said "token". Both connectors authenticate by **OAuth via
dynamic client registration** (`auth.type: dcr`) — there was never an API token to generate for
either. They are registered with the correct config and returning valid authorize URLs; each
needs one human browser login. Left for Mulaydm10 deliberately: authorising means signing into
their accounts.

**`brew install git`** (git 2.55.0 at `/opt/homebrew/bin/git`). Not needed for the demo now that
Daytona is live, but it makes the local fallback genuinely usable as a continuity path — see
`EXP-0009` for why TrueForge's macOS sandbox cannot use the Xcode `/usr/bin/git` shim.

Platform work is finished. `setup_trueforge.sh` reports **4 configured, 0 failed**, and the
judged path is proven rather than asserted. **The only thing now blocking product work is the
idea itself** (`Q-0001`) — `VISION.md` is still deliberately empty, and `Q-0009` stands ready to
discard the provisional cold-chain mission if the real thesis differs.

### 2026-08-27 09:30 CEST — deferred backlog recorded before context compaction

Mulaydm10 explicitly parked the Supabase and Stripe connector logins. Recorded in `STATE.md`
under a new **Deferred backlog** heading rather than left in Blocked, because the distinction
matters to whoever reads this next: these are scheduled decisions, not obstacles. An agent that
reports them as blockers will waste a turn asking about work that has already been triaged.

The same table carries the optional items nobody should burn critical-path time on: the San
Francisco day (2026-08-29, separate Luma registration), the blog-post prize, and starring the
TrueForge repo for the free draw.

Also worth restating here because it caused a wrong ask earlier in the session: **Supabase and
Stripe authenticate by OAuth (`auth.type: dcr`), not by API tokens.** There is no token for
anyone to generate. Each needs one browser login at Settings → Connectors.

Context is being compacted after this entry. Durable state lives in `STATE.md` (current truth),
this worklog (how we got here), `experiments/experiment_log.md` (`EXP-0001`–`EXP-0009`), and the
ADRs (`ADR-0002`–`ADR-0005`). A session log with the dead ends — the things that are expensive to
rediscover but do not belong in permanent history — is at
`logs/session-2026-08-27-platform-setup.md` (gitignored).

### 2026-08-27 10:05 CEST — PR #4 review resolved

Qodo reviewed PR #4: **2 bugs, 2 rule violations.** Both bugs were valid and are fixed; both rule
violations are the same learned-rule false positive dismissed four times on PR #3.

**Bug — stale instruction in the canonical snapshot.** `STATE.md`'s "Next intended step" still
told Mulaydm10 to put the OpenAI and Daytona keys in `.env` and run `setup_trueforge.sh`, work
that the same file records as finished four sections earlier. A snapshot that sends a maintainer
to redo completed setup is worse than one that says nothing. The step now states plainly that the
harness is already working, says not to repeat the setup, and lists what actually remains.

**Bug — overstated readiness.** The previous entry said the idea is "the only thing now blocking
product work". That was wrong on its own terms: the product-label decision (`Q-0007`) is also
open, and the Supabase and Stripe connector logins still gate creating the full agent. This
worklog is append-only, so the earlier entry stands as written and is corrected here instead —
that is the point of the append-only rule. `STATE.md`, which is the file that must be right about
*now*, was also carrying the connectors in **both** its Blocked list and its Deferred backlog
table, saying two different things about the same work in one file. Blocked now holds only the
idea and the label question; the connectors are named once, under Deferred, with a line in
Blocked explaining why they are not there.

**Two rule violations dismissed, again.** Qodo rule 2936598 reads the stable-ID table in
`CLAUDE.md` as confining every `EXP-####` and `Q-####` mention to its canonical file. `CLAUDE.md`
says the opposite in as many words: the table records where each ID is *defined*, never where it
may be *mentioned*, and citing IDs from anywhere is the entire point of the scheme — a rule that
confined mentions would make `grep -rn ADR-0003 .` return one file and destroy the traceability
the IDs exist for. Dismissed in-thread with that reason. It will re-report while the learned rule
persists; the clarifying paragraph landed in PR #3 and has not yet retrained it.

### 2026-08-27 10:40 CEST — the inferred mission was cleared (`ADR-0006`)

Mulaydm10 asked, before handing over the idea, whether the repo carried assumptions about it —
explicitly so that neither the repo nor the agent reading it would bias the real thesis. It did,
in twenty files. They directed that the idea-derived ones be removed.

**The origin matters, and the first answer given was too simple.** It was not purely a guess from
the project name. The tech stack Mulaydm10 supplied named a *"VCC-CPLD dataset (445K real
cold-chain records)"* and openFDA drug labels, so "cold-chain" traces back to their own input.
What was invented on top of it was the **mission**: mean kinetic temperature, USP <1079> stability
budgets, a release/review/quarantine verdict, a quality team signing a deviation record. None of
that was asked for. The same stack also named Stripe test-mode — which a pharmaceutical QA agent
has almost no use for, and which should have been read much earlier as a signal that the real idea
was something else.

Removed: `mkt.py`, `replay.py`, their 45 tests, `skills/coldchain-sop/SKILL.md`, and the agent's
`instructions`. Kept: the harness, the Daytona sandbox, the connectors and their approval gates,
the Qodo loop, both scripts, the `uv` toolchain, and the dependency-free constraint on the sandbox
payload — none of which depends on what ColdCall turns out to be.

Two judgement calls worth recording. **`ADR-0003` and the verified dataset stay**, even though the
ADR says "cold chain": it was Mulaydm10's input, the substitution was real work, and rewriting a
historical ADR to match a later reset would falsify the trail. And **`coldchain-sop` was replaced
rather than deleted** — the git-backed skill mount is a judged capability proven in `EXP-0008`,
and deleting the only skill would break the registration. `skills/repo-evidence/SKILL.md` carries
the repo's actual evidence rule instead, which holds whatever the idea is.

The test count drops 47 → 2, and that is the honest number rather than a regression: 45 of them
tested a mission nobody agreed to. `tests/test_package.py` keeps the canonical command green and
fails if domain logic reappears before `VISION.md` is real.

Also fixed while in the manifest: `model.name` was `openai/gpt-5-6-sol`, TrueForge's catalog
preset, which does not exist on this account's key (`EXP-0008` recorded that and the manifest was
never updated). It would have failed on agent creation. Now `openai/gpt-5`.

Restoring is one command if the thesis turns out to be cold-chain after all —
`git checkout 3e01090 -- src/coldcall tests skills/coldchain-sop` — which is why removal was
preferred to an `attic/` directory. Equally recoverable; only removal stops it pulling on what
comes next. `Q-0009` closes as discarded. `Q-0001` is now the only real blocker.

`tests/README.md` is LOCKED and its layout table still names the deleted test files. Proposed to
Main Agent, not applied.

### 2026-08-27 12:30 CEST — the thesis arrived, and it is cold-chain after all

Mulaydm10 supplied `coldchain-build-spec.md` (fetched from the omen box). It specifies a
pharmaceutical cold-chain **disposition** agent: MKT per USP <1079>, stability-budget
consumption, a release / quarantine-retest / destroy verdict, a human approval gate before any
irreversible action, and real executed downstream actions.

So `ADR-0006` was a false alarm — the inferred mission was close to the real one. It cost one
command to undo (`git checkout 3e01090 -- src/coldcall tests skills/coldchain-sop`) and it
bought something real: the spec settles which parts were Mulaydm10's and which were invented,
and the reset is why the restored code was reconciled against the spec rather than the spec
being bent to fit code that happened to already exist.

**What the restore brought back, and what changed on top.** `mkt.py` survives as the primitives
layer and is deliberately *not* replaced by the spec's Appendix C reference implementation: the
restored version is time-weighted, uses log-sum-exp, and validates its inputs, where Appendix C
is unweighted and sums exponentials directly. What Appendix C had that we lacked is the
decision layer, and that is now `disposition.py`: the three-way verdict vocabulary the incident
record and the demo script both speak, plus the Arrhenius potency estimate.

**Three deliberate deviations from the spec, each with a reason:**

1. **Chart is stdlib SVG, not matplotlib.** `src/coldcall` must import against a stock
   interpreter because it is uploaded into the sandbox (`ADR-0002`); matplotlib means a pip
   install inside a jail with a 60 s exec timeout and a network the harness docs warn about.
   SVG is text, embeds in the generative-UI board, and survives the file-download endpoint.
2. **No `docker-compose.yml`.** Docker is not installed here, so shipping one would mean
   shipping an untested one-command quickstart. `npx` standalone is the verified route.
3. **Replay engine in Python under `uv`, not TypeScript.** `ADR-0002` settled that there is no
   `package.json`; Node runs the harness and nothing else.

**The verdict fell out of real data rather than being tuned to it.** The allowance policy (6 h)
was fixed before the leg was scored. Device `DD:33:04:13:34:CD` from Zenodo 7907515, 20.3 h,
64 readings, one contiguous 231.7 min excursion peaking at 27 °C, judged against amoxicillin's
real openFDA label (set_id `e13cafe2-…`, 20–25 °C, excursions permitted 15–30 °C): MKT
24.54 °C, 64.35% of budget consumed, verdict **`quarantine_retest`**. That is the spec's own
demo verdict, arrived at independently.

**One thing the spec assumed that is not true, now verified rather than suspected.** No real
openFDA label states a permitted excursion *duration* — labels that pair an excursion range
with a number of hours are describing post-reconstitution in-use stability, a different
allowance entirely. USP <659> defines CRT by temperature and MKT, not by a time ceiling. So the
"hours out of range" figure is ours. `disposition.py` surfaces it as a policy input, stamps
`ColdCall demo policy — not a regulatory limit` into every emitted record, and the README and
narration must keep saying so.

`tests/test_package.py`'s `ADR-0006` guard is retired here, exactly as its own docstring
instructed: the thesis arrived, so the tripwire has done its job. What replaces it is the
constraint that outlives the reset — a subprocess test with `-I` that proves the sandbox
payload imports against a stock interpreter, so an accidental `httpx` import fails here rather
than mid-demo.

72 tests green, ruff clean. `VISION.md` is LOCKED, so the thesis is proposed in
`proposals/VISION.md` rather than written directly.

### 2026-08-27 11:15 CEST — one incident, end to end, with a receipt

The whole judged path now runs: excursion → four strands in parallel → deterministic math in a
Daytona microVM → generative-UI evidence bundle → **approval gate** → executed action with a
real receipt. Recorded as `EXP-0010` and `EXP-0011`.

**The verdict reproduces exactly.** The agent cloned the repo inside the sandbox, ran
`python -m coldcall.cli`, and returned `quarantine_retest`, MKT **24.54 °C**, budget **64.35%** —
byte-identical to the local run. That is the auditability claim demonstrated rather than
asserted: same inputs, same arithmetic, different machine.

**The gate works in both directions.** On deny the agent reported the denial and stopped without
retrying. On allow it created branch `incident/INC-VCC-118-A2231-20260827T090841Z` and committed
the 5 984-byte deviation record as `1c859fc` — a real, checkable audit trail on the public repo.

**Four bugs stood between here and there. Three were mine.**

1. A session body is `{"agent":{"spec":…}}`, not `{"agent":…}`. The build spec's Appendix A.6 is
   wrong and the API only says "Invalid input at agent".
2. Compaction nests under `config.context_management.compaction`.
3. `turn.created` carries `turn_id` **alongside** its own event `id`. I resumed the approval with
   the event id, so the gate fired correctly and the answer went nowhere — HTTP 404.
4. `ToolCallRef` carries only `{id, source_event_id}` — no name, no arguments. The first working
   gate therefore printed `?` and `{}` and asked a human to approve it. That is exactly the
   rubber stamp the SOP condemns, so the driver now resolves each pending call back to the
   `model.message` that requested it.

**And one in our own script, which cost the most time.** `setup_trueforge.sh` loaded `.env` with
`set -a`, which overrides variables the caller already exported. `.env` pins
`COLDCALL_SKILL_REF=main`, so passing a branch ref was silently ignored — and reported `ok`,
because the PUT succeeded with the wrong ref. The run then failed with
`path 'skills/coldchain-sop' not found in repository`, because `main` has not had that skill
since `ADR-0006`. Now uses standard dotenv semantics: the environment wins over the file.

**Two things the agent got right that are worth recording**, because they are the safety story
working rather than being described. When the module failed to import on an earlier run, it
**reported the error as the finding instead of estimating a verdict**. And when the Exposure
strand had no source for the shipment's units and value, it **listed what it needed rather than
inventing figures** — which is why the turn now points it at `replay/seed.json` for a real source
to cite.

**One honest caveat for the demo.** The git-backed skill fetch is a cold-start race against
Daytona's network, and each strand gets its own sandbox, so each rolls the dice separately. It
failed once and cleared on retry. Rehearse twice; do not assume a clean first run.

### 2026-08-27 13:45 CEST — three rounds of Qodo, and what the repeats were actually telling us

Qodo reviewed all four milestone PRs and raised **26 findings across three rounds**. 23 fixed,
3 dismissed in-thread with reasons. Several were genuinely serious, and the pattern in the
repeats matters more than any individual fix.

**The one real regulatory bug.** `disposition()` ignored the label's *permitted excursion
range* entirely. A real label states two bands — "store at 20–25 °C" **and** "excursions
permitted to 15–30 °C" — and only the first was reaching the maths. So an 18 °C reading, which
the label explicitly permits, was quarantining as a **freeze event**; and a brief 35 °C spike
could release whenever MKT and the time percentage stayed low. Wrong in both directions. Both
bands now flow through: time outside the storage range spends the budget, time outside the
permitted range is a condition the label makes no claim about and quarantines regardless.

Subtlety that cost a test cycle: the envelope rule must fire **only when a label actually
states a wider range**. Defaulting it to the storage band made every excursion "beyond the
envelope" and left the budget rules unreachable.

**The one real safety bug.** The approval gate could authorise a call whose name and arguments
the operator never saw — `resolve_pending_calls()` returned a `<could not resolve>` placeholder
and the driver still offered `allow`. That is worse than having no gate, because it *looks*
like oversight while manufacturing consent. It now fails closed. Immediately proved its own
worth by denying a legitimate action, which exposed that my resolver was keyed to a single
turn while the requesting `model.message` had landed in another — fail-closed turns a lookup
bug into a denied action rather than an unreviewed approval, which is the right direction, but
it means resolution has to actually work or the gate is unusable.

**Three findings were regressions from my own previous fixes.** Making telemetry ingestion
idempotent with `INSERT OR IGNORE` silently swallowed NOT NULL and CHECK violations too.
Tightening the timestamp rules rejected telemetry whose readings all carried explicit
durations, over a field nothing was going to read. Adding a leg-loading handler caught
`JSONDecodeError` but not the document's shape. Fixing a bug is where the next one gets in.

**`restart_proof.sh` needed three rounds, and that is the finding.** Every version shipped a
check that could pass without proving anything: first it compared 0 verdicts against 0; then
equal cardinalities, so replaced content passed; then five hand-picked fields, so a change to
any sixth passed. The common cause was **enumerating what matters**. For an integrity check the
only safe list is "all of it" — it now hashes whole event objects, and every read goes through
a helper that aborts rather than letting a failed fetch become the SHA-256 of an empty string.

**Two things dismissed, with reasons.** The "thesis is fabricated" rule violation fired
correctly on the evidence in the diff but on a false premise: the thesis *was* supplied, as a
build spec. `VISION.md` reads `TODO` only because it is LOCKED and an agent may not edit it —
the thesis is proposed in `proposals/VISION.md` for a human to apply. Writing it directly into
`VISION.md` is exactly what that rule should prevent.

### 2026-08-27 13:50 CEST — the Daytona quota trap (`EXP-0012`)

Worth its own entry because of how well it hid. Live runs began failing with
`git ls-remote failed ... Recv failure: Connection reset by peer` — identical to the transient
cold-start race already recorded in `EXP-0011`. It was not the network. A bare probe turn
returned the real cause: **`Total disk limit exceeded. Maximum allowed: 30GiB.`**

Every incident spawns a sandbox for the orchestrator and one per strand — five or six per run
at ~3 GiB each — and setup was registering Daytona with a five-day delete timer. The account
had reached **16 sandboxes / 48 GiB**.

The dangerous part is the disguise. A connection reset invites a retry, which fails the same
way, so the time goes into networking. Meanwhile the agent proceeds **without its SOP skill**
and produces a plausible-looking incident that never reaches an approval gate — a demo silently
skipping its own safety beat.

Fixed forward: `scripts/daytona_gc.sh` diagnoses and reaps (dry-run by default, never touches a
running sandbox); setup now sets 15-minute archive / 2-hour delete; and `replay/incident.py`
retries once past the genuine cold-start race and **refuses to present a run whose skill never
loaded**. Clearing the existing 45 GiB backlog needs Mulaydm10 — the DELETE was blocked by the
local permission classifier as a destructive external action, which is the correct call.

### 2026-08-27 14:10 CEST — M1 merged; the fourth review round, and what it caught

**PR #6 merged at 11:43 UTC** by Devin, after Qodo cleared it. `main` now carries the
deterministic disposition maths. #7 auto-retargeted to `main`; the rest of the stack follows.

The fourth round produced the two findings I would least like to have shipped, and neither was
in code I would have re-read.

**A retry that could repeat an irreversible action.** I added a single retry to `incident.py`
so the cold-start skill-fetch race would not eat a take. It keyed only on "did a sandbox
fail" — but a run can report one strand's sandbox failure *and* still reach an approval gate.
So under `--auto allow`, a retry would create the branch again, commit again, notify again. I
added reliability to a demo and handed it the power to double-execute the exact class of
action this entire project exists to gate. Retry is now conditional on nothing having been
approved, and a run that is untrustworthy exits non-zero instead of contradicting its own
warning.

**A predictable temp file in a destructive path.** `daytona_gc.sh` wrote sandbox ids through a
fixed `/tmp` path before reading them back to issue `DELETE`s — a symlink there truncates
someone else's file, and replaced contents feed attacker-chosen ids into irreversible deletes.
Ids now live in a shell array.

**Two failures-become-successes in the same script, one hiding the other.** The GC parser
rejected only a body whose `statusCode` was exactly 401, so a 403 or a 500 read as "no
sandboxes" and the script reported success. Fixing that to assert on HTTP status exposed the
same shape one scope up: `die` inside a command substitution exits only the *subshell*, so the
new guard fired, printed, and the script sailed on with an empty list. Both verified from the
failure side now.

**And the leg loader turned out to be three findings wearing one hat.** Validating readings in
isolation was never enough, because `replay` reads the series *in file order*: timestamps have
to parse, be strictly increasing, and not repeat. The duplicate case is the subtle one — the
store keeps only the first reading at an instant while `replay` evaluated every raw
temperature, so an incident's peak could rest on a reading absent from the audit telemetry its
own verdict is computed from.

Rejected rather than sorted or deduplicated, both times. Silently reordering or picking a
winner among someone's telemetry is its own integrity question, and the caller knows which of
the two records is real.

### 2026-08-27 14:55 CEST — the agent can now answer "why", and the answer is not "it was hot"

The build spec lists weather on route as real data and its architecture diagram feeds it into
the incident, but nothing in the agent flow used it. The SOP even promised that explaining
*why* it warmed is where the agent adds value the maths cannot — with no tool to do it. That
was the largest remaining gap against the spec, and it is now closed (`EXP-0013`, PR #10).

**The dataset had GPS all along.** The raw records carry `measurements.gps`; our device has 15
fixes clustered at 39.456 N, −0.347 E — Valencia. So the weather can be fetched for *where the
shipment actually was*, which is the only version of this worth doing: an invented location
produces an invented root cause.

**And the answer is the interesting one.** Open-Meteo's ERA5 archive for 2021-11-09 at that
point gives an ambient peak of **17.7 °C**, 13–17 °C through the excursion window. The
consignment reached **27 °C** — a median **12.6 °C above outside air**, across **14 of 14**
matched excursion readings. Attribution: **`containment_failure`**, not environmental exposure.

That distinction is the whole point of building it. The two outcomes lead to *opposite*
corrective actions — one is about the lane, the schedule and dwell time; the other about
packaging, the reefer unit and loading procedure. A deviation record that says "the shipment
reached 27 °C" and stops has skipped the only part an investigator can act on, and would have
sent this one to the wrong place.

Three design choices worth keeping in mind if this is ever extended:

- **Opt-in and never fatal.** A weather lookup failing must not cost a verdict already
  computed, so the failure lands inside the document rather than being raised. Without the
  flags the output is byte-identical to before.
- **`undetermined` is a first-class outcome.** Below half coverage it refuses to attribute and
  says why. Forcing a cause out of two matched readings is how a bad CAPA gets written.
- **Only out-of-band readings are attributed**, and matching is to the *nearest* hour rather
  than the preceding one. Including in-band time would drag the median toward the ambient
  baseline; rounding down would lag the ambient curve behind the telemetry and bias every gap
  in the same direction. Both are quiet errors an attribution should not rest on, and both are
  pinned by tests.

The limits are stated wherever the number appears — point weather, hourly, shade temperature,
moving cargo — and the 5 °C threshold that separates the two attributions is ColdCall policy,
not a regulatory value.

### 2026-08-27 16:40 CEST — M8/M9: the rehearsal that caught the demo not working

The stack landed, so this session was pre-flight: fresh-clone timing, walking `DEMO.md` as
written, and rehearsing the incident run. The rehearsal is what earned the session.

**The first two rehearsals never reached the approval gate.** That is the demo's centrepiece
and the whole control-and-safety claim, and it failed twice for two different reasons that
share a cause (`EXP-0017`).

Rehearsal 1 completed — 358k tokens, 476 s — and the orchestrator ended the incident
*believing the module had never run*, refusing to state a verdict it did not have. It was
right to refuse: a strand **had** run the module and produced `quarantine_retest` / 24.54 °C,
and the result never reached the parent. The SOP held; the run was still useless.

Rehearsal 2 was cancelled by the harness at `server-execution-timeout`, 190k tokens, before it
could act at all.

The shared cause was too much work before the action, on a critical path that depended on a
strand's result finding its way home. Three prompt-level changes, none touching the
deterministic layer: **the orchestrator now runs the module itself, first, before spawning
anything**; strands are told to answer in under 200 words *with the reason given*, that an
essay costs the run its gate; and the instruction says plainly that an incident which runs out
of turns before the gate has failed however good its analysis was.

Rehearsals 3 and 4 both gate. Deny 168 s, allow 191 s, and the allow path left commit
`6ccb0bd` — a real 11-section deviation record on the public repo.

A third failure surfaced before either: `--repo-ref` defaults to the current branch, so an
unpushed branch sent the sandbox to a ref that does not exist. Five strands each honestly
reported the clone failure. The driver now checks the ref against the remote and exits 2 with
an explanation rather than burning eight minutes discovering it.

**What a fresh-clone audit found**, beyond stale numbers: `DEMO-0001` named only two required
keys, but steps 6 and 7 need `GITHUB_TOKEN` — without it the connector is skipped and the
approval gate has no tool to call. Following the document literally produced a run whose
centrepiece silently did not happen. That is now called out in `DEMO.md` and `.env.example`,
along with where each key actually comes from.

**The AI-assistance disclosure was understating things and omitting a tool.** It described
Claude Code as a pair-programmer used for "research, documentation, and scaffolding" when it
wrote the large majority of the repository, and it did not mention Devin at all. Rewritten to
say so, with a number that can be checked rather than taken on trust: 65 of the 67 non-merge
commits on `main` carry the `Co-Authored-By` trailer, verifiable with one `git log --grep`.
The rules require disclosure; gesturing at it is not disclosure.

Pre-flight otherwise green (`EXP-0018`): Daytona reaped 48 GiB → 9 GiB, clearing the quota trap
that had been blocking live runs; setup idempotent across two consecutive runs; `verify_apis`
8/8; restart proof passing on the fresh incident with both digests stable.

Everything left needs a human, and none of it was attempted — the governance edit to
`VISION.md`, three optional OAuth logins, and the video. Each is a row in `STATE.md` with the
exact steps.

## 2026-08-25 08:25 UTC — Devin: corpus benchmark, part 1 (harness + zenodo-ll1)

Branch `feat/corpus-benchmark`. New surface: `corpus/` — the deterministic CLI run unmodified
over many real recordings from public datasets, as a robustness benchmark (see
`corpus/README.md` for what it is and, more importantly, what it does not claim). The runner
invokes `python -m coldcall.cli` as a subprocess — the exact sandbox entry point — and compares
every verdict against reviewed regression pins in each dataset's `expected.json`.

First dataset: the demo's own Zenodo 7907515 source, widened from one hand-picked leg to a
20 MB range sample — 26k readings, 7 devices, **47 legs cut on >3 h logger silences, all three
verdicts represented (10 release / 10 quarantine_retest / 27 destroy), cross-check agreeing on
every leg, 0 errors**.

One finding worth recording: the demo's `VCC-118` leg was bounded by the demo sample's last
byte, not by a logger silence — in the wider sample the same journey runs on to 2021-11-14 and
scores `destroy` over its full span. The demo verdict is correct for the window it replays and
is now regression-pinned by the corpus as its own leg (`…-demo-window`), next to the full
journey. Documented in `corpus/datasets/zenodo-ll1/DATASET.md`.

236 tests green (+6 for the harness: leg cutting, duplicate-instant rule, runner error rows),
ruff clean. Next: strawberry / mango air-cargo / COVID ULT / SOFIE datasets via delegated
sessions on `corpus/<slug>` branches, integrated and re-run here.

### 2026-08-28 16:20 CEST — the build closed; PR #11 merged and the project moved to its demo phase

`main` is at `7aca120` with **eleven PRs merged and zero direct pushes**. No open PRs, nothing
in flight. 230 tests green, ruff clean, `verify_apis.sh` 9/9.

**What the last three review rounds were actually about**, because the pattern is worth
carrying forward more than the individual fixes: **each finding was a defect in something added
to fix the previous finding.** A GitHub preflight was added because the credential whose
absence is silent went unchecked — and it checked `/user`, proving identity where
*authorization* was needed, so a minimally-scoped token passed green and the post-approval
commit would have failed. Fixing that, a fork-friendliness change pointed the check at
`COLDCALL_SKILL_REPO` while `replay/incident.py` wrote to a hard-coded repo — reintroducing the
exact divergence the check existed to prevent. Skill source and audit target are different
questions; borrowing one for the other was the bug.

Both are now behind one `COLDCALL_ACTION_REPO` read by both sides, so there is nothing left to
drift. The habit that caught these was verifying every fix **from the failure side** — pointing
the check at a repo I can read but not write, and confirming it fails — rather than confirming
the happy path.

**M8/M9 in one line each.** Fresh-clone audit found `DEMO-0001` named only two required keys
while steps 6–7 need `GITHUB_TOKEN`, so following the document literally produced a run whose
centrepiece silently did not happen. The AI-assistance disclosure was understating its subject
and omitted Devin entirely; it now states the scale with a number that can be checked — 65 of
67 non-merge commits carry the trailer. Pre-flight is green across the board and recorded as
`EXP-0018`.

**The rehearsal earned the session** (`EXP-0017`, `EXP-0019`). The first two runs never reached
the approval gate — one because the orchestrator ended the incident believing the module had
never run when a strand *had* run it and the result never came home, one cancelled by the
harness at `server-execution-timeout`. The fix was to have the orchestrator run the module
itself before spawning anything: a verdict that lives only inside a strand is one it may never
receive. Then the wording that fixed the timeout made the model skip the fan-out entirely, so
that was reworded to say the two are not a trade.

**Everything remaining needs a human**, and none of it was attempted: the governance edit
applying `proposals/VISION.md` to the LOCKED `VISION.md`, the video, and four optional items —
two OAuth connectors (Supabase, Stripe), a Slack **webhook**, and the prize-track actions. `STATE.md` carries the list with exact steps, plus the two rehearsal traps that will eat
a take — reap Daytona first, and rehearse until one run shows both the fan-out and the gate.

## 2026-08-28 — 16:30 UTC — Devin: five-dataset corpus integrated, 206 legs, 0 FAIL/DRIFT (PR #13)

Fixed Qodo's three findings on #13 (all verified real): the `-demo-window` leg held 76
readings, not DEMO-0001's 64, because the source JSON is not time-ordered — a new
`-demo-input` leg reconstructs the demo's exact input from its 3,000,001-byte sample range
(64 readings, MKT 24.54 °C, `quarantine_retest`, pinned + asserted); a pinned leg the adapter
stops emitting is now a FAIL row, not a silent shrink; `subprocess.TimeoutExpired` becomes a
structured error row instead of aborting the corpus.

Then merged the four delegated dataset branches (`corpus/strawberry`, `corpus/mango-aircargo`,
`corpus/covid-ult`, `corpus/sofie-foodchain`) — purely additive, no shared-core change needed
by any of them — fetched, adapted and ran everything locally: **206 legs across 5 datasets,
0 FAIL/DRIFT, cross-check agreeing on every leg**. 287 tests green, ruff clean. See EXP-0020
for what the corpus showed. Awaiting Qodo re-review on #13.

## 2026-08-28 — 17:05 UTC — Devin: Qodo round 2 on #13 — strawberry fetch hardening

Qodo's follow-up review on #13 re-listed the three already-fixed findings (demo-input fidelity,
dropped pins, timeout — all fixed in 4796af5, status posted in-thread) and raised two new ones,
both in `corpus/datasets/strawberry/fetch.sh`, both valid and fixed in d90c617: (1) the
parquet→csv converter now writes each CSV to a temp path and `os.replace()`s it, so an
interrupted conversion can never leave a truncated CSV that later runs accept as done; (2) the
converter runs through the project environment (`uv run --project --python 3.12`) instead of
`--no-project`, keeping pandas/pyarrow as an ephemeral `--with` overlay. Re-verified end to end:
CSVs deleted and regenerated via fetch, full corpus 206 legs / 0 FAIL/DRIFT, 287 tests, ruff
clean. Awaiting Qodo's next pass, then a human merge.

## 2026-08-28 — 19:00 UTC — Devin: PR #13 merged; README gains the corpus results (PR #14)

Mulaydm10 merged #12 (docs handoff) then #13 (the corpus) — the merge conflict between the two
on `STATE.md`/`worklog.md` was resolved on the corpus branch first (046166c: STATE reconciled
to the demo-phase snapshot with #13 as the one open code PR; worklog entries interleaved
chronologically, nothing edited). `main` now carries all thirteen PRs, 287 tests green.

New branch `docs/readme-corpus-results` (PR #14): the top-level README had no mention of the
corpus, so judges reading only the README would miss the breadth evidence. Added a "Run wide,
not just deep" section — 206 legs / 5 real datasets / 0 FAIL/DRIFT, per-dataset verdict
breakdown (counts taken from `corpus/results.json`, not from memory), the demo-input pin, and
the regression-pins-not-ground-truth caveat — linking to `corpus/RESULTS.md` and
`corpus/README.md`. Documentation only; no code change.

## 2026-08-28 — 19:35 UTC — Devin: VISION.md applied on Mulaydm10's instruction (PR #15)

Mulaydm10 instructed in chat ("solve this first") that the standing proposal be applied, so
`proposals/VISION.md`'s body now replaces the all-TODO scaffold in the LOCKED `VISION.md`,
verbatim. The edit is logged in `GOVERNANCE.md`'s audit table as Mulaydm10 (via Devin, on
their behalf), matching the existing "via Claude" precedent; `Q-0001` is resolved in
`research/open_questions.md`. This closes the gap where a judge following the read order hit
"the thesis is TODO" before any code — and the finding Qodo re-reported on every PR.
Documentation only; human merge still required.

## 2026-08-29 — 07:50 UTC — Devin: fresh-clone audit; stale judge-facing docs fixed

A full adversarial re-audit against the judging rubric, from a fresh clone (nothing reused
from earlier checkouts): `uv sync --group dev` → `uv run pytest` → 286 passed, 1 skipped
(the zenodo-ll1 raw-sample pin, which needs `fetch.sh` first — raw data is gitignored by
design), `ruff check` clean, README/DEMO relative links all resolve, no bare excepts in
`src/coldcall/`, `setup_trueforge.sh --dry-run` fails only for the expected reason on a cold
machine (no TrueForge at :8790).

The audit found one class of real risk: judge-facing docs still describing the pre-thesis
repo. CLAUDE.md's opening line said "what it does is TODO, the idea is pending" and its
layout table said `src/coldcall/` is "currently empty of domain logic" with a 2-test suite —
false since PR #7 and directly contradicting the merged VISION.md. README's Qodo-dismissal
note still said in the present tense that `VISION.md` reads TODO, false since PR #15 merged.
STATE.md still described #15 as the one open PR. All fixed in this entry's branch;
documentation only, no code change.

## 2026-08-30 — 10:40 UTC — Devin: demo frontend committed to the repo (`frontend/`)

The frontend built over the last sessions moves from a VM-local working copy into the repo,
under `frontend/`. Eight routes (Home, Overview, How it works, Console, Incidents, Evidence,
Decision room, Sources) in a single-page site with the Modernist design system; a stdlib-only
local server (`frontend/server.py`) serves it over the real `src/coldcall` SQLite store —
bootstrap seeds from `replay/seed.json`, replays the recorded demo leg, and records the
verdict computed by the same deterministic CLI the sandbox runs. Allow/Deny in the Decision
room write real receipts and survive restarts. The site degrades gracefully with no API
(recorded DEMO-0001 fixtures), so it can also be hosted statically — `frontend/vercel.json`
included for a Vercel deploy. Runtime store files are gitignored. Verified both modes before
commit: live (`/api/state` returns the persisted verdict, MKT 24.54 °C, gate open) and static
(page renders, Decision room + Console + live map work, only the expected `/api` 404s).

## 2026-08-30 14:05 UTC — Qodo review of PR #17: seven findings addressed

Qodo's `/agentic_review` on PR #17 returned 5 bugs + 2 rule violations; all addressed on the
branch. `frontend/server.py`: a decision is now final — any second `POST /api/decision` after
an allow *or* a deny returns 409 (deny was previously re-decidable); `Content-Length` is
validated (400/413) with a 4 KiB body cap, non-object JSON rejected, and 500s no longer leak
exception text; signer/reason are normalized (length caps, the ` - ` audit delimiter is
neutralized to an en dash) so reload hydration is lossless. `frontend/ColdCall.dc.html`: the
decision client now distinguishes live from static — in live mode a non-OK/failed POST shows
"the store did not record the decision" instead of faking success; static fallback unchanged.
Fixture text aligned to the canonical run (MKT 24.54 °C, 64.35 % — was 24.51/64.3 from an older
draft). `frontend/README.md` + `STATE.md`: launch documented as `uv run frontend/server.py`.
Verified: ruff clean, full pytest green, live curl checks (400/413/409 paths, tricky ` - `
names round-trip), fresh store boots gate-open.

## 2026-08-30 14:40 UTC — Qodo follow-up review on PR #17: two Mediums fixed

Follow-up review on a1e107f flagged two Mediums, both fixed: `by`/`reason` must now be JSON
strings (arrays/numbers/objects → 400, no coerced audit attribution), and the decision
handler's generic 500 now prints the traceback to stderr so store failures are diagnosable
from server output. Verified live: 400 on non-string fields, allow → 200, second decision →
409, ruff clean.

## 2026-08-30 15:35 UTC — demo video produced end to end (Devin)

Live TrueForge rehearsal verified first (session 01m19b3zrf8mw8kjrxd78wrnt6): two runtime bugs
fixed on the VM (sandbox proxy socket had to be re-bound after filesystem mounts; the git-skill
sparse-checkout needed `/usr/share` in the sandbox read allowlist), after which skills mounted,
specialists ran, the run paused at the approval gate, and `--auto allow` produced the branch +
deviation record + PR. No Daytona key in this environment — local sandbox fallback used, which
the competition permits (TrueForge is the mandatory harness; Daytona is optional).

Then the video: ~470-word narration script (10 beats following Mulaydm10's dictated flow),
OpenAI TTS voiceover (10 chunks, ~163 s), screen captured on the VM in 10 segments (home fleet
animation, Overview problem/solution, How-it-works pipeline run, Incidents/Evidence, Decision
room, Console with the live incident + map, TrueForge's own console session, the real signature
— typed name, hold-to-sign, receipt RCPT-20260830-A4F407 written by the live local API — and
Sources). Composited in Remotion (`~/demo-video-lab/coldcall-demo`): one `SEGMENTS` row per
beat (clip + narration + caption + trim/rate), rendered to
`out/coldcall-demo.mp4` — 1920×1080, 2:55, audio verified. Editable: change a row, re-render.

Recording-only mitigations were applied to the *local working copy* (finite landing playback,
reduced WebGL cost) because the VM's software renderer choked Chrome; deliberately NOT pushed —
the deployed site keeps the committed looping animation. STATE.md updated to reflect all this.
