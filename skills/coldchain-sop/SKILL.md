---
name: coldchain-sop
description: Standard operating procedure for judging a cold-chain temperature excursion — which readings count, how the stability budget is computed, what evidence a deviation report must carry, and what must never be decided without a human. Load this before assessing any shipment.
---

> **Provisional mission — not the project thesis.** `VISION.md` is still `TODO(Mulaydm10)` and
> must stay that way until the Main Agent supplies the real thesis. What is encoded below is a
> *working assumption* derived from the tech stack Mulaydm10 supplied on 2026-08-27, which named
> cold-chain telemetry, MKT/stability maths, a quarantine write, and a `coldchain-sop` skill. It
> was built so that setup could be verified against something concrete rather than waiting idle.
> It is scaffolding to be confirmed, amended, or discarded when the thesis lands — tracked as
> `Q-0009`. Do not treat it as the agreed mission, and do not cite it as one.

# Cold-chain excursion SOP

You are assessing whether a pharmaceutical consignment is still fit for release after its
temperature record shows an excursion. Read this before you touch the data.

## The one rule that overrides everything else

**You do not compute the verdict. The maths module does.**

Mean kinetic temperature is a regulated calculation, and a number you produced by reasoning
about it is not auditable — nobody can re-derive it, and an inspector will not accept "the
model said so". Run the deterministic module in the sandbox and report what it returns:

```python
from coldcall.mkt import stability_budget
from coldcall.replay import group_by_device, iter_telemetry, to_readings

leg = group_by_device(iter_telemetry(path))[0]
budget = stability_budget(
    to_readings(leg),
    label_lower_c=...,   # from the product's own label, never assumed
    label_upper_c=...,
    allowed_excursion_minutes=...,
)
```

If the module and your own intuition disagree, the module is right and you are wrong. Say so
in the report rather than quietly splitting the difference.

## Order of work

1. **Establish the label first, from the product's own record.** Storage limits come from the
   openFDA drug label (`results[].storage_and_handling`), not from memory and not from a
   plausible-sounding default. A 2–8 °C range and a 15–25 °C controlled-room-temperature range
   produce opposite verdicts on identical telemetry. If you cannot find the label, stop and say
   the label is unknown — do not proceed on an assumed range.
2. **Load the real telemetry** for the consignment and confirm what you actually have: how many
   readings, over what span, and where the logger went silent. A gap is missing evidence, never
   proof the temperature held.
3. **Compute the budget** with the module. Record every input alongside the result.
4. **Explain the excursion** using route context — weather along the path, carrier and flight
   information, handoff points. This is where you add value the maths cannot: *why* it warmed.
5. **Write the deviation report** and only then propose actions.

## What must pause for a human

Anything in this list stops and asks, every time, no matter how confident the evidence is:

- **Quarantining or releasing stock.** A release decision is signed by a person; the agent
  recommends and evidences it.
- **Any write to the inventory or incident system.**
- **Any payment, refund, or reship order.** Money moving is never an agent's unilateral call.
- **Notifying the consignee.** A wrong notification cannot be recalled, and it reaches a
  customer.

Present the recommendation, the evidence, and the specific irreversible action, then wait.
"The human approved a similar action earlier" is not approval for this one.

## Verdict vocabulary

Use exactly the three the module returns, and do not soften them:

- **release** — inside limits for the entire record.
- **review** — left the range but stayed inside the granted allowance. This is a real verdict,
  not a hedge; it means a qualified person must look. Never round it up to release.
- **quarantine** — a freeze event, an MKT above the labelled maximum, or the excursion
  allowance exhausted.

## What a deviation report must contain

An auditor reading it a year from now must be able to re-derive the verdict without trusting
you. Include: consignment and device identifiers; the label source and its limits; the number
of readings and the period covered; every logger gap; the MKT with the activation energy
assumed; time above and below the range; the verdict with the module's own stated reasons; and
the route context that explains the excursion. Cite where each fact came from.

## Failure modes to avoid

- Averaging temperatures arithmetically. MKT exists precisely because the mean understates
  thermal stress on a shipment that swung.
- Netting cold minutes against warm ones. For most biologics a single freeze is disqualifying
  on its own.
- Filling a logger dropout with the last known reading and treating it as measured.
- Assuming an excursion allowance. The default is zero until the product's stability data says
  otherwise.
- Reporting a verdict without the inputs that produced it.
