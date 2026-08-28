"""Adapt the ORNL/Carrier ultra-low-temperature vaccine container tests into corpus legs.

Source: figshare 14888121 (CC BY 4.0), the data record behind Sci Data 9, 67 (2022),
https://doi.org/10.1038/s41597-022-01167-y. Two measured laboratory tests of a refrigerated
shipping container loaded with dry-ice vaccine packages. Full provenance, channel meanings
and every assumption made here are in ``DATASET.md`` next to this file; the ones that change
numbers are repeated below because they belong with the code that applies them.

What becomes a leg
------------------
One leg per package thermocouple — the sensor inside a dry-ice-loaded vaccine package — for
the whole recorded test. Container-air, supply/return, ambient, O2 and CO2 channels are not
product temperature and are dropped. Channels are selected structurally:

* Test 1: columns whose *second* header row (the per-column label row) reads ``b<N>`` — the
  21-box layout of Fig. 4. The file carries b1..b20; the ambient comparison box b0 is not in it.
* Test 2: columns named ``TC_TB<N>`` — the payload-box thermocouples of Fig. 7.

then filtered by one physical rule: a channel whose **median reading is above 0 °C was not
inside a dry-ice-loaded package**, whatever the header claims. That drops exactly three
channels (documented in ``DATASET.md``): Test 2's ``TC_TB21``/``TC_TB22``, which sit at
laboratory room temperature throughout, and ``TC_TB2``, a detached/faulted thermocouple that
swings between −86 °C and +64 °C with 622 minute-to-minute jumps over 11 °C.

Units and time
--------------
Both files state ``Deg F`` / ``F`` in their unit header row; every temperature is converted
with ``(F − 32) × 5/9`` and nothing else is touched — no smoothing, no interpolation, no
resampling, no dropped outliers inside a kept channel.

Timestamps are naive local wall clock with no zone in the file. Both test platforms are US
Eastern sites (Carrier, East Syracuse NY; ORNL, Oak Ridge TN) and Test 2's record contains a
one-hour forward jump at exactly 2021-03-14 02:00 — US spring-forward — so the loggers were
running local time *with* DST. They are therefore interpreted in ``America/New_York`` and
emitted as UTC. Test 1 (December) crosses no transition, so there the assumption is a flat
UTC−5. The single Test 2 row stamped 02:00 on the transition date is a local time that does
not exist; ``zoneinfo``'s default (fold=0, i.e. EST) is used, which puts it 1 minute before
the 03:01 EDT row — consistent with the surrounding 1-minute cadence.

Duplicate instants keep the later-parsed reading (the CLI rejects rather than guesses); none
occur in this data, the rule is applied so that a re-published file cannot slip one past.

Stdlib only. Run ``fetch.sh`` first.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "corpus" / "covid-ult"
RAW_DIR = DATA_DIR / "raw"

#: Recording site timezone for both tests — see module docstring.
SITE_TZ = ZoneInfo("America/New_York")

#: A record silence longer than this cuts a new leg. Same threshold the zenodo-ll1 adapter
#: uses. Neither file here needs it (largest real gap: 11 min in Test 1), but a leg must not
#: silently span a dropout if the record is ever re-published with one.
GAP_MINUTES = 180.0
MIN_READINGS = 8
MIN_DURATION_MINUTES = 120.0

#: A channel whose median is warmer than this was not inside a dry-ice package.
PACKAGE_MEDIAN_MAX_C = 0.0


def f_to_c(fahrenheit: float) -> float:
    """Convert °F to °C. Rounded to 4 dp — below the ±1.1 °C thermocouple accuracy the
    paper's Table 3 states, so no measured information is lost, and it keeps the emitted
    legs a third smaller."""
    return round((fahrenheit - 32.0) * 5.0 / 9.0, 4)


def to_utc(naive_local: datetime) -> datetime:
    """Attach the site timezone to a naive wall-clock stamp and express it in UTC."""
    return naive_local.replace(tzinfo=SITE_TZ).astimezone(timezone.utc)


def read_test1(path: Path) -> tuple[list[datetime], dict[str, list[float]]]:
    """Parse Test1_TempCO2O2.csv: 3 header rows (name / label / unit), then `date,time,...`.

    Channels are keyed by their *label* row value (``b1``..``b20``), which is what the paper's
    figures name; the column names (``Pod20``, ``TC12``, ...) are logger channel numbers whose
    ordering does not follow the box numbering.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        next(rows)
        labels = next(rows)
        units = next(rows)
        picked = [
            index
            for index, label in enumerate(labels)
            if len(label) > 1 and label[0] == "b" and label[1:].isdigit()
        ]
        for index in picked:
            if units[index].strip().upper() not in ("F", "DEG F"):
                raise ValueError(
                    f"Test 1 column {labels[index]!r} is in {units[index]!r}, not F — the "
                    "unit header changed and the conversion below would be wrong"
                )
        stamps: list[datetime] = []
        series: dict[str, list[float]] = {labels[i]: [] for i in picked}
        for row in rows:
            if not row or not row[0].strip():
                continue
            stamps.append(
                to_utc(datetime.strptime(f"{row[0]} {row[1]}", "%d-%b-%y %H:%M:%S"))
            )
            for index in picked:
                series[labels[index]].append(float(row[index]))
    return stamps, series


