# sofie-foodchain — SOFIE table-grape transport and warehouse telemetry

| | |
|---|---|
| Source | SOFIE EU H2020 Food Supply Chain pilot, Zenodo record 4392842 (version 2.0) |
| DOI | Version DOI [10.5281/zenodo.4392842](https://doi.org/10.5281/zenodo.4392842); concept DOI [10.5281/zenodo.4392841](https://doi.org/10.5281/zenodo.4392841) |
| License | CC BY 4.0 (`cc-by-4.0` on the Zenodo record) |
| Domain | Food logistics: table grapes moving from farm to warehouse to supermarket |
| Pilot status | Real operational pilot data, anonymized before publication; not synthetic |

The concept DOI identifies the evolving dataset and currently redirects to record 4392842.
The version DOI identifies the immutable version used here. Downloads and checksums are pinned
to version 2.0, record 4392842.

SOFIE deliverable D5.4 describes the pilot as deployed in a real operational environment at
Grapes Pegasos premises in Greece and says the published sensor data were anonymized, with
product information removed. It also identifies temperature units as degrees Celsius for both
truck-gateway and warehouse-room measurements:
[SOFIE D5.4, Final Validation & Replication Guidelines](https://media.voog.com/0000/0042/0957/files/SOFIE_D5.4-Final_Validation_Replication_Guidelines.pdf).

## Files on record 4392842

| File | Bytes | MD5 | Use here |
|---|---:|---|---|
| `transport_farm_warehouse.json` | 690,944 | `f1a5c885487413e7169fe13e71052b56` | Parsed as truck temperature; excluded by the corpus duration floor |
| `transport_warehouse_supermarket.json` | 423,770 | `15dd401ad5f1dee76968c25337049a0e` | Parsed as truck temperature; excluded by the corpus duration floor |
| `warehouse.csv` | 118,444 | `1b07d04a3b0afd0263d9bd41f06ad2eb` | Temperature legs per monitored room; humidity summarized in the manifest |
| `synfield.csv` | 696 | `d2ee6cacac8036da3c5cc141807014b3` | Excluded: daily field GDD/weather, not product movement or storage telemetry |

The two files named `.json` are Mongo shell exports, not strict JSON: they contain
`ObjectId(...)`, `NumberLong(...)`, and a leading comment in one file. The adapter removes only
those wrappers before using the standard-library JSON parser. Each truck record carries one
gateway ID, sensor type, epoch-millisecond timestamp, temperature, and RFID box IDs present.
The box-presence values establish transport context but are not scored. `warehouse.csv` has
`entity_id`, `entity_type`, relative humidity, temperature, and an epoch-millisecond
`time_index`.

## Timestamps and timezone

Both formats store Unix epoch milliseconds. The adapter interprets Unix time in its defined UTC
timescale and emits explicit `Z` timestamps; it does not assume Greek civil time. As an
independent check on the transport export, the timestamp encoded by each Mongo ObjectId's first
four bytes exactly matches the adjacent `header.timestamp.long` value (for example,
`5f6b2379` and `1600856953000` both resolve to `2020-09-23T10:29:13Z`). No source field records
the local wall-clock timezone, so this dataset cannot establish what a local display showed.

## How legs are cut (`adapt.py`)

- The two transport files are already divided by documented route: farm-to-warehouse and
  warehouse-to-supermarket. Within each file, points are grouped by gateway and sensor type.
- Warehouse points are grouped by `entity_id`, producing one candidate stream per monitored
  room. Channels are never aggregated.
- Within every candidate stream, points are sorted by timestamp and split after a silence
  **longer than 30 minutes**. This conservative logger-discontinuity threshold is 30 times the
  warehouse file's observed median interval (~60 s) and 180 times the transport files'
  observed median interval (10 s). No selected stream crosses it: observed maximum gaps are
  about 121 s in the warehouse and 11 s in transport.
- Duplicate instants keep the later-parsed reading. No duplicates occur in version 2.0, but
  the rule is applied before cutting and tested synthetically.
- Legs with fewer than 8 readings or less than 2 hours from first to last reading are dropped.
  Consequently, both genuine transport streams are inspected and parsed but do not become
  corpus legs: farm-to-warehouse spans 117 minutes 37 seconds (706 readings), and
  warehouse-to-supermarket spans 72 minutes 4 seconds (433 readings). The emitted benchmark
  therefore contains the three warehouse-room legs only.
- Canonical leg files contain only UTC timestamp and Celsius temperature because those are the
  fields accepted by `coldcall.cli`. Warehouse humidity is not discarded silently: its
  observed minimum and maximum are recorded as manifest metadata, but humidity is not an input
  to the disposition calculation.

## Food storage-band policy

The pilot documentation identifies the product as table grapes. The ColdCall benchmark profile
uses **-1 to 0 °C**, the optimum table-grape storage range published by the FAO Post-harvest
Compendium:
[Grape: Post-harvest Operations](https://www.fao.org/fileadmin/user_upload/inpho/docs/Post_Harvest_Compendium_-_Grape.pdf).
The same source reports optimum relative humidity of 90–95% and a highest berry freezing point
of -2.1 °C, varying with soluble-solids concentration.

`no_freeze_rule` is enabled because a reading slightly below the -1 °C optimum is not by itself
evidence that grapes froze; sub-minimum time still consumes the excursion budget. The
**2-hour allowed excursion is a ColdCall benchmark policy, not a product label, regulation, or
FAO allowance**. It makes one sustained out-of-band interval of distribution-leg scale consume
the budget; the 50% retest and 100% destroy thresholds are likewise benchmark policy.

This is food-chain validation, not pharmaceutical regulatory validation. The verdict vocabulary
only demonstrates that the deterministic arithmetic can process real food-logistics telemetry.

## Limitations

- The anonymized warehouse file does not associate RFID box IDs with RoomA, RoomB, or RoomC.
  These are real monitored storage-room conditions, but a room leg is not proof that grapes
  occupied that room throughout the interval. RoomA and RoomC are much warmer than the
  table-grape band and may be non-cold rooms.
- The source contains only about 18.4 hours of warehouse data and two short transport journeys.
  It does not represent a full commercial storage life.
- D5.4 summarizes collection frequencies as 20 seconds for truck gateways and 5 minutes for
  warehouse sensors, while these published files sample at about 10 seconds and 1 minute.
  The adapter uses actual timestamps, not the documented nominal frequencies.
- Celsius units are documented in D5.4 but absent from the raw file headers. Sensor calibration,
  accuracy, placement, and whether temperature is air or product-pulp temperature are not
  provided.
- Relative humidity is contextual metadata only; ColdCall's CLI scores temperature.
- The -1 to 0 °C band is published handling guidance, not a lot-specific label. The 2-hour
  allowance and verdict thresholds are explicit benchmark assumptions.
