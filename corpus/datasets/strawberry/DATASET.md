# strawberry — refrigerated strawberry truck shipments, 9 probes per trailer

| | |
|---|---|
| Study | Abdella, Brecht & Uysal, *"Systematic modeling of strawberry quality during postharvest handling"* — arXiv:2103.12895 / [10.1016/j.jfoodeng.2021.110477](https://doi.org/10.1016/j.jfoodeng.2021.110477) |
| Data actually fetched | Hugging Face dataset [`Professor29/Cold-Chain-Transportation-Strawberry`](https://huggingface.co/datasets/Professor29/Cold-Chain-Transportation-Strawberry), files `benchmark_v2/S{1..6}_aligned_strict_linear_with_labels.parquet`, pinned to commit `53ddd9410cf560e6e4647e7dff96655d48811559` |
| License | **apache-2.0**, as stated in the YAML front-matter of that repo's dataset card (`license: apache-2.0`). See "License — what is and is not verified" below: this is the *mirror's* declared license, and the upstream study's own terms could not be located. |
| Domain | **Food / fresh produce cold chain.** Not pharmaceutical. See "This is food, not pharma". |
| Records | 6 shipments (S1–S6), 9 fixed trailer probe positions each (Front/Middle/Rear × Top/Middle/Bottom), °C, on a strict 10-minute grid, March–July 2019 |
| Fetched size | 6 Parquet files, 747,863 bytes total (per-file sizes and sha256 pinned in `fetch.sh`) |

## Source discovery — what was looked for and what was found

The paper names the data owner, not a download: the shipments were run with **WishFarms**
(Plant City, FL), and the arXiv PDF carries a Mendeley Data *draft* link,
`https://data.mendeley.com/datasets/nxttkftnzk/draft?a=7d8b1fed-c1c3-4aa3-8cf3-5b385d221237`.
That is a private pre-publication URL with a reviewer token, not a public record. The published
form of that identifier, `https://data.mendeley.com/datasets/nxttkftnzk/1`, returns HTTP 200 but
the Mendeley public API returns `{"error":404}` for its file listing
(`https://data.mendeley.com/public-api/datasets/nxttkftnzk/files?folder_id=root&version=1`), so
**no downloadable primary file, and no license statement attached to one, could be obtained from
Mendeley on 2026-08-28.** The raw WishFarms logger exports are therefore not in this corpus.

Two Hugging Face mirrors carry the same six shipments:
`Professor29/Cold-Chain-Transportation-Strawberry` (card says apache-2.0) and
`NifferLi/cold-chain-strawberry-sensors` (card says cc-by-4.0). They agree on shape and on
values — the same six shipments, the same nine probe columns, the same 10-minute grid, differing
only in timestamp rendering (`2019-03-12 12:30:00` vs `2019/3/12 12:30`). Professor29's
`benchmark_v2` files were used because they are the plainest per-shipment tables of the two and
their commit is pinnable. Neither mirror states who produced it from the authors' data or under
what permission.

### This is a processed derivative, not raw logger output

State this plainly: **what this adapter reads has been through someone else's pipeline.** From
the mirror's own README and from inspecting the files:

- The grid is **strictly 10-minute** in every shipment, with no jitter at all. Real loggers do
  not sample on an exact grid; the paper describes ~5–10 min sampling. The filename says it:
  `aligned_strict_linear` — the series have been **aligned to a common grid and linearly
  interpolated** onto it. Some fraction of the values this corpus scores are therefore
  interpolated, and there is no flag in the file marking which.
- The same files carry **engineered columns** the mirror generated: 60-minute rolling-window
  ("W60") features, risk labels, and future prediction targets, including a `dur_gt4` duration-
  above-4 °C feature. **None of those are carried into the legs.** `fetch.sh` extracts exactly
  ten columns — `Time` plus the nine probe temperatures — and drops everything derived, so this
  benchmark scores telemetry, never someone else's labels.
- Missing samples survive as nulls and are preserved as empty cells, not zeros; the adapter drops
  them rather than filling them.

What is lost by not having the raw files: the true sampling instants, which readings are measured
versus interpolated, probe make/accuracy, and any logger-side quality flags.

## Fetch and the Parquet → CSV conversion (`fetch.sh`)

`adapt.py` must be stdlib-only, and the source is Parquet, so the conversion happens at fetch
time. `fetch.sh`:

1. Downloads the six files from immutable `resolve/<sha>/` URLs into `data/corpus/strawberry/raw/`
   and checks **both** byte size and sha256 against values pinned in the script; a mismatch is a
   hard failure. A file that already matches is not re-downloaded, and the CSVs are only rebuilt
   when missing — the script is idempotent.
2. Converts each Parquet to `data/corpus/strawberry/S<N>.csv` with header
   `ts,Front_Top,...,Rear_Bottom`, using pandas + pyarrow inside an **ephemeral** environment
   (`uv run --no-project --with pandas --with pyarrow`). Nothing is added to the project venv and
   nothing is installed globally, per the repo's environment rule. Values are written exactly as
   stored, to the one decimal the source uses; timestamps are written ISO-8601; nulls become
   empty cells. No resampling, no interpolation, no rounding is introduced by the conversion.

Everything above lands in `data/corpus/` and is gitignored.

## How legs are cut (`adapt.py`)

- **One leg per shipment × probe position** — 6 × 9 = 54 possible; 52 series actually report.
  `S1`'s `Front_Bottom` and `Middle_Bottom` columns are entirely null in the source and are
  omitted rather than zero-filled. Channels are never averaged: the whole point of a 9-probe trailer is that the
  rear-top pallet and the front-bottom pallet do not experience the same trip, and in this data
  they differ by tens of degrees.
- **Timezone**: the source timestamps are naive, with no offset and no timezone statement in the
  mirror, the file, or the paper. The adapter labels them **UTC without shifting**. The shipments
  were run in Florida, so the wall-clock is most likely US Eastern — meaning the *absolute*
  instants in these legs are probably offset by 4–5 h from reality. Nothing this benchmark
  computes (durations, MKT, budget) depends on the absolute offset, only on the intervals, which
  are unaffected. Where a leg id carries a date, read it as source wall-clock, not UTC.
- **Units**: source values are Celsius (the paper and the mirror both state °C, and the ranges
  — Florida field heat in the 30s, refrigerated transit near 0 — are only coherent in °C). No
  conversion is applied.
- **Ordering and duplicates**: each probe's points are sorted before writing, and of a duplicated
  instant the later-parsed reading wins — the same rule as `zenodo-ll1`, and it exists because
  the CLI rejects out-of-order input rather than guessing. In this source, which is already
  strictly gridded, neither case actually fires; the handling is there so a re-pull of a less
  clean mirror cannot silently produce garbage.
- **Journey cut at > 3 h of silence**, the same threshold `zenodo-ll1` uses. Two probe series
  contain a real multi-day silence and are split: `S1-Rear_Top` (12–22 Mar, then 28–29 Mar) and
  `S3-Front_Bottom` (9–16 Jul, then 17–20 Jul). A split leg's id gains its start date, e.g.
  `S1-Rear_Top-20190328-1430`; unsplit series keep the plain `<shipment>-<sensor>` id.
- **Legs shorter than 8 readings or 2 h are dropped** — too little evidence to score. None were
  dropped here.
- Nothing is invented, interpolated or smoothed by the adapter (the mirror already did its own
  interpolation, which is why that caveat matters above and not here).

Result: **54 legs** from those 52 probe series (two of them split in two), 68,697 readings, spanning
2019-03-12 → 2019-07-26. Note S3/S4 cover identical windows, as do S5/S6 — they read as two
trailers on the same lane rather than six independent trips.

## Policy and the storage band

`profile.json` sets **0–4 °C** and `config.json` allows **24 h** out of band, retest at 50%,
destroy at 100%, with the **freeze rule off**. Where those numbers come from, in short (the full
statements, verbatim, are in `profile.json`):

- **0 °C floor — published.** USDA Agriculture Handbook 66's strawberry summary says "Store at
  0 °C (32 °F) with 90 to 95% RH". The PDF was downloaded from
  `https://www.ars.usda.gov/is/np/CommercialStorage/CommercialStorage.pdf` and read directly.
- **4 °C ceiling — a ColdCall benchmark assumption, not a published limit.** No source says
  "0–4 °C" for strawberry; AH-66 gives an optimum, not a band. 4 °C was chosen from AH-66's own
  respiration and Rhizopus-growth statements and from the >4 °C threshold the mirror itself uses
  for its risk labels. It is a judgement call and is labelled as one.
- **24 h allowance — a benchmark assumption.** Every record here opens in the field at ambient
  and includes pallet build-up and forced-air precooling, so a short allowance would condemn all
  54 legs for doing exactly what harvest handling requires. 24 h is ~1/7 of AH-66's 7-day storage
  life at 0 °C. Reasoning in full in `config.json`'s `policy_note`.
- **Freeze rule off (`no_freeze_rule: true`).** AH-66: strawberries "are not sensitive to
  chilling and should be stored as cold as possible without freezing". With a 0 °C floor set at
  the *optimum*, ColdCall's default "any minute below the floor is disqualifying" would quarantine
  a leg for a −0.3 °C reading at tenth-of-a-degree logger resolution, which is noise. Sub-zero
  time still counts as out of band and still spends the 24 h allowance. Worth knowing: the data
  does contain at least one genuine freeze — `S2` reaches −6.5 °C — and that leg lands on
  `destroy` on time-out-of-band alone (`S2-Middle_Top`), so switching the rule off did not let a
  real freeze pass unnoticed.

**AH-66's strawberry summary does not state the fruit's freezing point, so no freezing-point
figure is asserted anywhere here.** UC Davis Postharvest's Produce Facts sheet was sought as a
second source and `postharvest.ucdavis.edu` returned HTTP 403 (Cloudflare) on 2026-08-28;
nothing from it is cited.

## This is food, not pharma

Nothing in this dataset or profile is pharmaceutical regulatory validation, and a verdict here
is not a regulatory determination about anything. ColdCall's engine speaks in `release` /
`quarantine_retest` / `destroy` and computes MKT by the USP <1079> method; applied to
strawberries those are an **analogy**, deliberately, to show the same arithmetic against a
second real domain. AH-66 is USDA *handling guidance* for produce — it is not a drug label, it
carries no permitted-excursion envelope, and no medicines regulator has reviewed any number in
`profile.json`. Read the verdicts as "how badly did this pallet's cold chain fail relative to a
stated band", not as a shipping decision anyone should make from this repo.

## Results, and why so many legs are destroyed

40 destroy / 12 quarantine_retest / 2 release (pinned in `expected.json`, cross-check agreeing on
all 54). That skew is a property of the data, not of a harsh policy: these records begin at
harvest in a Florida field — peaks of 36–46 °C appear in the first hours of most shipments — and
most loggers keep reporting after the trailer is opened at the DC. A leg is "everything one probe
recorded", so ambient field time and post-delivery time both count against the band. The 2
releases (`S4-Rear_Top`, `S5-Front_Middle`) are probes that were pulled down fast and held near
0 °C for a 130–160 h trip.

One behaviour worth flagging because it looks wrong and is not: a few legs sit well under the 50%
retest line yet come out `quarantine_retest` (e.g. `S2-Front_Top`, 18.06% consumed). That is
`src/coldcall/disposition.py`'s MKT rule — MKT above the band ceiling quarantines regardless of
elapsed time. With a 4 °C ceiling and a short record containing a hot start, MKT 10.9 °C is
genuinely above band, so the rule is doing its job.

## Limitations

- **The primary source is not in this corpus.** The raw WishFarms logger files are not publicly
  downloadable (evidence above); everything here is a third-party mirror of a processed form.
  The mirror's provenance — who processed it, with what permission — is not stated by the mirror.
- **The values are grid-aligned and linearly interpolated** by the mirror, and no flag
  distinguishes measured from interpolated readings. Durations out of band are consequently
  accurate to the mirror's grid, not to the loggers.
- **License is the mirror's claim only.** Professor29's card declares apache-2.0; the second
  mirror of the same underlying data declares cc-by-4.0. They cannot both be authoritative, and
  neither is the study's own terms, which could not be located. Anyone re-using this data beyond
  benchmarking should go to the authors.
- **Timestamps are assumed UTC** although they are almost certainly US Eastern wall-clock (above).
- **A leg is one probe's whole record**, which mixes field, precool, transit and post-delivery
  dwell — the source has no phase or event annotations to cut on, and the 3 h gap rule only
  catches logger silences, of which there are two.
- **The band's upper bound and the 24 h allowance are ColdCall's, not anyone's published policy.**
  Change either and the verdict spread moves; the pins in `expected.json` are pins against *this*
  configuration.
- 4 of the 6 shipments overlap pairwise in time and probe layout, so the 54 legs are less
  independent than the count suggests.
