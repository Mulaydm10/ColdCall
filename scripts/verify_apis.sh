#!/usr/bin/env bash
# Verify every external data source ColdCall depends on is actually reachable and keyless.
#
# Run this before a demo. Each check hits the real endpoint and asserts on the response, so a
# green run means the data path works right now — not that it worked when someone wrote the
# README. Exits non-zero if any required source is down.
#
# Usage:  ./scripts/verify_apis.sh [--verbose]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
echo "Route context, through the real code path"
# Not another curl. This calls src/coldcall/weather.py the way the agent does, at the demo
# leg's own coordinates, so a green line here means the code works now — not merely that the
# endpoint responds. That distinction is this repo's whole evidence rule, and a check that
# proves the URL is up while the caller is broken is exactly the kind of vacuous pass we have
# already had to fix three times elsewhere.
if command -v uv >/dev/null 2>&1; then
  ROUTE=$(cd "$ROOT" 2>/dev/null || cd "$(dirname "${BASH_SOURCE[0]}")/.."; uv run python - <<'PYEOF' 2>&1
import sys
from datetime import datetime, timezone
sys.path.insert(0, "src")
try:
    from coldcall.weather import fetch_ambient
    start = datetime(2021, 11, 9, 12, tzinfo=timezone.utc)
    end = datetime(2021, 11, 10, 4, tzinfo=timezone.utc)
    series = fetch_ambient(39.4565, -0.3465, start, end)
    matched = series.at(datetime(2021, 11, 9, 15, 30, tzinfo=timezone.utc))
    print(f"OK {len(series.times)} hours, {matched} C at the excursion peak hour")
except Exception as exc:  # noqa: BLE001 - a pre-demo check reports, it does not raise
    print(f"FAIL {type(exc).__name__}: {exc}")
PYEOF
)
  if [[ "$ROUTE" == OK* ]]; then
    printf '  \033[32mok\033[0m    %-22s %s\n' "fetch_ambient" "${ROUTE#OK }"; PASS=$((PASS+1))
  else
    printf '  \033[31mFAIL\033[0m  %-22s %s\n' "fetch_ambient" "${ROUTE#FAIL }"; FAIL=$((FAIL+1))
  fi
else
  # A skip is not a pass. This script's contract is that green means the data path works NOW,
  # so silently omitting a check while still reporting "N passed, 0 failed" would let a
  # missing toolchain read as a working one — the precise overclaim the script exists to
  # prevent. uv is a documented prerequisite; not having it is a real failure of the check.
  printf '  \033[31mFAIL\033[0m  %-22s uv not found, so the route-context code path is UNVERIFIED\n' \
    "fetch_ambient"
  FAIL=$((FAIL+1))
fi

echo
echo "Credentialed API"
# GITHUB_TOKEN is the one credential whose absence is SILENT: without it the connector is
# skipped, the approval gate has no tool to call, and the demo's centrepiece does not happen
# while every command still exits 0. A pre-flight that checks five keyless endpoints and not
# this one is checking the things that were never going to fail.
GH_TOKEN_VALUE=$(awk -F= '/^GITHUB_TOKEN=/{sub(/^GITHUB_TOKEN=/,""); gsub(/^["'"'"']|["'"'"']$/,""); print; exit}' \
                 "$ROOT/.env" 2>/dev/null)
GH_TOKEN_VALUE=${GITHUB_TOKEN:-$GH_TOKEN_VALUE}
if [[ -z "$GH_TOKEN_VALUE" ]]; then
  printf '  \033[31mFAIL\033[0m  %-22s GITHUB_TOKEN unset — the approval gate will have no tool to call\n' "GitHub token"
  FAIL=$((FAIL+1))
else
  GH_LOGIN=$(curl -sS -m 20 -H "Authorization: Bearer $GH_TOKEN_VALUE" \
             -H 'Accept: application/vnd.github+json' https://api.github.com/user \
             | jq -r '.login // empty')
  if [[ -n "$GH_LOGIN" ]]; then
    printf '  \033[32mok\033[0m    %-22s authenticated as %s\n' "GitHub token" "$GH_LOGIN"
    PASS=$((PASS+1))
  else
    printf '  \033[31mFAIL\033[0m  %-22s token present but rejected by api.github.com\n' "GitHub token"
    FAIL=$((FAIL+1))
  fi
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
