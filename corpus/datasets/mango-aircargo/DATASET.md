# mango-aircargo — a real air-freight mango shipment, Thailand → France

**This is food / fresh-produce logistics, not pharma.** Nothing here is regulatory validation,
nothing here is a drug label, and no verdict below says anything about medicines. It is the
same deterministic arithmetic run against a domain whose storage band comes from horticultural
handling guidance — see `corpus/README.md` on what the corpus does and does not claim.

| | |
|---|---|
| Source | Recherche Data Gouv (Dataverse, INRAE), *Dataset of Air Cargo Supply Chain and Fruit quality: case study of mango shipment from Thailand to France* |
| DOI | [10.57745/F9UJGQ](https://doi.org/10.57745/F9UJGQ) |
| License | **CC-BY-NC-SA 4.0** — the value of `termsOfUse` on the published record (`api/datasets/:persistentId?persistentId=doi:10.57745/F9UJGQ`) and the licence shown on the dataset landing page, both checked 2026-08-28. Note the **NC**: attribution + non-commercial + share-alike. |
| Published | 2025-02-06 (v1.0); data collected 2023-04-18 → 2023-05-03 |
| Cited by | Chaomuang N. *et al.* (2024), *Experimental investigation of temperature distribution in air cargo supply chain of mango from Thailand to France and its impact on product quality*, Int. J. Refrigeration 160, [10.1016/j.ijrefrig.2024.02.009](https://doi.org/10.1016/j.ijrefrig.2024.02.009) |
| Domain | Fresh produce in air cargo — one unit load device (ULD), 148 cartons, 14 mangoes (*Mangifera indica* L. cv. 'Nam Dok Mai Si-Thong') per carton |
| Files used | the 31 `00_All_Recording_Packing_House_to_Arrival_At_INRAE_<i>_<j>_<k>_Temp[_Hum].txt` recordings (directory `01_src_subset_dataset_T_H`), 18,696 or 22,038 bytes each |
| Not used | the per-step recordings (`0_Packing_House_*` … `9_10_Transport_And_Arrival_*`), quality assays (mass, colour, pH, TSS), photographs, and the R plotting scripts |

## Record shape (inspected, not assumed)

Tab-separated text, CRLF line endings, one header line:

```
Time	T_mangoes	T_Air              (22 files)
Time	T_mangoes	T_Air	RH_Air     (9 files)
18/04/2023 15:02	31.6	32.1
```

- **Timestamps** are `DD/MM/YYYY HH:MM` — day-first, as a French/Thai export would be. Every
  file is an unbroken 5-minute grid: 667 readings, `18/04/2023 15:02` → `20/04/2023 22:32`
  (55.5 h), identical across all 31 cartons. No gaps, no duplicate instants, no missing cells,
  no out-of-order rows — verified over all 31 files before writing the adapter.
- **Decimals use a point**, not the comma a French locale export might have used. Checked on
  every value in every file; the adapter would raise rather than mis-parse if that changed.
- **Units**: °C. The dataset is French/Thai academic work and the values (31 °C in a Thai
  packing house in April, ~19 °C on arrival) are only coherent as Celsius; there is no
  Fahrenheit anywhere and no unit column. No conversion is applied.
- **`RH_Air`** is relative humidity in %; it is not temperature and is dropped.

### Timezone — an inference, stated as one

The files carry **no timezone**. The per-step files show the record is one continuous clock
across the whole journey (the `7_Inflight` segment runs 20/04 00:07 → 12:02 with no jump, and
each step starts exactly 5 min after the previous ends), so a single offset is in force
throughout. This adapter reads the clock as **UTC+7 (Indochina Time)** — the packing house's
local time, where the loggers were started. Under that reading the Bangkok→Paris flight runs
17:07 → 05:02 UTC, i.e. a ~00:00 departure from BKK and a ~07:00 local arrival at CDG, which is
what scheduled nonstops on that route look like. It remains an inference. **It moves no
verdict**: every rule on this path is duration-based, and a constant offset cancels out of
durations, MKT and excursion minutes alike.

### The 86.2 h in the dataset description

The record's own description states a total shipment time of 86.2 h. The recordings used here
cover **55.5 h**, and the ten per-step files tile that same 55.5 h exactly with no missing
segment. We could not verify what the extra ~31 h in the description covers (harvest-to-packing
before the loggers started, or post-arrival handling at INRAE, or a different clock convention)
and do not guess: the legs below are the 55.5 h that were actually recorded.

## How legs are cut (`adapt.py`)

- **One leg per sensor channel per carton — 62 legs from 31 files.** `T_mangoes` (fruit) and
  `T_Air` (air inside the carton) are two physical sensors, and they disagree materially (up to
  11.0 °C at the same instant in the same box). Averaging them would fabricate a reading neither
  took, so each is its own leg: `box-<i>-<j>-<k>-mangoes` and `box-<i>-<j>-<k>-air`.
- **`<i>-<j>-<k>` is the carton's position in the ULD**, `k` being the vertical layer — the
  scheme drawn in the record's own `Instrumentation_position_ULD.PNG` (layers 1, 7 and 12 are
  the instrumented ones for most stacks). The record describes 25 instrumented cartons; 31
  `00_All_*` recordings are published, including positions outside the 1/7/12 layer pattern
  (`2_2_3`, `2_2_6`, `2_2_10`, `3_2_3`, `3_2_10`). All 31 are used; the discrepancy between "25
  instrumented cartons" and 31 published recordings is not explained by the record and we do
  not guess at it.
- **Full packing-house → arrival span**, cut on silences longer than **3 h** (the same
  threshold the `zenodo-ll1` adapter uses). No file contains a gap at all, so no cut fires
  here; the rule is implemented and unit-tested regardless, so that the leg definition is a
  property of the adapter rather than of this particular download.
- **Duplicate instants keep the later-parsed reading** (matching `coldcall.replay.to_readings`,
  so the survivor owns the interval to the next point). None occur in the published files.
- Legs with **< 8 readings or < 2 h span** are dropped. None are.
- Nothing is smoothed, resampled or interpolated; every emitted reading is a published one.

## Storage band and policy

Band: **10–13 °C**, from USDA Agriculture Handbook 66 (*The Commercial Storage of Fruits,
Vegetables, and Florist and Nursery Stocks*), Mango chapter, "Optimum Storage Conditions" —
quoted verbatim with its retrieval URL and date in `profile.json`. That is handling guidance
for mature-green mango in general; it is not a specification for this shipment and not a
regulatory limit.

- **No excursion envelope is configured.** No published source states an "excursions permitted
  to X–Y °C" band for mango (see `excursion_band_finding` in `profile.json`), and inventing one
  would change which disposition rule fires. `coldcall.disposition` then falls back to the
  storage band, which is its documented conservative behaviour.
- **The freeze rule stays on, re-read as chilling injury.** Handbook 66: "Most cultivars show
  injury below 10 °C." Sub-band temperature really is a product-integrity question for mango,
  not a budget item — the same shape the rule already has. It never fires on this dataset: the
  coldest reading anywhere is 13.1 °C.
- **`allowed_excursion_hours: 12` is a ColdCall benchmark assumption, not a published figure.**
  It is sized to the shipment's own structure: the non-flight ground segments (packing house,
  cold storage, road to BKK, airport platform, box arrangement, tarmac, loading, CDG storage,
  road to INRAE) total ~43 h, of which only the ~20 h cold-storage step is actively cooled. A
  12 h out-of-band allowance is therefore generous rather than strict for this domain. Any
  number here is policy; the arithmetic it feeds is not.

