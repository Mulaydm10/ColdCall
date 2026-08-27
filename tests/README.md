> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# tests/

**There is a green test baseline.** `ADR-0002` is Accepted and landed one in the same change, as
this file previously required.

```sh
uv run pytest          # whole suite
uv run pytest -m smoke # the single trivial test proving the toolchain works end to end
uv run ruff check .    # lint
```

Everything runs through `uv` in the project-local `.venv`. Never a global install — see
`CLAUDE.md` → "Canonical commands".

## Layout and conventions

| File | Covers |
|---|---|
| `test_mkt.py` | Mean kinetic temperature, excursion accounting, the release/review/quarantine verdict |
| `test_replay.py` | Streaming telemetry parser, per-device grouping, duration weighting |

Markers, declared in `pyproject.toml`:

- `smoke` — the minimal green baseline. One test. If this fails, the toolchain is broken, not
  the logic.
- `usp` — properties that come from the regulatory definition of MKT rather than from our
  implementation choices.

## How to write a test here

**Do not hard-code a constant copied from a document.** A fixture transcribed from a PDF proves
only that the transcription was done carefully; if the number is mistyped, the test enshrines
the typo and defends it forever. Assert the properties that *define* the behaviour instead —
and where an implementation is optimised, cross-check it against a second, deliberately naive
implementation written in the test file. `test_mkt.py` does exactly this: the shipped log-sum-exp
version must agree to twelve decimal places with a direct-summation version, so an optimisation
cannot quietly change an answer.

**Tests must not need the network or the dataset.** The real telemetry file is ~402 MB and lives
on Zenodo; `test_replay.py` builds its own fixtures in `tmp_path` in the shape of that file —
pretty-printed array, Mongo extended-JSON timestamps, missing measurements, truncated tail. A
suite that needs a 402 MB download is a suite nobody runs.

**Test the refusals too.** A large share of the value here is what the code declines to do:
dropping a message with no temperature rather than defaulting it to zero, capping how much
weight a logger dropout can absorb, refusing a reading below absolute zero. Those paths are
where a silent wrong answer would come from, so they carry tests of their own.
