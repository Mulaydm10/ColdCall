# PROPOSED `VISION.md` — for Main Agent (Mulaydm10) to apply

> `VISION.md` is a LOCKED governing file. This is a proposal, not an edit. Apply it by
> copying the body below into `VISION.md` and logging the edit in `GOVERNANCE.md`'s audit
> table. Everything below the rule is the proposed file content.

---

# VISION — ColdCall

> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

## The thesis

**Detection is a solved problem. The decision is not.**

Temperature sensors on pharmaceutical freight work. They log, they alarm, they escalate. What
no system automates is the question that follows the alarm: *given this exact thermal history,
is this pallet still legally releasable — or must it be quarantined, retested, or destroyed?*

Today that question is answered by a quality professional reading a chart, consulting a
product's stability data, and applying judgement, over hours to days. The pallet sits in a bay
the entire time. ColdCall does the arithmetic in seconds and hands the human a signed-off-able
evidence bundle — **and then stops, because the signature is not the agent's to give.**

## What ColdCall is

An incident-response agent running on the TrueForge harness. On a temperature excursion it:

1. opens a persistent session that **is** the regulatory incident record;
2. fans out to four specialist strands — stability, logistics, compliance, exposure;
3. computes the disposition in a sandbox using **deterministic, unit-tested, inspectable
   Python** — never an LLM estimate;
4. assembles an evidence bundle: verdict, the MKT arithmetic, the excursion chart, the value
   at risk, a drafted deviation report;
5. **halts at a human approval gate** before any irreversible action;
6. on approval, executes the real downstream actions and commits the audit trail.

## What makes it different

Prior art in this space predicts *risk*. ColdCall computes *disposition*. The distinction is
the whole project:

- A risk score is a number a model produces. It cannot be audited, reproduced by a regulator,
  or defended in a deviation investigation.
- A disposition is arithmetic with a regulatory definition behind it — mean kinetic temperature
  per USP <1079>, excursion evaluation per WHO TRS-999 Annex 5 — that anyone can re-run and
  get the same answer.

The LLM's job is to gather, orchestrate, explain and draft. **The LLM never decides.** That
separation is the safety story and the technical story at once.

## What is regulation and what is ours

Stated here because it must never blur, and because a judge will ask.

| Anchored in regulation | ColdCall's own policy |
|---|---|
| The MKT formula (USP <1079>, ICH Q1A) | The thresholds that turn a budget % into a verdict |
| The labelled storage range, from the real openFDA label | The permitted excursion **duration** in hours |
| The permitted excursion **range**, from that same label | The Arrhenius potency **estimate** parameters |
| Cumulative thermal stress over peak temperature (WHO TRS-999 A5) | Which verdicts count as irreversible |

Real drug labels state a permitted excursion *range*. Verified against openFDA: **no real label
states a permitted excursion duration.** Any "hours out of range" figure here is ours, is
surfaced as an input, and is never presented as if the label said it.

## Honest limits

- **Decision support, not a release system.** No claim is made that this makes actual regulated
  release decisions in production. A human QA director owns the release decision, and the
  approval gate exists to enforce exactly that.
- **Real recorded telemetry, replayed** — never live commercial telemetry. The dataset, the
  leg, and the selection criteria are documented in `replay/SHIPMENT.md` and `ADR-0003`.
- **The potency figure is an estimate, not an assay.** It is labelled as such in the code, in
  the emitted JSON, and on screen. A retest verdict exists precisely because the estimate is
  not good enough to release on.

## What success looks like

One shipment's story, end to end, on camera: a real excursion, a computed verdict, a human
holding the pen, real executed actions with receipts, and an incident record that survives the
server being killed mid-incident.

Not a fleet dashboard. Not a prediction platform. One pallet, decided properly.
