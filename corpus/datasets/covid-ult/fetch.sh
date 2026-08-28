#!/usr/bin/env bash
# Fetch the ORNL/Carrier ultra-low-temperature vaccine-container test data (figshare
# 14888121, CC BY 4.0) into data/corpus/covid-ult/raw/.
#
# Idempotent: a file already present with the record's published size and MD5 is left alone.
# Both file IDs, sizes and checksums are pinned to figshare article 14888121 version 1
# (https://doi.org/10.6084/m9.figshare.14888121) as published 2021-06-30.
#
# Test1_DryIceWeight.csv (file 28668009) is deliberately NOT fetched: it is scale readings in
# pounds, not temperature — see corpus/datasets/covid-ult/DATASET.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="$REPO_ROOT/data/corpus/covid-ult/raw"
mkdir -p "$DEST_DIR"

# name|figshare file id|bytes|md5 (all four from the figshare API record for 14888121)
FILES=(
  "Test1_TempCO2O2.csv|28668003|64056341|b8164462feaca1d699a53a2503f92d30"
  "Test2_TempCO2O2.csv|28668012|7457046|a306c744bc037558819b188a9149c853"
)

md5_of() {
  if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1
  else md5 -q "$1"; fi
}

for entry in "${FILES[@]}"; do
  IFS='|' read -r NAME FILE_ID BYTES MD5 <<<"$entry"
  DEST="$DEST_DIR/$NAME"
  if [ -f "$DEST" ] \
    && [ "$(wc -c < "$DEST" | tr -d ' ')" -eq "$BYTES" ] \
    && [ "$(md5_of "$DEST")" = "$MD5" ]; then
    echo "already fetched: $DEST"
    continue
  fi
  echo "fetching $NAME (figshare file $FILE_ID, $BYTES bytes) ..."
  curl -fsSL -o "$DEST" "https://ndownloader.figshare.com/files/$FILE_ID"
  GOT_BYTES="$(wc -c < "$DEST" | tr -d ' ')"
  GOT_MD5="$(md5_of "$DEST")"
  if [ "$GOT_BYTES" -ne "$BYTES" ] || [ "$GOT_MD5" != "$MD5" ]; then
    echo "checksum/size mismatch for $NAME: got $GOT_BYTES bytes md5 $GOT_MD5, " \
         "expected $BYTES bytes md5 $MD5 — the figshare record changed, do not adapt this" >&2
    exit 1
  fi
  echo "ok: $DEST ($GOT_BYTES bytes, md5 $GOT_MD5)"
done