## What the verdicts say (and what they do not)

All 62 legs score `destroy`. That is not a degenerate benchmark result, it is what the record
contains: **the consignment never entered the 10–13 °C band at any point**. The coldest reading
across all 62 channels is 13.1 °C and the bulk sit between 17 and 32 °C, so all 3,335 recorded
minutes are out of band on every leg — 463.2% of the 12 h allowance. Air-freighted mango from
Thailand is not moved as a chilled cold chain in the way the handbook's storage recommendation
assumes, and the cited paper's own subject is exactly this: how much the temperature *varies by
position* and what it does to fruit quality.

What this dataset therefore pins is not verdict spread but the per-position arithmetic: MKT
ranges 21.49–25.28 °C and peaks 31.5–32.6 °C between the coolest and warmest instrumented
channels (`corpus/RESULTS.md`). A change that silently moved any of it fails the corpus.

## Limitations

- **One shipment.** 62 legs, but one ULD on one flight on one date — breadth of *sensor
  positions*, not of shipments. Nothing here supports a claim about air-freight mango in
  general.
- **The band is horticultural guidance, not a spec.** Handbook 66's 10–13 °C is for
  mature-green fruit generally; 'Nam Dok Mai Si-Thong' is not one of the cultivars it names,
  and the exporter's own commercial protocol for this shipment is not published. A `destroy`
  here means "far outside published storage guidance for the commodity, for the whole record",
  not "the fruit was unsaleable" — the record's own quality assays (D3–D15 after arrival) are
  the place to look for what actually happened to the mangoes, and this corpus does not use
  them.
- **The 12 h allowance and the 50/100% policy lines are ours.** No published mango source
  states a permitted duration out of band.
- **Timezone is inferred** (UTC+7, argued above), and the description's 86.2 h total is not
  reproduced by the recordings (55.5 h) — neither is guessed at, and neither affects a verdict.
- **Fruit and air channels are not independent legs in the physical sense.** They are two
  sensors in the same carton on the same journey, so 62 legs are not 62 independent
  observations; they are 31 cartons observed two ways.
- **Licence is NC.** Raw files and generated legs live under the gitignored `data/corpus/`, are
  never committed here, and are re-fetched from the DOI by `fetch.sh`.
