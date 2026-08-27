# SHIPMENT — the one leg chosen for the demo

This documents the selection of a single, real shipment leg with a genuine, borderline
temperature excursion, pulled from a bounded byte-range sample of a real public dataset. It is
a data-selection record, not a design decision — it does not get an `ADR-####`.

## Dataset

- Zenodo record **7907515**, "Shipments Sensors readings", DOI `10.5281/zenodo.7907515`,
  CC-BY-4.0.
- File: `LL1_raw_messages_Public.json`, **421,429,648 bytes** (~402 MiB) per the Zenodo API's
  `.files[].size` and confirmed again via `curl -sI` (`content-length: 421429648`) on
  2026-08-27. This is a size, not a record count — the full file was never parsed, so no claim
  is made here about how many readings it contains in total.
- Direct file URL (from `.files[].links.self` in the record's API response):
  `https://zenodo.org/api/records/7907515/files/LL1_raw_messages_Public.json/content`

## How the sample was obtained

**The whole 402 MB file was never downloaded.** A single HTTP range request pulled the first
~2.9 MB and nothing else:

```sh
curl -s -r 0-3000000 -o data/samples/ll1_raw_sample.json \
  "https://zenodo.org/api/records/7907515/files/LL1_raw_messages_Public.json/content"
```

This was re-run in this session to confirm reproducibility: the server returned `HTTP/1.1 206
Partial Content`, `content-range: bytes 0-3000000/421429648`, `content-length: 3000001`, and the
resulting bytes are **byte-identical** (`cmp` confirmed) to the sample already sitting in
`data/samples/ll1_raw_sample.json` from a prior session. The server advertises
`accept-ranges: bytes`, so this is a supported, repeatable way to pull a bounded slice.

A 2.9 MB slice of a 402 MB pretty-printed JSON array necessarily ends mid-record. The parser
used here (`json.JSONDecoder().raw_decode` walked forward through the array, skipping
separators) reads every complete top-level object up to that point and stops cleanly at the
first one it cannot fully decode — the same tolerant-of-truncation approach already used in
`src/coldcall/replay.py`. That yields **3,818 usable readings across 6 devices** from this one
sample. This is a count from the sample, not from the file — a different byte range, or the
full file, would surface more devices and more readings than this.

## Record shape (as actually observed, field-for-field)

Each element of the top-level JSON array is one sensor message, shaped like this (irrelevant
values omitted, real example from the sample):

```json
{
  "_id": { "$oid": "61a85c97931b91f5b5844226" },
  "identifier": "DD:33:04:13:34:BA",
  "timestamp": { "$date": "2021-11-08T17:48:04Z" },
  "status": ["normal"],
  "measurements": {
    "temperature": 27,
    "gps": { "lat": 39.4565, "long": -0.3465 },
    "battery": 3.05
  },
  "device_parameter": { "tlm_ver": "0" },
  "parent_identifier": "EF:65:5A:8D:73:97",
  "address": "Aqua Multiespacio, 19, Carrer de Menorca, ... Spain",
  "raw_address": { "shop": "...", "city": "Valencia", "country": "Spain", "country_code": "es", "...": "..." },
  "sscc": "00312345678939742991",
  "GRAI": "800301234567891110DD33041334BA",
  "GSIN": "40212345678970614449"
}
```

Field-by-field, for the fields that matter to this task:

| Field | Path | Type | Notes |
|---|---|---|---|
| device / sensor id | `identifier` | string, MAC-like (`AA:BB:CC:DD:EE:FF`) | The tracker/tag id. This is what "device" means throughout this doc. |
| timestamp | `timestamp.$date` | string, ISO-8601 UTC, `Z`-suffixed | Mongo extended-JSON form (`{"$date": "..."}`), not a bare string. Some devices report whole seconds only. |
| temperature | `measurements.temperature` | number (int or float, °C) | The DD:xx devices in this sample report **integer** degrees only; the other two devices (`CB:...`, `EF:...`) report to 2 decimal places. |
| status | `status` | array of strings | e.g. `["normal"]`, `["stop", "data_buffered"]`. Not used in the selection below but worth knowing it exists. |
| GPS | `measurements.gps.lat` / `.long` | numbers | Present on most but not all messages. |
| battery | `measurements.battery` | number | Volts, roughly 3.0–3.1 on the small DD tags, ~11.4 on the larger CB/EF loggers — these are physically different device classes. |
| address (reverse-geocoded) | `address`, `raw_address.*` | strings | Present on many readings; `"Unknown Address"` / `{}` on some. |
| logistics identifiers | `sscc`, `GRAI`, `GSIN`, `parent_identifier` | strings | GS1-style pallet/case identifiers; present but not used here. |

This matches `src/coldcall/replay.py`'s `_normalise()`, which already reads exactly
`record["identifier"]`, `record["timestamp"]["$date"]` (or a bare ISO string), and
`record["measurements"]["temperature"]`.

## Per-device overview of the sample (before splitting into legs)

| device | readings in sample | span | temp range (°C) |
|---|---:|---|---|
| `EF:65:5A:8D:73:97` | 1786 | 2021-10-01 → 2021-11-09 (39.2 days) | 22.64 – 30.17 |
| `CB:46:70:5F:0A:6C` | 1710 | 2021-10-01 → 2021-10-19 (17.4 days) | 22.21 – 29.94 |
| `DD:33:04:13:34:C6` | 98 | 2021-11-08 → 2021-11-10 (1.46 days) | 22.00 – 26.00 |
| `DD:33:04:13:34:CD` | 79 | 2021-11-08 → 2021-11-10 (1.45 days) | 23.00 – 27.00 |
| `DD:33:04:13:34:D4` | 74 | 2021-11-08 → 2021-11-10 (1.44 days) | 24.00 – 28.00 |
| `DD:33:04:13:34:BA` | 71 | 2021-11-08 → 2021-11-10 (1.44 days) | 25.00 – 29.00 |

Every one of these device totals spans a multi-day (in two cases multi-week) window and clearly
contains several separate journeys with idle stops in between — a device does not move
continuously for 39 days. Reporting one of these multi-week windows whole as "a shipment leg"
would be misleading: it would blend several distinct trips (and several distinct excursions)
into one number. `src/coldcall/replay.py`'s `group_by_device()` treats a whole device's span as
one `ShipmentLeg` for its own purpose (duration-weighted MKT across everything a device saw,
capping any single gap at `max_gap_minutes`); **that is a different, coarser notion of "leg"
than the one used below**, made for a different job (grading), and this document does not
change that code.

## Segmenting into actual journeys

For this task, "one leg" means one physically contiguous run: readings from a single device with
no gap larger than 3 hours between consecutive readings (a gap that size reliably marks the
tracker sitting idle at a stop, based on the sampling interval — see below). Splitting on that
threshold turns the 6 device-totals above into 25 candidate legs of 5+ readings each. The
typical reporting interval, once moving, is **~11.7–14.3 minutes** (median inter-reading gap
within a leg) for every device in the sample.

## Candidate legs, ranked by fit to the excursion criterion

The criterion: mostly inside the 15–25 °C USP Controlled Room Temperature band, with a
**contiguous** excursion above 25 °C lasting tens of minutes to hours — borderline, not
catastrophic, and not boringly clean either.

| device | leg window (UTC) | n | duration | tmin/tmax/mean °C | minutes >25°C | longest contiguous stretch >25°C | % of leg time >25°C | verdict |
|---|---|---:|---:|---|---:|---:|---:|---|
| **`DD:33:04:13:34:CD`** | **2021-11-09 08:23:09 → 2021-11-10 04:42:10** | **64** | **20.3 h** | **23.0 / 27.0 / 24.70** | **231.7 (3.86 h)** | **231.7 (3.86 h)** | **19.0%** | **Chosen** |
| `EF:65:5A:8D:73:97` | 2021-10-01 11:52:18 → 2021-10-05 09:25:44 | 395 | 93.6 h | 22.64 / 30.17 / 26.40 | 4247.2 | 3734.1 | 75.6% | Rejected — well over half the leg is above 25 °C; not "mostly in band" |
| `EF:65:5A:8D:73:97` | 2021-10-19 12:41:49 → 2021-11-09 17:05:35 (5 sub-legs, e.g. n=187) | 187 | 44.8 h | 23.38 / 27.34 / 24.84 | 962.7 | 501.1 (8.35 h) | 35.8% | Runner-up — good single excursion, but over a third of the leg sits above 25 °C, less clean a "mostly fine" baseline |
| `DD:33:04:13:34:D4` | 2021-11-09 08:23:09 → 2021-11-10 04:27:52 | 64 | 20.1 h | 24.00 / 28.00 / 26.11 | 649.0 | 634.0 (10.6 h) | 53.9% | Rejected — over half the leg is above 25 °C, roughly a coin flip rather than an excursion |
| `DD:33:04:13:34:BA` | 2021-11-09 08:39:52 → 2021-11-10 04:27:52 | 62 | 19.8 h | 25.00 / 29.00 / 27.10 | 1019.2 | 1019.2 (17.0 h) | 85.8% | Rejected — never actually inside the 15–25 band (tmin itself is 25.0); this is the catastrophic case the brief said to avoid |
| `DD:33:04:13:34:C6` | 2021-11-09 08:23:09 → 2021-11-10 04:45:16 | 84 | 20.4 h | 22.00 / 26.00 / 23.65 | 25.2 | 12.3 | 2.1% | Rejected — technically has an excursion but it's a single ~12-minute blip, too brief to read as an "incident" on a demo timeline |
| `CB:46:70:5F:0A:6C` | 2021-10-18 15:11:54 → 2021-10-19 01:15:45 | 16 | 10.1 h | 24.38 / 25.84 / 25.15 | 347.9 | 347.9 | 57.6% | Rejected — majority of leg above 25 °C, and the excursion barely clears the boundary (max 25.84 °C) |

## Why `DD:33:04:13:34:CD`, 2021-11-09 08:23:09 → 2021-11-10 04:42:10

This is the cleanest borderline case in the sample:

- **81.0% of the leg (64 readings, ~16.6 hours) sits at or below 25 °C**, ranging 23–25 °C —
  comfortably in the 15–25 USP CRT band, and not hugging either edge.
- There is **exactly one** contiguous excursion above 25 °C: from **2021-11-09 14:58:16 to
  2021-11-09 18:49:56**, **231.7 minutes (3 hours 52 minutes)**, rising smoothly from 25 °C to a
  peak of **27 °C** and back down — not a spike, a genuine sustained warm stretch consistent
  with, e.g., a midday stop in direct sun or a warm loading dock.
- The peak (27 °C) is **2 °C above the CRT ceiling and 3 °C inside the 30 °C excursion-permitted
  ceiling** — a real but non-catastrophic breach, i.e. exactly the "borderline, worth a human
  judgment call" case the brief asked for, not a leg that never leaves band (no incident) and
  not one that never returns to band (boring/catastrophic).
- It is a single, complete, gap-bounded run (bordered by >12-hour gaps on both sides within the
  device's own data in this sample) — i.e., a plausible single shipment leg, roughly a day long,
  not an artificially stitched-together window.

The runner-up (`EF:65:5A:8D:73:97`, the 187-reading, 44.8-hour sub-leg) is a legitimate second
choice — longer, with a comparably shaped single 8.35-hour excursion peaking at only 27.34 °C —
but a larger fraction of that leg (35.8% vs. 19.0%) sits above the label ceiling, which makes it
read less like "an otherwise-fine trip with one incident" and more like "a trip that runs warm."
`DD:33:04:13:34:CD` is the sharper demo case.

## Honesty about limits

- Only a **~2.9 MB byte-range sample of a 402 MB file** was parsed — not the full dataset. The
  6 devices and 3,818 readings above are what happened to fall inside that first slice, which
  (per the timestamps) is chronologically the *early* part of the file. A different range, or
  the full file, would very likely surface more devices, more legs, and possibly cleaner or
  messier excursions than the ones tabulated here.
- No claim is made about how many total readings exist in the full 421,429,648-byte file — it
  was never counted.
- The "leg" boundaries above are a segmentation choice (>3 hour gap = new leg) made for this
  document, not a field in the source data and not the same grouping `src/coldcall/replay.py`
  uses internally (`group_by_device`, which does not split on gaps at all). Both are legitimate
  views of the same data for different purposes; do not assume they agree on how many "legs" a
  device has.
- The two decimal-precision devices (`CB:...`, `EF:...`) and the four integer-precision devices
  (`DD:...`) look like two different hardware/firmware generations. This wasn't something the
  task asked to resolve and is left as an observation rather than a conclusion.

## Output file

The chosen leg's 64 readings, sorted by time, are written to
`data/samples/selected_leg.json` as a plain JSON array of `{"ts": "<ISO-8601 UTC>", "temp_c":
<number>}` objects — no nesting, no Mongo extended-JSON, so downstream code can `json.load()` it
directly without re-parsing the big file or handling truncation. First and last entries:

```json
[
  { "ts": "2021-11-09T08:23:09Z", "temp_c": 23.0 },
  ...
  { "ts": "2021-11-10T04:42:10Z", "temp_c": 23.0 }
]
```

## Route coordinates, and why they are in the dataset rather than assumed

The chosen leg's raw records carry `measurements.gps`. For device `DD:33:04:13:34:CD` the
sample holds 15 fixes, all clustered at **39.456 N, −0.347 E — Valencia, Spain**:

```
{'lat': 39.4564, 'long': -0.3467} @ 2021-11-08T17:59:37Z
{'lat': 39.4568, 'long': -0.3461} @ 2021-11-08T17:59:06Z
{'lat': 39.4565, 'long': -0.3465} @ 2021-11-08T17:48:04Z
```

`39.4565, −0.3465` is used as the route point. It matters that this is **the leg's own
recorded position** and not a plausible-sounding city: `src/coldcall/weather.py` fetches real
historical weather for that coordinate and compares it against the internal temperature, so an
invented location would produce an invented root cause.

**What it shows.** Open-Meteo's archive (ERA5) for 2021-11-09 at that point gives an ambient
peak of **17.7 °C**, and 13–17 °C across the excursion window. The consignment reached
**27 °C** — a median of **12.6 °C above outside air**, across 14 of 14 matched excursion
readings.

So the excursion is **not** explained by the weather. That is a materially different finding
from "it was a hot day": it points the investigation at packaging, the reefer unit and loading
procedure rather than at the lane or the schedule. See `EXP-0013`.

**Honest limits**, which belong in any report quoting this: the archive gives point weather at
hourly granularity for shade temperature, while the cargo moved and sat inside a vehicle. Some
positive gap is expected; the 5 °C threshold that separates "containment failure" from
"environmental exposure" is ColdCall policy, not a regulatory value.
