#!/usr/bin/env bash
# Verify every external data source ColdCall depends on is actually reachable and keyless.
#
# Run this before a demo. Each check hits the real endpoint and asserts on the response, so a
# green run means the data path works right now — not that it worked when someone wrote the
# README. Exits non-zero if any required source is down.
#
# Usage:  ./scripts/verify_apis.sh [--verbose]
set -uo pipefail

VERBOSE=${1:-}
PASS=0
FAIL=0
UA="ColdCall/0.1 (agent-harness-hackathon; https://github.com/Mulaydm10/ColdCall)"

check() {
  local name="$1" url="$2" jq_probe="$3"; shift 3
  local body
  body=$(curl -sS --max-time 20 -H "User-Agent: $UA" "$@" "$url" 2>/dev/null)
  if [[ -z "$body" ]]; then
    printf '  \033[31mFAIL\033[0m  %-22s no response\n' "$name"; FAIL=$((FAIL+1)); return 1
  fi
  local probe
  probe=$(printf '%s' "$body" | jq -r "$jq_probe" 2>/dev/null)
  if [[ -z "$probe" || "$probe" == "null" ]]; then
    printf '  \033[31mFAIL\033[0m  %-22s unexpected shape (%s)\n' "$name" "$(printf '%s' "$body" | head -c 80)"
    FAIL=$((FAIL+1)); return 1
  fi
  printf '  \033[32mok\033[0m    %-22s %s\n' "$name" "$(printf '%s' "$probe" | head -c 68)"
  [[ -n "$VERBOSE" ]] && printf '        %s\n' "$url"
  PASS=$((PASS+1)); return 0
}

command -v jq >/dev/null || { echo "jq is required (brew install jq)"; exit 2; }

echo "ColdCall — external data source check  ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
echo
echo "Keyless public APIs"

# Real drug storage rules. storage_and_handling is the field the label text actually lives in.
check "openFDA label" \
  "https://api.fda.gov/drug/label.json?search=openfda.generic_name:insulin+AND+_exists_:storage_and_handling&limit=1" \
  '.results[0].storage_and_handling[0]'

# Route weather along the shipment path. Frankfurt as a fixed probe point.
check "Open-Meteo forecast" \
  "https://api.open-meteo.com/v1/forecast?latitude=50.11&longitude=8.68&hourly=temperature_2m&forecast_days=1" \
  '"\(.hourly.temperature_2m[0]) °C at \(.hourly.time[0])"'

check "Open-Meteo archive" \
  "https://archive-api.open-meteo.com/v1/archive?latitude=50.11&longitude=8.68&start_date=2024-01-01&end_date=2024-01-01&hourly=temperature_2m" \
  '"\(.hourly.temperature_2m[0]) °C at \(.hourly.time[0])"'

# NWS 403s on an empty User-Agent — the header above is load-bearing, not decoration.
check "NWS points" \
  "https://api.weather.gov/points/38.8894,-77.0352" \
  '.properties.forecastHourly'

# Anonymous OpenSky is rate-limited (~400 credits/day) but does not require OAuth.
check "OpenSky states" \
  "https://opensky-network.org/api/states/all?lamin=49.9&lomin=8.4&lamax=50.3&lomax=8.9" \
  '"\(.states | length) aircraft at \(.time)"'

echo
echo "Dataset"
DATASET_URL="https://zenodo.org/api/records/7907515/files/LL1_raw_messages_Public.json/content"
SIZE=$(curl -sIL --max-time 25 "$DATASET_URL" | awk 'tolower($1)=="content-length:"{print $2}' | tail -1 | tr -d '\r')
if [[ -n "$SIZE" && "$SIZE" -gt 0 ]]; then
  printf '  \033[32mok\033[0m    %-22s %s MB (Zenodo 7907515, CC-BY-4.0)\n' "LL1 telemetry" "$((SIZE/1024/1024))"
  PASS=$((PASS+1))
else
  printf '  \033[31mFAIL\033[0m  %-22s could not resolve\n' "LL1 telemetry"; FAIL=$((FAIL+1))
fi

echo
echo "Local harness"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8790/ || echo 000)
if [[ "$CODE" == "200" ]]; then
  printf '  \033[32mok\033[0m    %-22s HTTP 200 on :8790\n' "TrueForge"; PASS=$((PASS+1))
else
  printf '  \033[33mwarn\033[0m  %-22s not running (start: npx @truefoundry/trueforge)\n' "TrueForge"
fi

echo
echo "  $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
