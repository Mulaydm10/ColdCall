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
