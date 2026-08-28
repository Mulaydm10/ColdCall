#!/usr/bin/env bash
# Fetch a bounded byte-range sample of the Zenodo 7907515 telemetry file (CC-BY-4.0).
# Idempotent: skips the download when the sample is already the expected size.
# The full file is ~402 MB and is never downloaded — see corpus/datasets/zenodo-ll1/DATASET.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="$REPO_ROOT/data/corpus/zenodo-ll1"
DEST="$DEST_DIR/ll1_raw_sample.json"
URL="https://zenodo.org/api/records/7907515/files/LL1_raw_messages_Public.json/content"
# First 20 MB: enough to carry every device the 2.9 MB demo sample saw, across a longer span,
# so the corpus can cut multiple legs per device. A range request is a supported access path
# (the server advertises accept-ranges: bytes).
RANGE="0-20000000"
EXPECTED_BYTES=20000001

mkdir -p "$DEST_DIR"
if [ -f "$DEST" ] && [ "$(wc -c < "$DEST" | tr -d ' ')" -eq "$EXPECTED_BYTES" ]; then
  echo "already fetched: $DEST"
  exit 0
fi

echo "fetching bytes $RANGE of Zenodo 7907515 LL1_raw_messages_Public.json ..."
curl -fsS -r "$RANGE" -o "$DEST" "$URL"
BYTES="$(wc -c < "$DEST" | tr -d ' ')"
if [ "$BYTES" -ne "$EXPECTED_BYTES" ]; then
  echo "unexpected sample size $BYTES (wanted $EXPECTED_BYTES) — server range support changed?" >&2
  exit 1
fi
echo "ok: $DEST ($BYTES bytes)"
