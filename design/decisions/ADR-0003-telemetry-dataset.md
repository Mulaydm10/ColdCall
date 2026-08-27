# ADR-0003: Which real telemetry dataset we replay

Status: Accepted
Owner: Mulaydm10
Date: 2026-08-27

## Context

The plan named a "VCC-CPLD dataset (Zenodo, 445K real cold-chain records)" as the shipment
telemetry to replay. The judging rubric rewards real data over mocks, so this is load-bearing:
if the dataset is not real, the demo's central claim is not either.

**It could not be found, and we should assume it does not exist under that name.** A search of
Zenodo's API for the exact string `VCC-CPLD` returns zero records. Broader searches surface
only unrelated material (market reports, and electronics documentation where CPLD means
Complex Programmable Logic Device). No dataset matching the ~445 000-record cold-chain
description surfaced. It may be an internal name from a paper that was never deposited, or the
identifier may simply be wrong.

Citing a DOI we cannot resolve would be worse than having no dataset at all.

## Options considered

- **Keep hunting for VCC-CPLD off-Zenodo** — possible, but unbounded search under a deadline,
  with no evidence it exists anywhere.
- **Generate synthetic cold-chain telemetry** — trivially easy, and it forfeits the "real data,
  no mocks" credit entirely. A judge who asks "where is this from?" gets a bad answer.
- **Replay a different, verified public dataset** — costs the specific "cold chain" framing but
  keeps the data real and the DOI resolvable.

## Decision

**Replay Zenodo record 7907515, "Shipments Sensors readings"** (DOI `10.5281/zenodo.7907515`,
CC-BY-4.0, `LL1_raw_messages_Public.json`, ~402 MB). It is real per-reading logistics telemetry
from an EU logistics project: temperature, GPS, battery and status per message, per device,
across multi-week journeys. Verified reachable; a 2.9 MB range sample parses into 3 818 usable
readings across 6 devices, the largest leg covering 1 786 readings over 39 days.

A structured EPCIS sibling exists at `10.5281/zenodo.7907512` if we need event semantics.

**We do not claim 445 000 records.** We have not parsed the whole file, so the honest statement
is "~402 MB of real per-reading telemetry" until someone counts.

## The catch, and how we handle it

This data is **ambient logistics, not refrigerated cold chain.** Readings sit around 22–30 °C.
Judged against a 2–8 °C biologic label every leg quarantines immediately, which is a boring
demo and a misleading one.

Judged against a **real USP controlled-room-temperature label (15–25 °C)** — which is what this
cargo actually is, and which openFDA supplies for real products — the same data produces a
genuine spread: legs that release, legs that need review, legs that quarantine. That is both
more honest and a better demo, because the interesting verdict is the borderline one.

So: the label comes from openFDA for a real product whose storage range matches the goods, and
we describe the shipment as what it is. If a genuinely refrigerated public dataset turns up
later, only the label range changes — the pipeline is indifferent.

## Consequences

- `scripts/verify_apis.sh` checks the Zenodo URL resolves, so a dead link is caught before a demo.
- The replay engine streams rather than loading: 402 MB will not fit comfortably in a sandbox.
- `data/samples/` is gitignored. The sample is re-fetchable with one range request.
- Any claim about record counts must be measured before it is written down.

## Related

`ADR-0002`, `Q-0004`, `Q-0007`