def read_test2(path: Path) -> tuple[list[datetime], dict[str, list[float]]]:
    """Parse Test2_TempCO2O2.csv: 2 header rows (name / unit), then `TIMESTAMP,...`."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        names = next(rows)
        units = next(rows)
        picked = [
            index
            for index, name in enumerate(names)
            if name.startswith("TC_TB") and name[len("TC_TB") :].isdigit()
        ]
        for index in picked:
            if units[index].strip().upper() not in ("F", "DEG F"):
                raise ValueError(
                    f"Test 2 column {names[index]!r} is in {units[index]!r}, not Deg F — the "
                    "unit header changed and the conversion below would be wrong"
                )
        stamps: list[datetime] = []
        series: dict[str, list[float]] = {names[i]: [] for i in picked}
        for row in rows:
            if not row or not row[0].strip():
                continue
            stamps.append(to_utc(datetime.strptime(row[0], "%m/%d/%Y %H:%M")))
            for index in picked:
                series[names[index]].append(float(row[index]))
    return stamps, series


def dedupe(points: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    """Sort by instant and collapse duplicate instants, keeping the later-parsed reading."""
    ordered = sorted(points, key=lambda point: point[0])
    out: list[tuple[datetime, float]] = []
    for point in ordered:
        if out and out[-1][0] == point[0]:
            out[-1] = point
            continue
        out.append(point)
    return out


def cut_legs(points: list[tuple[datetime, float]]) -> list[list[tuple[datetime, float]]]:
    """Split on record silence, then drop stubs that carry too little duration evidence."""
    legs: list[list[tuple[datetime, float]]] = []
    current: list[tuple[datetime, float]] = []
    for point in points:
        if current and (point[0] - current[-1][0]).total_seconds() / 60.0 > GAP_MINUTES:
            legs.append(current)
            current = []
        current.append(point)
    if current:
        legs.append(current)
    return [
        leg
        for leg in legs
        if len(leg) >= MIN_READINGS
        and (leg[-1][0] - leg[0][0]).total_seconds() / 60.0 >= MIN_DURATION_MINUTES
    ]


def build_legs(
    stamps: list[datetime], series: dict[str, list[float]], test: str
) -> list[tuple[str, list[tuple[datetime, float]]]]:
    """Turn one test's parsed channels into (leg_id, points) pairs, in stable order."""
    out: list[tuple[str, list[tuple[datetime, float]]]] = []
    for channel in sorted(series, key=_channel_sort_key):
        celsius = [f_to_c(value) for value in series[channel]]
        if statistics.median(celsius) > PACKAGE_MEDIAN_MAX_C:
            print(
                f"  skip {test}-{channel}: median {statistics.median(celsius):.1f} °C — not "
                "inside a dry-ice package (lab-ambient or detached thermocouple)",
                file=sys.stderr,
            )
            continue
        points = dedupe(list(zip(stamps, celsius, strict=True)))
        for index, leg in enumerate(cut_legs(points)):
            suffix = "" if index == 0 else f"-{index + 1}"
            out.append((f"{test}-{channel.replace('TC_TB', 'B')}{suffix}", leg))
    return out


def _channel_sort_key(channel: str) -> tuple[str, int]:
    digits = "".join(char for char in channel if char.isdigit())
    return (channel.rstrip("0123456789"), int(digits or 0))


def main() -> int:
    raw = {
        "test1": RAW_DIR / "Test1_TempCO2O2.csv",
        "test2": RAW_DIR / "Test2_TempCO2O2.csv",
    }
    missing = [str(path) for path in raw.values() if not path.exists()]
    if missing:
        print(
            f"missing {', '.join(missing)} — run corpus/datasets/covid-ult/fetch.sh first",
            file=sys.stderr,
        )
        return 2

    legs: list[tuple[str, list[tuple[datetime, float]]]] = []
    stamps1, series1 = read_test1(raw["test1"])
    legs += build_legs(stamps1, series1, "test1")
    stamps2, series2 = read_test2(raw["test2"])
    legs += build_legs(stamps2, series2, "test2")

    legs_dir = DATA_DIR / "legs"
    legs_dir.mkdir(parents=True, exist_ok=True)
    manifest_legs = []
    for leg_id, points in legs:
        file_name = f"{leg_id}.json"
        (legs_dir / file_name).write_text(
            json.dumps(
                [{"ts": at.isoformat(), "temp_c": temp} for at, temp in points], indent=1
            )
            + "\n",
            encoding="utf-8",
        )
        manifest_legs.append(
            {
                "id": leg_id,
                "file": f"legs/{file_name}",
                "test": leg_id.split("-")[0],
                "sensor": leg_id.split("-", 1)[1],
                "start": points[0][0].isoformat(),
                "end": points[-1][0].isoformat(),
                "n": len(points),
                "min_c": min(temp for _, temp in points),
                "max_c": max(temp for _, temp in points),
            }
        )

    manifest = {
        "dataset": "covid-ult",
        "source": (
            "https://doi.org/10.6084/m9.figshare.14888121 "
            "(Test1_TempCO2O2.csv, Test2_TempCO2O2.csv), the data record of "
            "https://doi.org/10.1038/s41597-022-01167-y"
        ),
        "legs": manifest_legs,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(manifest_legs)} legs -> {DATA_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
