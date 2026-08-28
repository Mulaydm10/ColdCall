# covid-ult — ultra-low-temperature COVID-19 vaccine container tests (ORNL / Carrier)

| | |
|---|---|
| Source | figshare article 14888121, files `Test1_TempCO2O2.csv` and `Test2_TempCO2O2.csv` |
| Data DOI | [10.6084/m9.figshare.14888121](https://doi.org/10.6084/m9.figshare.14888121) |
| Paper | Sun, J. *et al.* "Dataset of ultralow temperature refrigeration for COVID 19 vaccine distribution solution", *Sci Data* **9**, 67 (2022), [10.1038/s41597-022-01167-y](https://doi.org/10.1038/s41597-022-01167-y) |
| License | **CC BY 4.0**, verified on the figshare record itself: the figshare API for article 14888121 returns `"license": {"value": 1, "name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"}` (checked 2026-08-28). The Sci Data article is separately CC BY 4.0. |
| Domain | **Pharmaceutical** — ultra-low-temperature (ULT) distribution of COVID-19 vaccine, dry-ice-loaded packages inside a refrigerated shipping container |
| Producer | Oak Ridge National Laboratory with Carrier Global Corporation, funded by the US DOE Building Technologies Office |
| Files fetched | `Test1_TempCO2O2.csv` (64,056,341 B, md5 `b8164462feaca1d699a53a2503f92d30`), `Test2_TempCO2O2.csv` (7,457,046 B, md5 `a306c744bc037558819b188a9149c853`) — both pinned by figshare file ID in `fetch.sh` |

## Measured, not simulated — and what that means here

**This corpus only takes real recordings, so this was checked before anything else was
written.** The record's two temperature CSVs are instrument output from two physical
laboratory tests: thermocouples (paper Table 3 gives the instrument specifications and their
±1.1 °C accuracy) logged by a Campbell Scientific CR3000 datalogger in Test 2, and by the
Test 1 platform's own acquisition system.

The paper *does* also describe an ANSYS/FLUENT CFD model, under "Technical Validation ->
Simulation models". That model is **not part of the data record**: it lives in a separate
publication (Zhang *et al.*, *Int. Comm. Heat and Mass Transfer* **130**, 105749) and no
simulated series appears in either CSV — each column is a named physical channel (a
thermocouple, an O₂ or CO₂ sensor). Nothing simulated is adapted here.

Two honesty notes about what the measurements are:

- These are **stationary laboratory tests, not shipments**. The container never moved; the
  tests measure how long dry ice holds a package in the ULT band, and both were deliberately
  run past depletion. A "leg" here is therefore a recorded thermal history of one package
  under test, not a journey.
- **No vaccine was in the boxes.** Test 2 put an empty payload box inside each package with a
  thermocouple at its centre "to represent the vaccine temperature" (paper, Test 2); Test 1
  put a thermocouple among the dry ice inside each box, at a position the paper states was
  *not* the same for every box — which is why Test 1's boxes have visibly different profiles.

## Record shape

Both files are CSV with multi-row headers and no timezone anywhere.

**Test 1** (test platform A, 21 Styrofoam boxes each with ~50 lb dry ice, container setpoint
−34.5 °C): three header rows — logger channel name (`Pod20`, `TC12`, …), physical label
(`b20`, `Ta1`, `Toutside`, …), unit (`F`) — then `date,time,Time Elapsed,…` rows.
112,267 rows, 16-Dec-2020 11:25:54 to 29-Dec-2020 12:05:07 local (312.7 h) at a nominal 10 s
cadence (observed 9–11 s, one 11-minute gap on 22-Dec). Package channels present: `b1`..`b20`.
The ambient comparison box `b0` described in the paper has **no column in the file**; the
`Toutside` channel is the room, not a box.

**Test 2** (test platform B at Oak Ridge, 20 packages each containing an empty payload box,
container setpoint −30 °C): two header rows — channel name, unit (`Deg F`) — then
`TIMESTAMP,…`. 13,944 rows, 3/9/2021 06:37 to 3/19/2021 00:00 local (232.4 h) at exactly
1 minute. Payload-box channels: `TC_TB1`..`TC_TB22`. Container-air distribution channels
(`TC_A*`..`TC_E*`), `O2` and `CO2` are also present.

The record's third file, `Test1_DryIceWeight.csv`, is sublimation scale readings in pounds at
3-hour intervals — not temperature — and is not fetched or adapted.

## How legs are cut (`adapt.py`)

**One leg per package thermocouple, per test, for the whole record.** Channels are never
aggregated or averaged: 39 legs, each one sensor.

1. **Channel selection is structural.** Test 1 takes columns whose *label* row matches `b<N>`;
   Test 2 takes columns named `TC_TB<N>`. Container air, supply/return air, ambient, O₂ and
   CO₂ are not product temperature and are dropped.
2. **One physical filter**: a channel whose median reading is above 0 °C was not inside a
   dry-ice-loaded package, whatever the header says. It drops exactly three Test 2 channels,
   and the adapter prints each one it drops:
   - `TC_TB21`, `TC_TB22` — median +19.3 / +19.6 °C, flat at laboratory room temperature for
     the whole record. The paper says two boxes were placed in the laboratory for comparison;
     whatever these two channels were attached to, they never record a cold package.
   - `TC_TB2` — median +19.7 °C, swinging between −86 °C and +64 °C with 622 minute-to-minute
     jumps larger than 11 °C. A detached or faulted thermocouple, not a thermal history.
   No Test 1 channel is dropped by this rule.
3. **Units**: both files declare °F in their unit header and the adapter *asserts* that
   declaration before converting; every value becomes °C by `(F − 32) × 5/9`, rounded to 4 dp
   (three orders of magnitude below the instruments' stated ±1.1 °C, so nothing measured is
   lost). No smoothing, no interpolation, no resampling, no outlier removal inside a kept
   channel.
4. **Timestamps → UTC**: the files carry naive local wall clock. Both sites are US Eastern
   (Carrier, East Syracuse NY; ORNL, Oak Ridge TN) and Test 2's record contains a one-hour
   forward jump at exactly 2021-03-14 02:00 — US spring-forward — so the loggers were keeping
   local time *with* DST. Timestamps are therefore interpreted in `America/New_York` and
   emitted as UTC. **This is an assumption**: no field in either file states a zone. It is a
   flat −5 h shift for Test 1 (December, no transition) and for Test 2 up to 14-Mar, −4 h
   after. The single Test 2 row stamped `02:00` on the transition date is a local time that
   does not exist; `zoneinfo`'s default (EST) is used, which lands it one minute before the
   `03:01` EDT row, consistent with the surrounding cadence.
5. **Duplicate instants** keep the later-parsed reading (the CLI rejects rather than guesses).
   None occur in this data; the rule is applied so a re-published file cannot slip one past.
6. **Gap cut at > 3 h** of record silence, the same threshold `zenodo-ll1` uses. It never
   fires here (largest real gap: 11 minutes in Test 1), so each sensor yields exactly one leg.
7. Legs with < 8 readings or < 2 h span are dropped. None are.

Leg ids are `test1-b<N>` and `test2-B<N>` — `<recording>-<sensor>`.

## Storage-band policy

`profile.json` uses **−90 to −60 °C**, the ULT storage condition in the FDA-approved
prescribing information for COMIRNATY (COVID-19 Vaccine, mRNA), Section 16, quoted verbatim in
the profile: *"single-dose vials may be stored in an ultra-low temperature freezer at −90 ºC
to −60 ºC (−130 ºF to −76 ºF)"* (document LAB-1490-16.2, revised 8/2026, retrieved from
<https://www.fda.gov/media/151707/download> on 2026-08-28, PDF md5
`55edfece518bdd227371ea04276a2f19`). The dataset's own paper independently describes the
required range for its payload boxes as −80 °C to −60 °C; the label band is used because it is
the regulatory text and it is the wider, more conservative floor.

**No excursion envelope is configured.** The label states no permitted excursion range around
the ULT condition — it states separate *alternative storage conditions* (2–8 °C for up to 10
weeks once thawed; total time out of refrigeration between 8 and 25 °C not to exceed 12 h) and
explicitly forbids −25 to −15 °C for these vials. Treating an alternative storage condition as
an excursion envelope would invent a stability claim the label does not make.

**The allowance hours are a ColdCall benchmark assumption, not a published figure.** Real
thermal-stability budgets for this product are manufacturer data and are not public.
`config.json` sets 12 h and its `policy_note` says exactly why that number and not another,
including the fact that no verdict here depends on it (the least-exposed leg is 13.5 h out of
band, so any allowance below ~13.5 h gives the same 39 verdicts).

**Below-minimum time / the freeze rule.** The freeze rule is left ON (its default), with
`storage_min_c` at the labelled −90 °C. The coldest reading anywhere in this dataset is
−84.031 °C, so no leg has any below-minimum time and the rule never fires — keeping the
label's own floor is both the literal reading of the label and inert on this data, which is
why `no_freeze_rule` was not set. The argument for setting it would be real if a package ever
did go below −90 °C: "freeze" is not a meaningful failure mode for a product whose storage
condition is already −90 °C, and coldcall's freeze rule exists for products that must not
freeze. That decision is deliberately left un-taken rather than taken invisibly.

## Results

All 39 legs score `destroy`, with the independent cross-check agreeing on every one. That is
a property of the source, not of the policy: both tests are dry-ice endurance runs taken to
depletion, so every package warms out of the ULT band and stays out for tens to hundreds of
hours (see `expected.json`'s note for the hand-checked arithmetic on two legs).

## Limitations

- **Not regulatory validation, and not a vaccine disposition.** No vaccine was present in
  either test. Scoring a laboratory container test's thermocouples against a drug label band
  demonstrates that the arithmetic handles ULT records; it says nothing about any real lot.
- **Not shipments.** Stationary laboratory tests of a container that never moved. Nothing here
  carries transport shock, handover, or route context.
- **Test 1's sensor position inside each box varies** and the paper says so — the spread
  between Test 1 legs is partly thermocouple placement, not only package performance.
- **Timezone is inferred, not stated** (see cut rule 4). If the loggers were in fact on UTC or
  on fixed standard time, every leg shifts by a constant and the durations, excursions and
  verdicts are unchanged — the assumption affects only absolute timestamps.
- **The dropped channels are a judgement**, applied by a single mechanical rule and logged by
  the adapter at run time. `TC_TB2` in particular is *real recorded output*; it is excluded as
  an instrument fault, not because its values were inconvenient.
- **No verdict spread.** Every leg destroys, so these pins catch a parser or unit regression
  and an arithmetic sign error, but they cannot catch a threshold regression that only moves
  the release/quarantine boundary.
- The paper's Table 2 describes "a collection of 2 CSV files" while the figshare record holds
  three (the third being the dry-ice weight file). Noted, not resolved.
