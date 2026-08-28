# zenodo-ll1 — pharma logistics logger telemetry (the demo's own source, widened)

| | |
|---|---|
| Source | Zenodo record 7907515, file `LL1_raw_messages_Public.json` |
| DOI | [10.5281/zenodo.7907515](https://doi.org/10.5281/zenodo.7907515) |
| License | CC-BY-4.0 (per the Zenodo record) |
| Domain | Pharmaceutical logistics (real BLE logger messages from live shipments) |
| Full size | 421,429,648 bytes; this corpus samples the first 20 MB by HTTP range request |
| Record shape | Mongo extended-JSON messages: `identifier` (device MAC), `timestamp.$date`, `measurements.temperature` (°C), optional `measurements.gps`, `battery`, `status[]` |

This is the dataset `DEMO-0001` replays — but the demo uses **one** hand-picked leg
(`VCC-118`, device `DD:33:04:13:34:CD`, see `replay/SHIPMENT.md`). Here the same source is
widened: every device in the sample, every contiguous journey, no hand-picking. The 20 MB
sample carries ~26k usable readings across 7 devices spanning Oct–Dec 2021.

## How legs are cut (`adapt.py`)

- Parsed with the same streaming parser the demo uses (`coldcall.replay.iter_telemetry`) — a
  truncated final object from the range request ends iteration quietly, by design.
- Per device, time-ordered points are split into legs wherever the record goes silent for
  **> 3 h** (the journey-cut threshold `replay/SHIPMENT.md` established): a multi-week device
  history is several journeys, and scoring it as one would let quiet weeks dilute an excursion.
- Duplicate instants keep the later-parsed reading (same rule as `coldcall.replay.to_readings`,
  where of a duplicated pair the reading owning the next interval survives).
- Legs with < 8 readings or < 2 h duration are dropped: near-zero duration evidence.

## Policy

The product context is the demo's real openFDA Amoxicillin label (`data/product_profile.json`):
20–25 °C storage, 15–30 °C permitted excursion envelope, and the **6 h allowance that is
ColdCall demo policy, not label text**. These are the same devices and the same distribution
context as the demo leg, so the same profile is the honest choice.

## Limitations

- A 20 MB range sample, not the full 402 MB file — breadth within the sample window only.
  Legs that run to the sample's last byte are truncated windows of longer journeys; they are
  still real evidence for the time they cover, but their verdicts speak for the window.
- Device gaps are the only journey signal; the data has no shipment IDs, so a leg is "what one
  logger recorded between silences", which may merge dwell and transport.
- **A finding this corpus surfaced about the demo itself**: the demo's 64-reading `VCC-118`
  leg (device `…34:CD` from 2021-11-09 08:23) was bounded not by a real logger silence but by
  the end of the demo's 2.9 MB sample. In this wider sample the same journey continues
  uninterrupted to 2021-11-14 22:34 (617 readings, leg `1334CD-20211109-0823`) and the full
  journey scores `destroy` — more warm time, more budget spent. The demo's
  `quarantine_retest` is the correct verdict *for the 20.3 h window it replays* and stays
  pinned as such in `tests/`; the corpus scores the whole journey.
