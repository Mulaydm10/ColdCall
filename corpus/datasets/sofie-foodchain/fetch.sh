#!/usr/bin/env bash
# Fetch the temperature-bearing files from Zenodo record 4392842 (CC BY 4.0).
# Exact record, file IDs, URLs, sizes, and MD5 checksums are pinned below.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="$REPO_ROOT/data/corpus/sofie-foodchain"

mkdir -p "$DEST_DIR"

fetch_one() {
  local name="$1"
  local file_id="$2"
  local expected_bytes="$3"
  local expected_md5="$4"
  local url="$5"
  local dest="$DEST_DIR/$name"
  local part="$dest.part"

  if [ -f "$dest" ] \
    && [ "$(wc -c < "$dest" | tr -d ' ')" -eq "$expected_bytes" ] \
    && [ "$(md5sum "$dest" | awk '{print $1}')" = "$expected_md5" ]; then
    echo "already fetched: $dest (Zenodo file $file_id)"
    return
  fi

  rm -f "$part"
  echo "fetching $name (Zenodo file $file_id) ..."
  curl -fsS -o "$part" "$url"

  local actual_bytes
  local actual_md5
  actual_bytes="$(wc -c < "$part" | tr -d ' ')"
  actual_md5="$(md5sum "$part" | awk '{print $1}')"
  if [ "$actual_bytes" -ne "$expected_bytes" ] || [ "$actual_md5" != "$expected_md5" ]; then
    echo "$name verification failed: bytes=$actual_bytes md5=$actual_md5" >&2
    rm -f "$part"
    return 1
  fi
  mv "$part" "$dest"
  echo "ok: $dest ($actual_bytes bytes, md5:$actual_md5)"
}

fetch_one \
  "transport_farm_warehouse.json" \
  "05ea0a1d-bc2a-49eb-b556-823ea1bcc4c7" \
  690944 \
  "f1a5c885487413e7169fe13e71052b56" \
  "https://zenodo.org/api/records/4392842/files/transport_farm_warehouse.json/content"

fetch_one \
  "transport_warehouse_supermarket.json" \
  "0e8c2d83-971e-4343-8cea-f7e021a5037b" \
  423770 \
  "15dd401ad5f1dee76968c25337049a0e" \
  "https://zenodo.org/api/records/4392842/files/transport_warehouse_supermarket.json/content"

fetch_one \
  "warehouse.csv" \
  "5fd95ec0-5350-4d56-b8e9-03f93a686c27" \
  118444 \
  "1b07d04a3b0afd0263d9bd41f06ad2eb" \
  "https://zenodo.org/api/records/4392842/files/warehouse.csv/content"
