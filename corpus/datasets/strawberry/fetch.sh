#!/usr/bin/env bash
# Fetch the six shipment-level files of the strawberry cold-chain transport dataset
# (Abdella, Brecht & Uysal — arXiv 2103.12895) from the Hugging Face mirror that carries them
# losslessly, then convert the Parquet to plain CSV so the stdlib-only adapter can read it.
#
# Idempotent: a file whose size AND sha256 already match is not re-downloaded, and the CSV is
# only rewritten when it is missing. Everything is pinned to one immutable commit of the
# mirror, so a re-run a year from now gets byte-identical inputs or fails loudly.
#
# Provenance, licence and processing caveats: corpus/datasets/strawberry/DATASET.md
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="$REPO_ROOT/data/corpus/strawberry"
RAW_DIR="$DEST_DIR/raw"

# Immutable commit of Professor29/Cold-Chain-Transportation-Strawberry (branch main moves;
# this sha does not). Resolve URLs are of the form
#   https://huggingface.co/datasets/<repo>/resolve/<revision>/<path>
HF_REPO="Professor29/Cold-Chain-Transportation-Strawberry"
HF_REV="53ddd9410cf560e6e4647e7dff96655d48811559"

# shipment  bytes    sha256
FILES=(
  "S1 145155 849e959ffddf0a524202dee72b3d337a8f06c6956f94585b1da3f2fd04eadc25"
  "S2 135329 e086dde035554a9535104481196ed801850125690a9fc8bea1dcbd23e7af073c"
  "S3 120816 3267578e79ef349a88a939b42d6fec215d8b69c520def1f2b218f4067e3e6008"
  "S4 120750 e7971fb61b41c0fadfe915f41beb5c1fe7c828c9b4e1190eb4c698051e1921cb"
  "S5 105608 eb6157685e2a53a4a483c7cae438f4f20fa87314aeb7433639abaad69d71faed"
  "S6 120205 d130834bbcf92c976e7c8c466c8797955f2bfb02d46ba887323e6458e1c5c57f"
)

mkdir -p "$RAW_DIR"

sha_of() { sha256sum "$1" | cut -d' ' -f1; }

need_convert=0
for row in "${FILES[@]}"; do
  read -r ship bytes sha <<<"$row"
  name="${ship}_aligned_strict_linear_with_labels.parquet"
  dest="$RAW_DIR/$name"
  if [ -f "$dest" ] && [ "$(wc -c <"$dest" | tr -d ' ')" -eq "$bytes" ] && [ "$(sha_of "$dest")" = "$sha" ]; then
    echo "already fetched: $dest"
  else
    echo "fetching $name ..."
    curl -fsSL --retry 5 --retry-all-errors --retry-delay 3 \
      -o "$dest" "https://huggingface.co/datasets/$HF_REPO/resolve/$HF_REV/benchmark_v2/$name"
    got_bytes="$(wc -c <"$dest" | tr -d ' ')"
    got_sha="$(sha_of "$dest")"
    if [ "$got_bytes" -ne "$bytes" ] || [ "$got_sha" != "$sha" ]; then
      echo "checksum mismatch for $name: got $got_bytes bytes / $got_sha, wanted $bytes / $sha" >&2
      exit 1
    fi
    need_convert=1
  fi
  [ -f "$DEST_DIR/${ship}.csv" ] || need_convert=1
done

if [ "$need_convert" -eq 0 ]; then
  echo "csv already converted: $DEST_DIR/S1.csv .. S6.csv"
  exit 0
fi

# Parquet -> CSV. adapt.py is stdlib-only (repo rule), so the one thing that needs a third-party
# reader happens here, in an ephemeral uv environment with pinned majors — nothing is installed
# into the project venv and nothing global is touched.
CONVERT="$DEST_DIR/_parquet_to_csv.py"
cat >"$CONVERT" <<'PYEOF'
"""Write Time + the nine probe columns of each shipment Parquet out as plain CSV.

Only these ten columns are carried over: everything else in the mirror's file (engineered
W60 window features, risk labels, prediction targets) is derived and is not source telemetry.
Values are written exactly as stored (one decimal, degrees Celsius); missing samples stay
empty cells. No resampling, no interpolation, no rounding.
"""

import csv
import os
import sys
from pathlib import Path

import pandas as pd

SENSORS = [
    "Front_Top", "Front_Middle", "Front_Bottom",
    "Middle_Top", "Middle_Middle", "Middle_Bottom",
    "Rear_Top", "Rear_Middle", "Rear_Bottom",
]

dest_dir = Path(sys.argv[1])
raw_dir = dest_dir / "raw"
for ship in ("S1", "S2", "S3", "S4", "S5", "S6"):
    frame = pd.read_parquet(raw_dir / f"{ship}_aligned_strict_linear_with_labels.parquet")
    out = dest_dir / f"{ship}.csv"
    # Write to a temp path and rename: an interrupted conversion must never leave a
    # truncated CSV at the final path, where a later fetch run would accept it as done.
    tmp = out.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ts", *SENSORS])
        for row in frame[["Time", *SENSORS]].itertuples(index=False):
            ts = pd.Timestamp(row[0]).strftime("%Y-%m-%dT%H:%M:%S")
            cells = ["" if pd.isna(v) else f"{float(v):.1f}" for v in row[1:]]
            writer.writerow([ts, *cells])
    os.replace(tmp, out)
    print(f"wrote {out} ({len(frame)} rows)")
PYEOF

echo "converting parquet -> csv ..."
uv run --project "$REPO_ROOT" --python 3.12 --quiet \
  --with "pandas>=2.2,<3" --with "pyarrow>=17,<22" \
  python "$CONVERT" "$DEST_DIR"
echo "ok: $DEST_DIR/S1.csv .. S6.csv"
