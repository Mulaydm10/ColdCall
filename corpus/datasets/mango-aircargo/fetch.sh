#!/usr/bin/env bash
# Fetch the 31 packing-house-to-arrival temperature recordings of the mango air-cargo
# shipment (Recherche Data Gouv doi:10.57745/F9UJGQ, CC-BY-NC-SA 4.0) into
# data/corpus/mango-aircargo/raw/ (gitignored).
#
# Idempotent: a file whose MD5 already matches the checksum the Dataverse record publishes is
# left alone. Every file ID, size and MD5 below is pinned from the dataset's own file
# metadata (api/datasets/:persistentId?persistentId=doi:10.57745/F9UJGQ), so a silently
# republished file fails the check instead of quietly changing a verdict.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="$REPO_ROOT/data/corpus/mango-aircargo/raw"
BASE="https://entrepot.recherche.data.gouv.fr/api/access/datafile"

# id  md5  bytes  filename
FILES="
597061 30d0fb538653159879904870e94de685 22039 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_1_1_Temp_Hum.txt
596910 bb180b9de42ba0635559c4d73a42ba74 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_1_7_Temp_Hum.txt
596969 bbd847499894a65c76f5176e2a0adeb7 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_1_12_Temp_Hum.txt
597108 67f9e4e4b892a976edbef34e9e2e3d0f 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_3_1_Temp.txt
596846 8f94be886baec8e5d6ad04d77ee1ed59 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_3_7_Temp.txt
596874 f13ce09a6b7d3b7b894e30a9d2780244 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_3_12_Temp.txt
597077 e4ecfc6d572c26aae0800174bb17d7ca 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_4_1_Temp_Hum.txt
597030 0c232ebba9695045dcc35a5f68ee8961 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_4_7_Temp.txt
596877 bb41a6d1eb5c271fcad5159c97267e4a 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_1_4_12_Temp.txt
597046 b94dfd7e86a92ba2e62e013b7d16c1c8 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_1_1_Temp.txt
596906 bed1a1df112e468c644674fc7d78a519 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_1_7_Temp.txt
597152 b0df4e7b9276ced10bc097aeca98317a 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_1_12_Temp.txt
597145 00b6bc7d65a2ef9a88c8bca97d0da03a 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_2_1_Temp_Hum.txt
597148 2c878aa749f131aa4eb98a31b1a7cbdc 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_2_3_Temp.txt
597144 6124e963514262a47f939f0005850608 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_2_6_Temp_Hum.txt
596849 8e620a65e400d2c917a9301d41f8c78d 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_2_10_Temp.txt
596905 fdb72c993ed665cbc4194b090b5cf02b 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_2_12_Temp_Hum.txt
597017 e47833e3736960afed58d989a763c15f 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_4_1_Temp.txt
596892 d8eda22b9214772bff50a20f267868a0 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_2_4_7_Temp.txt
596904 2cc33922bbde8c408d6f39338581baa9 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_1_12_Temp.txt
597070 51b12a5893e6880a67d67f526db54c8a 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_2_1_Temp.txt
597074 7d77d036a05d3cb31c5e43bb807c27b3 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_2_3_Temp.txt
596968 e50d4b981eb3a94e1b9ab2ccb9d057b2 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_2_7_Temp.txt
596991 b93a0d5f497d4229bb60d3fff0969f25 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_2_10_Temp.txt
596857 b563a7150e5f53ba8571ce22d71e25c8 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_3_3_12_Temp.txt
596986 48cf2d8b7ea18774db9ed6bdda181c60 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_1_1_Temp_Hum.txt
596993 15978af29a906d2cf1691e5811a215fe 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_1_7_Temp.txt
596826 ad3342989f7d2aab092ebdf40d3fb971 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_2_1_Temp.txt
597130 a940848b31342c275363f4c0ea484054 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_2_7_Temp.txt
596959 d9c324e9d8d1e3ec5046dfa436d7ae81 22038 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_4_1_Temp_Hum.txt
596962 5181ec7dc0adf23160e88dc06aebbf03 18696 00_All_Recording_Packing_House_to_Arrival_At_INRAE_4_4_7_Temp.txt
"

mkdir -p "$DEST_DIR"

md5_of() {
  if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | awk '{print $1}';
  else md5 -q "$1"; fi
}

fetched=0
kept=0
while read -r ID MD5 BYTES NAME; do
  [ -z "${ID:-}" ] && continue
  DEST="$DEST_DIR/$NAME"
  if [ -f "$DEST" ] && [ "$(md5_of "$DEST")" = "$MD5" ]; then
    kept=$((kept + 1))
    continue
  fi
  curl -fsSL -o "$DEST" "$BASE/$ID"
  GOT_BYTES="$(wc -c < "$DEST" | tr -d ' ')"
  GOT_MD5="$(md5_of "$DEST")"
  if [ "$GOT_BYTES" != "$BYTES" ] || [ "$GOT_MD5" != "$MD5" ]; then
    echo "checksum/size mismatch for $NAME (datafile $ID): got $GOT_BYTES bytes / $GOT_MD5," >&2
    echo "expected $BYTES bytes / $MD5 — the record changed; do not adapt this." >&2
    exit 1
  fi
  fetched=$((fetched + 1))
done <<< "$FILES"

echo "ok: $DEST_DIR ($fetched fetched, $kept already present, $((fetched + kept)) total)"
