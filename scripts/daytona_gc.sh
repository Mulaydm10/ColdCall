#!/usr/bin/env bash
# Reap the Daytona sandboxes that accumulate from incident runs.
#
# WHY THIS EXISTS, because the failure it prevents is genuinely confusing.
#
# Every incident spawns a sandbox for the orchestrator and one per strand — five or six per
# run, ~3 GiB each. They are stopped and archived rather than deleted, so a handful of
# rehearsals silently walks into Daytona's free-tier ceiling (30 GiB).
#
# When you hit it, the harness does NOT say "out of disk". It reports:
#
#     Sandbox initialization failed: (exit code 1): WARNING: git ls-remote failed (exit 128):
#     fatal: unable to access 'https://github.com/...': Recv failure: Connection reset by peer
#
# which reads exactly like the transient cold-start network race — and that race is real, so
# you retry, and it fails again, and you start debugging the wrong thing. The agent meanwhile
# runs WITHOUT its SOP skill and produces a plausible-looking incident that never reaches an
# approval gate. That is the worst way for this to fail on camera.
#
# Run this before a rehearsal and before recording.
#
#   ./scripts/daytona_gc.sh            # show what would be deleted, delete nothing
#   ./scripts/daytona_gc.sh --yes      # actually delete
#
# Only touches sandboxes that are already stopped or archived — never one that is running.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API=${DAYTONA_API_URL:-https://app.daytona.io/api}
CONFIRM=${1:-}

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
dim()   { printf '\033[2m%s\033[0m\n' "$*"; }
die()   { red "$*"; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 is required"

# Read the key directly rather than sourcing .env. Sourcing it exports every other variable
# into this shell as a side effect, and one malformed line aborts the whole file — which is
# how this key silently came back empty once already.
KEY=$(awk -F= '/^DAYTONA_API_KEY=/{sub(/^DAYTONA_API_KEY=/,""); gsub(/^["'"'"']|["'"'"']$/,""); print; exit}' \
      "$ROOT/.env" 2>/dev/null)
KEY=${DAYTONA_API_KEY:-$KEY}
[[ -n "$KEY" ]] || die "DAYTONA_API_KEY not found in the environment or $ROOT/.env"

LIST=$(curl -sS -m 60 -H "Authorization: Bearer $KEY" "$API/sandbox") \
  || die "could not reach Daytona at $API"

printf '%s' "$LIST" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("Daytona did not return JSON:", raw[:200], file=sys.stderr); sys.exit(1)
if isinstance(data, dict) and data.get("statusCode") == 401:
    print("Daytona rejected the key (401).", file=sys.stderr); sys.exit(1)
items = data if isinstance(data, list) else data.get("items", [])
total = sum((s.get("disk") or 0) for s in items)
reapable = [s for s in items if s.get("state") in ("stopped", "archived", "archiving")]
freed = sum((s.get("disk") or 0) for s in reapable)
print(f"  {len(items)} sandbox(es), {total} GiB total  (free tier ceiling: 30 GiB)")
print(f"  {len(reapable)} reapable, {freed} GiB would be freed")
if total >= 30:
    print("  \033[31mAT OR OVER THE CEILING — sandbox creation will fail with a misleading "
          "network error\033[0m")
with open("/tmp/coldcall-daytona-reap", "w") as fh:
    fh.write("\n".join(s["id"] for s in reapable))
' || exit 1

IDS=$(cat /tmp/coldcall-daytona-reap 2>/dev/null)
[[ -n "$IDS" ]] || { green "nothing to reap."; exit 0; }

if [[ "$CONFIRM" != "--yes" ]]; then
  echo
  dim "  dry run. Re-run with --yes to delete:"
  dim "    ./scripts/daytona_gc.sh --yes"
  exit 0
fi

echo
FAILED=0
for id in $IDS; do
  code=$(curl -sS -m 120 -o /dev/null -w '%{http_code}' -X DELETE \
         -H "Authorization: Bearer $KEY" "$API/sandbox/$id?force=true")
  if [[ "$code" =~ ^2 ]]; then
    printf '  \033[32mdeleted\033[0m %s\n' "${id:0:8}"
  else
    printf '  \033[31mfailed \033[0m %s (HTTP %s)\n' "${id:0:8}" "$code"
    FAILED=$((FAILED+1))
  fi
done

echo
curl -sS -m 60 -H "Authorization: Bearer $KEY" "$API/sandbox" | python3 -c '
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get("items", [])
print(f"  now: {len(items)} sandbox(es), {sum((s.get(\"disk\") or 0) for s in items)} GiB")
'
[[ "$FAILED" -eq 0 ]] || exit 1
