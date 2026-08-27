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
#
# Uses jq rather than python: this issues irreversible DELETEs, and the other scripts in this
# directory already depend on jq, so there is one less runtime in the destructive path.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API=${DAYTONA_API_URL:-https://app.daytona.io/api}
CONFIRM=${1:-}
CEILING_GIB=30

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
dim()   { printf '\033[2m%s\033[0m\n' "$*"; }
die()   { red "$*"; exit 1; }

command -v jq >/dev/null 2>&1 || die "jq is required (brew install jq / apt install jq)"

# Read the key directly rather than sourcing .env. Sourcing exports every other variable into
# this shell as a side effect, and one malformed line aborts the whole file — which is how
# this key silently came back empty once already.
KEY=$(awk -F= '/^DAYTONA_API_KEY=/{sub(/^DAYTONA_API_KEY=/,""); gsub(/^["'"'"']|["'"'"']$/,""); print; exit}' \
      "$ROOT/.env" 2>/dev/null)
KEY=${DAYTONA_API_KEY:-$KEY}
[[ -n "$KEY" ]] || die "DAYTONA_API_KEY not found in the environment or $ROOT/.env"

# Every call goes through here. It asserts on the HTTP STATUS, not on the shape of the body:
# a 403, a rate-limit, or a 500 returns a JSON object with no `items`, which a shape-only
# check reads as "an empty list of sandboxes" — so the script would report nothing to reap and
# exit 0, telling the operator cleanup succeeded while the quota problem stood untouched.
daytona_get() {
  local url="$1" out code body
  out=$(curl -sS -m 60 -w '\n%{http_code}' -H "Authorization: Bearer $KEY" "$url" 2>&1) \
    || die "could not reach Daytona at $url"
  code=$(printf '%s' "$out" | tail -1)
  body=$(printf '%s' "$out" | sed '$d')
  [[ "$code" =~ ^2 ]] || die "Daytona returned HTTP $code for $url — $(printf '%s' "$body" | head -c 200)"
  printf '%s' "$body" | jq -e 'if type == "array" then true else has("items") end' >/dev/null 2>&1 \
    || die "unexpected response from $url — $(printf '%s' "$body" | head -c 200)"
  printf '%s' "$body"
}

inventory() {  # -> "<count> <disk_gib>"; non-zero if the read or parse failed
  daytona_get "$API/sandbox" \
    | jq -r '(if type == "array" then . else .items end)
             | "\(length) \([.[].disk // 0] | add // 0)"'
}

# `|| exit` is load-bearing: `die` inside a command substitution exits only the SUBSHELL, so
# without this the guard fires, prints, and the script sails on with LIST empty — reporting
# "nothing to reap" on an auth failure. That is the same failure-becomes-empty-success shape
# the guards were added to prevent, one level up.
LIST=$(daytona_get "$API/sandbox") || exit 1

TOTAL=$(printf '%s' "$LIST" | jq -r '(if type=="array" then . else .items end) | length')
DISK=$(printf '%s' "$LIST" | jq -r '(if type=="array" then . else .items end)
                                    | [.[].disk // 0] | add // 0')
# Read the ids into an array rather than a temp file. The previous version wrote them to a
# fixed /tmp path that another local process could pre-create as a symlink or overwrite —
# feeding attacker-chosen ids into irreversible DELETE requests, or truncating someone else's
# file. Nothing about a destructive flow should touch a predictable path.
IDS=()
while IFS= read -r id; do
  [[ -n "$id" ]] && IDS+=("$id")
done < <(printf '%s' "$LIST" | jq -r '(if type=="array" then . else .items end)
                                      | .[] | select(.state == "stopped" or .state == "archived"
                                                     or .state == "archiving") | .id')

FREEABLE=$(printf '%s' "$LIST" | jq -r '(if type=="array" then . else .items end)
                                        | [.[] | select(.state == "stopped" or .state == "archived"
                                                        or .state == "archiving") | .disk // 0]
                                        | add // 0')

printf '  %s sandbox(es), %s GiB total  (free tier ceiling: %s GiB)\n' "$TOTAL" "$DISK" "$CEILING_GIB"
printf '  %s reapable, %s GiB would be freed\n' "${#IDS[@]}" "$FREEABLE"
if [[ "$DISK" -ge "$CEILING_GIB" ]] 2>/dev/null; then
  red "  AT OR OVER THE CEILING — sandbox creation will fail with a misleading network error"
fi

[[ "${#IDS[@]}" -gt 0 ]] || { echo; green "nothing to reap."; exit 0; }

if [[ "$CONFIRM" != "--yes" ]]; then
  echo
  dim "  dry run. Re-run with --yes to delete:"
  dim "    ./scripts/daytona_gc.sh --yes"
  exit 0
fi

echo
FAILED=0
SKIPPED=0
for id in "${IDS[@]}"; do
  # Re-check state immediately before deleting. The list above is a snapshot, and a sandbox
  # that was stopped when it was taken can be running by now — a demo started in the next
  # terminal is exactly how. Deleting it would break the guarantee at the top of this file,
  # and `?force=true` means it would go without complaint.
  state=$(curl -sS -m 30 -H "Authorization: Bearer $KEY" "$API/sandbox/$id" 2>/dev/null \
          | jq -r '.state // "unknown"')
  case "$state" in
    stopped|archived|archiving) ;;
    *)
      printf '  \033[33mskipped\033[0m %s (now %s — not reaping a live sandbox)\n' \
        "${id:0:8}" "$state"
      SKIPPED=$((SKIPPED+1))
      continue
      ;;
  esac
  code=$(curl -sS -m 120 -o /dev/null -w '%{http_code}' -X DELETE \
         -H "Authorization: Bearer $KEY" "$API/sandbox/$id?force=true" 2>/dev/null)
  if [[ "$code" =~ ^2 ]]; then
    printf '  \033[32mdeleted\033[0m %s\n' "${id:0:8}"
  else
    printf '  \033[31mfailed \033[0m %s (HTTP %s)\n' "${id:0:8}" "$code"
    FAILED=$((FAILED+1))
  fi
done

# Verify, and let a failed verification fail the script. Previously this pipeline was
# unguarded and the `FAILED -eq 0` test that followed overwrote its status, so cleanup could
# exit 0 having never confirmed the resulting count — the one thing the operator came for.
echo
if ! AFTER=$(inventory); then
  die "deletions ran but the resulting sandbox count could not be verified"
fi
printf '  now: %s sandbox(es), %s GiB\n' "${AFTER% *}" "${AFTER#* }"
[[ "$SKIPPED" -eq 0 ]] || dim "  $SKIPPED skipped because they were running by the time we got to them"

[[ "$FAILED" -eq 0 ]] || die "$FAILED deletion(s) failed — the quota may still be exhausted"
