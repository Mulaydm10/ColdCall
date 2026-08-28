"""Adapt the mango air-cargo recordings (doi:10.57745/F9UJGQ) into canonical corpus legs.

Source shape: one tab-separated text file per instrumented carton, exported by the logger
software with a one-line header (``Time<TAB>T_mangoes<TAB>T_Air`` and, on nine of the cartons,
a fourth ``RH_Air`` column). Timestamps are ``DD/MM/YYYY HH:MM``, values use a decimal **point**
(not the comma a French export might have used — checked, see DATASET.md), lines end CRLF.

Two decisions this file makes, both documented at length in DATASET.md:

* **Each temperature channel is its own leg.** ``T_mangoes`` (fruit) and ``T_Air`` (air inside
  the carton) are two physical sensors and they disagree by several degrees; averaging them
  would invent a reading neither sensor took. Hygrometry is not temperature and is dropped.
* **The logger clock is read as UTC+7 (Indochina Time).** The recordings run continuously
  across the Bangkok-Paris flight with no clock jump, so a single zone is in force for the
  whole record; UTC+7 is the packing-house local time and puts the in-flight segment at
  17:07-05:02 UTC, i.e. a ~midnight BKK departure and ~07:00 Paris arrival. The dataset does
  not state the zone — this is an inference, and it moves no verdict, since every rule here is
  duration-based and offsets cancel.

Readings are never invented, smoothed or resampled. Duplicate instants (none occur in the
published files) keep the later-parsed reading, matching ``coldcall.replay.to_readings``, and
a silence longer than 3 h would cut a file into separate legs (none occurs either — every file
is an unbroken 5-minute grid). Both rules are implemented and tested anyway: they are what
makes the leg definition honest rather than a property of this particular download.

Run ``fetch.sh`` first. Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "corpus" / "mango-aircargo"
RAW_DIR = DATA_DIR / "raw"

#: The logger clock's assumed offset — Indochina Time, see the module docstring.
SOURCE_TZ = timezone(timedelta(hours=7))
#: Longest silence that still belongs to one leg. Same threshold as the zenodo-ll1 adapter.
GAP_MINUTES = 180.0
MIN_READINGS = 8
MIN_DURATION_MINUTES = 120.0

#: ``..._INRAE_<i>_<j>_<k>_Temp.txt`` — the carton's position in the unit load device, with
#: ``k`` the vertical layer (Instrumentation_position_ULD.PNG in the same record).
NAME_RE = re.compile(
    r"^00_All_Recording_Packing_House_to_Arrival_At_INRAE_(\d+)_(\d+)_(\d+)_Temp(?:_Hum)?\.txt$"
)
#: Header column -> the channel suffix its leg id carries. RH_Air is humidity, not temperature.
CHANNELS = {"T_mangoes": "mangoes", "T_Air": "air"}


def parse_file(text: str) -> dict[str, list[tuple[datetime, float]]]:
    """Parse one logger export into ``{channel: [(instant, celsius), ...]}``.

    Raises:
        ValueError: on a header without a recognised temperature column, or a row whose field
            count does not match the header. Either means the export shape changed, and
            guessing which column is the temperature is exactly the kind of guess that ends up
            in a disposition.
    """
    lines = [line for line in text.replace("\r\n", "\n").split("\n") if line.strip()]
    if not lines:
        raise ValueError("empty file")
    header = [cell.strip().lstrip("\ufeff") for cell in lines[0].split("\t")]
    if header[0] != "Time":
        raise ValueError(f"unexpected first column {header[0]!r}, wanted 'Time'")
    wanted = {index: CHANNELS[name] for index, name in enumerate(header) if name in CHANNELS}
    if not wanted:
        raise ValueError(f"no temperature column in header {header!r}")

    series: dict[str, list[tuple[datetime, float]]] = {name: [] for name in wanted.values()}
    for number, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != len(header):
            raise ValueError(f"line {number}: {len(cells)} fields, header has {len(header)}")
        instant = datetime.strptime(cells[0].strip(), "%d/%m/%Y %H:%M").replace(
            tzinfo=SOURCE_TZ
        )
        for index, channel in wanted.items():
            series[channel].append((instant, float(cells[index].strip())))
    return series


def cut_legs(points: list[tuple[datetime, float]]) -> list[list[tuple[datetime, float]]]:
    """Split one channel's time-ordered readings on silence, then drop the too-short ones.

    Duplicate instants keep the later-parsed reading: both values are real logger output, and
    the survivor is the one that owns the interval to the next point.
    """
    legs: list[list[tuple[datetime, float]]] = []
    current: list[tuple[datetime, float]] = []
    for point in points:
        if current and (point[0] - current[-1][0]).total_seconds() / 60.0 > GAP_MINUTES:
            legs.append(current)
            current = []
        if current and point[0] == current[-1][0]:
            current[-1] = point
            continue
        current.append(point)
    if current:
        legs.append(current)
    return [
        leg
        for leg in legs
        if len(leg) >= MIN_READINGS
        and (leg[-1][0] - leg[0][0]).total_seconds() / 60.0 >= MIN_DURATION_MINUTES
    ]


def main() -> int:
    raw_files = sorted(RAW_DIR.glob("00_All_Recording_*.txt"))
    if not raw_files:
        print(
            f"no recordings under {RAW_DIR} — run corpus/datasets/mango-aircargo/fetch.sh first",
            file=sys.stderr,
        )
        return 2

    legs_dir = DATA_DIR / "legs"
    legs_dir.mkdir(parents=True, exist_ok=True)
    manifest_legs = []
    for path in raw_files:
        match = NAME_RE.match(path.name)
        if match is None:
            raise ValueError(f"unexpected file name {path.name}")
        position = "-".join(match.groups())
        series = parse_file(path.read_text(encoding="utf-8-sig"))
        for channel in sorted(series):
            ordered = sorted(series[channel], key=lambda point: point[0])
            for index, leg in enumerate(cut_legs(ordered)):
                suffix = f"-{index + 1}" if index else ""
                leg_id = f"box-{position}-{channel}{suffix}"
                file_name = f"{leg_id}.json"
                (legs_dir / file_name).write_text(
                    json.dumps(
                        [
                            {
                                "ts": instant.astimezone(timezone.utc).isoformat(),
                                "temp_c": celsius,
                            }
                            for instant, celsius in leg
                        ],
                        indent=1,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                manifest_legs.append(
                    {
                        "id": leg_id,
                        "file": f"legs/{file_name}",
                        "carton": position,
                        "channel": channel,
                        "source_file": path.name,
                        "start": leg[0][0].astimezone(timezone.utc).isoformat(),
                        "end": leg[-1][0].astimezone(timezone.utc).isoformat(),
                        "n": len(leg),
                    }
                )

    manifest = {
        "dataset": "mango-aircargo",
        "source": (
            "https://doi.org/10.57745/F9UJGQ (Recherche Data Gouv; "
            "00_All_Recording_Packing_House_to_Arrival_At_INRAE_*_Temp[_Hum].txt)"
        ),
        "legs": manifest_legs,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{len(manifest_legs)} legs from {len(raw_files)} cartons "
        f"-> {DATA_DIR / 'manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
