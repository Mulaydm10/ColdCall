# Corpus — the disposition maths, run against many real recordings

`DEMO-0001` proves the judged path end to end on **one** real shipment leg (`VCC-118`). This
directory proves **breadth**: the same deterministic pipeline (`coldcall.cli` — disposition +
independent cross-check), run unmodified against many legs from several public datasets in
different domains, with every verdict recorded and regression-pinned.

What this is and is not:

- **It is** a robustness benchmark: real recorded telemetry from independent sources, in
  formats this repo did not choose, pushed through the exact entry point the sandbox runs.
  Every parser bug, timestamp pathology or unit surprise a dataset exposes gets fixed in the
  core, with a test.
- **It is not** regulatory validation. The verdicts below food-domain legs use storage bands
  from documented industry/handling guidance, not drug labels; every profile names its source
  and the allowance hours remain **ColdCall demo policy** (see `data/product_profile.json`'s
  `excursion_duration_finding`). A verdict on strawberries is a demonstration that the maths
  generalises, not a claim that USP applies to fruit.
- **Real recordings only.** Synthetic or simulated datasets are excluded on purpose — the
  project's realism claim is "real data, replayed", and one simulated source would taint it.

## Layout

| Path | What |
|---|---|
| `corpus/datasets/<slug>/DATASET.md` | Provenance: source, DOI/URL, license, record shape, how legs were cut |
| `corpus/datasets/<slug>/fetch.sh` | Idempotent download into `data/corpus/<slug>/` (gitignored, re-fetchable) |
| `corpus/datasets/<slug>/adapt.py` | Stdlib-only: raw format → canonical legs + `manifest.json` |
| `corpus/datasets/<slug>/profile.json` | Storage band + provenance for the product/domain, source named |
| `corpus/datasets/<slug>/config.json` | Runner config: policy flags, paths |
| `corpus/datasets/<slug>/expected.json` | Regression pins: the reviewed verdict per leg |
| `corpus/run_corpus.py` | Runs `coldcall.cli` per leg, compares against pins, writes results |
| `corpus/RESULTS.md` | Generated evidence table (committed, dated) |

## Canonical leg format

The same shape `DEMO-0001` replays — a JSON array of readings:

```json
[ { "ts": "2021-11-09T08:23:09Z", "temp_c": 23.0 }, ... ]
```

Adapters do the honest work: parse the native format, normalise timestamps to UTC, resolve
duplicates/ordering **upstream** (the CLI rejects rather than guesses), and cut multi-journey
device histories into physically contiguous legs (documented per dataset). Adapters never
invent readings and never smooth values.

## Running it

```sh
corpus/datasets/<slug>/fetch.sh          # once per dataset; idempotent
uv run python corpus/datasets/<slug>/adapt.py
uv run python corpus/run_corpus.py       # all fetched datasets; skips unfetched ones
```

The runner invokes `python -m coldcall.cli` as a subprocess — the exact sandbox entry point,
not an import — so what is benchmarked is what ships. Route context (weather) is **not** part
of the corpus run: it is opt-in, network-dependent demo context, while this benchmark is about
the deterministic verdict. Exit code 3 (cross-check disagreement) on any leg fails the run.

## Expected verdicts are pins, not ground truth

No public dataset ships a regulatory disposition to compare against. `expected.json` records
the verdict each leg produced when it was first reviewed for plausibility (band source right,
durations sane, cross-check agreeing) — after that it is a **regression pin**: a code change
that silently moves any verdict fails the corpus. `NEW` legs (no pin yet) are reported, not
failed, so adding data never masquerades as passing.
