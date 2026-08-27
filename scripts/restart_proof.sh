#!/usr/bin/env bash
# Prove that an incident survives the harness dying underneath it.
#
# In pharma the record IS the product: a deviation investigation that evaporates because a
# process restarted is not an audit trail. This kills TrueForge mid-incident, restarts it, and
# reads the same session back — history, verdict and all.
#
# It asserts on the CONTENT, not on the HTTP status. A 200 from a server that came back empty
# would be the worst possible pass.
#
#   ./scripts/restart_proof.sh                 # use the newest session
#   ./scripts/restart_proof.sh <session-id>    # a specific one
#
# Exits non-zero if anything is lost, so it can be a rehearsal gate rather than a vibe check.

set -uo pipefail

TF=${TRUEFORGE_URL:-http://localhost:8790}
API="$TF/api/v1"
SESSION_ARG=${1:-}

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
dim()   { printf '\033[2m%s\033[0m\n' "$*"; }
die()   { red "FAIL: $*"; exit 1; }

command -v jq >/dev/null 2>&1 || die "jq is required (brew install jq)"

curl -sf --max-time 5 "$API/capabilities" >/dev/null \
  || die "TrueForge is not reachable at $TF — start it with: npx @truefoundry/trueforge"

# ---- before -----------------------------------------------------------------------------

if [[ -n "$SESSION_ARG" ]]; then
  SESSION="$SESSION_ARG"
else
  SESSION=$(curl -s "$API/sessions" | jq -r '.data[0].id // empty')
  [[ -n "$SESSION" ]] || die "no sessions exist yet — run: uv run python replay/incident.py"
fi

echo
echo "Restart proof for session $SESSION"
dim "  the session IS the incident record; if it does not survive, nothing else matters"
echo

BEFORE_TURNS=$(curl -s "$API/sessions/$SESSION/turns" | jq '.data | length')
[[ "$BEFORE_TURNS" -gt 0 ]] 2>/dev/null || die "session $SESSION has no turns to lose"

# Count across EVERY turn, not just the last one. The last turn in an incident is usually a
# short approval resume; checking only that would compare 0 against 0 and call it a pass —
# the same empty-pass this script exists to rule out.
tally() {
  local events=0 verdicts=0 turn
  for turn in $(curl -s "$API/sessions/$SESSION/turns" | jq -r '.data[].id'); do
    local body
    body=$(curl -s "$API/sessions/$SESSION/turns/$turn/events")
    events=$(( events + $(printf '%s' "$body" | jq '.data | length') ))
    # `tostring` because .content is not always a string, and a plain `verdict` match
    # because escaping quotes through the shell into jq silently produced a regex that
    # matched nothing — and a matcher that never matches makes this whole check a no-op.
    verdicts=$(( verdicts + $(printf '%s' "$body" \
      | jq '[.data[] | select(.type=="tool.response") | (.content|tostring)]
             | map(select(test("verdict")))
             | length') ))
  done
  printf '%s %s\n' "$events" "$verdicts"
}

# Counts alone do not prove anything survived: an event stream with the same cardinality but
# replaced content would pass. So the real assertion is over a digest of the ordered content
# of every event in every turn — id, type, thread and payload. `sort` on the turn list keeps
# the digest stable if the API ever returns turns in a different order.
digest() {
  local turn
  for turn in $(curl -s "$API/sessions/$SESSION/turns" | jq -r '.data[].id' | sort); do
    curl -s "$API/sessions/$SESSION/turns/$turn/events" \
      | jq -S -c '[.data[] | {id, type, thread_id, content: (.content|tostring),
                              tool_calls: (.tool_calls // [] | tostring)}]'
  done | shasum -a 256 | awk '{print $1}'
}

read -r BEFORE_EVENTS BEFORE_VERDICT <<<"$(tally)"
BEFORE_DIGEST=$(digest)

echo "  before:  $BEFORE_TURNS turn(s), $BEFORE_EVENTS events, $BEFORE_VERDICT verdict-bearing response(s)"
echo "           content digest ${BEFORE_DIGEST:0:16}…"

# A proof that finds nothing to lose proves nothing.
[[ "$BEFORE_VERDICT" -gt 0 ]] \
  || die "session $SESSION carries no verdict — pick an incident session that reached one, \
otherwise this check passes by comparing 0 against 0"

# ---- kill -------------------------------------------------------------------------------

# Target the process actually LISTENING ON THE PORT, not every command line matching
# "trueforge". A developer with an editor, a log tail, or a second checkout open would
# otherwise have unrelated processes SIGKILLed by a script they ran to check persistence.
PORT=${TF##*:}
PORT=${PORT%%/*}
PIDS=$(lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | sort -u || true)
[[ -n "$PIDS" ]] || die "nothing is listening on port $PORT — cannot identify the harness to kill"

# Refuse to kill something that is not the harness. `npx` runs it under node, and killing an
# unrelated service that happens to hold this port would be a genuinely destructive surprise.
for pid in $PIDS; do
  cmd=$(ps -o command= -p "$pid" 2>/dev/null || true)
  case "$cmd" in
    *trueforge*|*node*) ;;
    *) die "pid $pid on port $PORT does not look like TrueForge (\`$cmd\`) — refusing to kill it" ;;
  esac
done

echo
red "  killing the harness mid-incident (pids on :$PORT: $(echo "$PIDS" | tr '\n' ' '))"
# SIGKILL, deliberately: a graceful shutdown that flushes cleanly proves much less than an
# abrupt one. This is the version of the claim worth making on camera.
# shellcheck disable=SC2086
kill -9 $PIDS 2>/dev/null || true

for _ in $(seq 1 30); do
  curl -sf --max-time 2 "$API/capabilities" >/dev/null 2>&1 || break
  sleep 1
done
curl -sf --max-time 2 "$API/capabilities" >/dev/null 2>&1 && die "harness did not actually die"
dim "  harness is down"

# ---- restart ----------------------------------------------------------------------------

echo
dim "  restarting: npx @truefoundry/trueforge"
LOG=$(mktemp -t trueforge-restart)
nohup npx @truefoundry/trueforge >"$LOG" 2>&1 &
disown 2>/dev/null || true

UP=""
for _ in $(seq 1 90); do
  if curl -sf --max-time 2 "$API/capabilities" >/dev/null 2>&1; then UP=1; break; fi
  sleep 2
done
[[ -n "$UP" ]] || { red "  harness did not come back; log at $LOG"; tail -20 "$LOG"; exit 1; }
green "  harness is back up"

# ---- after ------------------------------------------------------------------------------

echo
AFTER_TURNS=$(curl -s "$API/sessions/$SESSION/turns" | jq '.data | length')
read -r AFTER_EVENTS AFTER_VERDICT <<<"$(tally)"
AFTER_DIGEST=$(digest)

echo "  after:   $AFTER_TURNS turn(s), $AFTER_EVENTS events, $AFTER_VERDICT verdict-bearing response(s)"
echo "           content digest ${AFTER_DIGEST:0:16}…"
echo

FAILED=0
[[ "$AFTER_TURNS"   == "$BEFORE_TURNS"   ]] || { red "  turns lost:  $BEFORE_TURNS -> $AFTER_TURNS"; FAILED=1; }
[[ "$AFTER_EVENTS"  == "$BEFORE_EVENTS"  ]] || { red "  events lost: $BEFORE_EVENTS -> $AFTER_EVENTS"; FAILED=1; }
[[ "$AFTER_VERDICT" == "$BEFORE_VERDICT" ]] || { red "  verdict lost: $BEFORE_VERDICT -> $AFTER_VERDICT"; FAILED=1; }
# The assertion that actually matters. Equal counts with different content is exactly the
# silent-corruption case the counts above cannot see.
[[ "$AFTER_DIGEST" == "$BEFORE_DIGEST" ]] \
  || { red "  event CONTENT changed across the restart:"; \
       red "    before $BEFORE_DIGEST"; red "    after  $AFTER_DIGEST"; FAILED=1; }

# Configuration has to survive too. An incident record with no model provider is a museum
# piece — you could read it, but you could not continue the investigation.
MODELS=$(curl -s "$API/models" | jq '.data | length')
SKILLS=$(curl -s "$API/settings/skills" | jq '.data | length')
echo "  config:  $MODELS model(s), $SKILLS skill(s) still registered"
[[ "$MODELS" -gt 0 ]] || { red "  model provider lost"; FAILED=1; }
[[ "$SKILLS" -gt 0 ]] || { red "  skills lost"; FAILED=1; }

echo
if [[ "$FAILED" -eq 0 ]]; then
  green "PASS — the incident record survived a SIGKILL intact."
  dim   "       In pharma the record IS the product."
  exit 0
fi
die "the incident did not survive intact"
