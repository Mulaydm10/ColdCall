#!/usr/bin/env bash
# Configure a running TrueForge instance for ColdCall. Idempotent: safe to re-run.
#
# Every step uses PUT (create-or-replace) rather than POST, so running this twice converges
# on the same state instead of erroring on "already exists". That matters mid-event — the
# fastest recovery from a confused harness is to re-run setup, not to debug it.
#
# Note on routes: PUT goes to the *collection* endpoint (/settings/skills), never to
# /settings/skills/{name} — those per-name paths are read-only and return 404 on a write.
# Verified against this build's OpenAPI spec, which disagrees with the published docs here.
#
# Reads secrets from .env (gitignored). Nothing is echoed back to the terminal.
#
# Usage:  ./scripts/setup_trueforge.sh [--dry-run]
set -uo pipefail

DRY=${1:-}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && set -a && . "$ROOT/.env" && set +a

TF=${TRUEFORGE_URL:-http://localhost:8790}
MODEL_ID=${COLDCALL_MODEL_ID:-gpt-5.6-sol}
# TrueForge's FQN is provider/name, and `name` must match ResourceName (lowercase, no dots),
# so the upstream id is sanitised into a valid local name. `properties` is REQUIRED by the
# schema even though the catalog preset makes it look optional — omitting it is a 400.
MODEL_NAME=$(printf '%s' "$MODEL_ID" | tr '.' '-')
SKIPPED=0
DONE=0
FAILED=0

say()  { printf '  \033[32mok\033[0m    %s\n' "$1"; DONE=$((DONE+1)); }
skip() { printf '  \033[33mskip\033[0m  %-26s %s\n' "$1" "$2"; SKIPPED=$((SKIPPED+1)); }
die()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; exit 1; }

# PUT a manifest and report. Prints the server's error message when it rejects one, because
# a silent 422 during setup is the single most expensive minute of a hackathon.
put() {
  local label="$1" path="$2" body="$3"
  if [[ -n "$DRY" ]]; then printf '  \033[36mdry\033[0m   %-26s PUT %s\n' "$label" "$path"; return 0; fi
  local out code
  out=$(curl -sS -X PUT "$TF$path" -H 'Content-Type: application/json' \
        -w '\n%{http_code}' -d "$body" 2>&1)
  code=$(printf '%s' "$out" | tail -1)
  if [[ "$code" =~ ^2 ]]; then say "$label"; else
    printf '  \033[31mFAIL\033[0m  %-26s HTTP %s — %s\n' "$label" "$code" \
      "$(printf '%s' "$out" | sed '$d' | head -c 200)"
    FAILED=$((FAILED+1))
    return 1
  fi
}

curl -sf --max-time 5 "$TF/api/v1/capabilities" >/dev/null \
  || die "TrueForge is not reachable at $TF (start it: npx @truefoundry/trueforge)"

# A value that is only the prefix of a real credential is not a credential. `.env.example`
# ships `STRIPE_SECRET_KEY=sk_test_` as a hint about the required form, and treating that as
# configured silently registers a connector that will fail on first use — the worst moment to
# discover it. Anything at or below this length is a leftover placeholder, not a secret.
MIN_SECRET_LEN=12

is_placeholder() {
  local v="$1"
  [[ -z "$v" ]] && return 0
  (( ${#v} < MIN_SECRET_LEN )) && return 0
  # Bare scheme prefixes left in .env.example
  [[ "$v" =~ ^(sk_test_|sk_live_|dtn_|ghp_|sbp_|Bearer)$ ]] && return 0
  return 1
}

echo "ColdCall — TrueForge configuration  ($TF)"
echo
echo "Model provider"
if ! is_placeholder "${OPENAI_API_KEY:-}"; then
  put "openai / $MODEL_ID" /api/v1/settings/model-providers "$(cat <<JSON
{"manifest":{"type":"openai","auth":{"api_key":"$OPENAI_API_KEY"},
 "models":[{"model_id":"$MODEL_ID","name":"$MODEL_NAME",
 "properties":{"context_length":${MODEL_CONTEXT_LENGTH:-400000},
 "max_output_tokens":${MODEL_MAX_OUTPUT_TOKENS:-128000},
 "reasoning_efforts":["none","low","medium","high"]}}]}}
JSON
)"
else
  skip "openai" "OPENAI_API_KEY unset — the harness cannot think without this"
fi

echo
echo "Sandbox provider"
# Required for the competition demo (ADR-0005). A local fallback exists and will quietly cover
# an unset key, which is exactly why this reports loudly rather than passing silently: the
# fallback is undocumented and is continuity only, not the sandbox we present to judges.
if ! is_placeholder "${DAYTONA_API_KEY:-}"; then
  # Singleton resource: PUT only, no POST. All four timers are required by the schema.
  put "daytona" /api/v1/settings/sandbox-providers "$(cat <<JSON
{"manifest":{"type":"daytona","auth":{"api_key":"$DAYTONA_API_KEY"},
 "exec_timeout_ms":60000,"auto_stop_interval_in_minutes":5,
 "auto_archive_interval_in_minutes":60,"auto_delete_interval_in_minutes":7200}}
JSON
)"
else
  skip "daytona" "DAYTONA_API_KEY unset — REQUIRED for the demo; needs write:snapshots scope"
fi

echo
echo "MCP servers"
mcp_header() {  # name url token description
  if [[ -z "$2" ]]; then skip "$1" "URL unset"; return 0; fi
  if is_placeholder "$3"; then skip "$1" "token unset or still the .env.example placeholder"; return 0; fi
  put "$1" "/api/v1/settings/mcp-servers" "$(cat <<JSON
{"manifest":{"type":"remote","name":"$1","url":"$2","description":"$4",
 "auth":{"type":"header","headers":{"Authorization":"Bearer $3"}}}}
JSON
)"
}
mcp_header supabase "${SUPABASE_MCP_URL:-}" "${SUPABASE_ACCESS_TOKEN:-}" \
  "Relational store for whatever state the agent must persist. Purpose follows the thesis (ADR-0006)."
mcp_header stripe   "${STRIPE_MCP_URL:-}"   "${STRIPE_SECRET_KEY:-}" \
  "Test-mode billing. Gated at @all: every tool call waits for approval. Purpose follows the thesis."
mcp_header github   "${GITHUB_MCP_URL:-}"   "${GITHUB_TOKEN:-}" \
  "Reads and writes this repo, which is what makes the agent's output auditable."

echo
echo "Skills"
SKILL_REPO=${COLDCALL_SKILL_REPO:-https://github.com/Mulaydm10/ColdCall}
SKILL_REF=${COLDCALL_SKILL_REF:-main}
# `ref` is required by the schema even though the docs read as if pinning is optional.
# The skill is fetched from GitHub at $SKILL_REF, never from the working tree - editing
# SKILL.md locally changes nothing until it is pushed to that ref.
put "coldchain-sop" /api/v1/settings/skills "$(cat <<JSON
{"manifest":{"type":"git","name":"coldchain-sop","url":"$SKILL_REPO",
 "path":"skills/coldchain-sop","ref":"$SKILL_REF",
 "description":"SOP for a pharmaceutical cold-chain temperature-excursion incident: how to open it, how the disposition is computed by the deterministic module rather than by the model, what the evidence bundle must carry, and what may never happen without a human. Aligned with WHO TRS-999 Annex 5 and USP <1079>."}}
JSON
)"

put "repo-evidence" /api/v1/settings/skills "$(cat <<JSON
{"manifest":{"type":"git","name":"repo-evidence","url":"$SKILL_REPO",
 "path":"skills/repo-evidence","ref":"$SKILL_REF",
 "description":"How this repo proves a claim: a result is worth nothing until it is backed by something a human can re-run. Domain-neutral, so it holds whatever the thesis turns out to be."}}
JSON
)"

echo
printf '  %d configured, %d skipped, %d failed\n' "$DONE" "$SKIPPED" "$FAILED"
if [[ $SKIPPED -gt 0 ]]; then
  echo
  echo "  Skipped steps need values in .env (copy .env.example). Re-run this script after"
  echo "  filling them in — it is idempotent, nothing is duplicated."
fi

# A rejected PUT leaves the harness unconfigured, so exiting 0 would tell a caller (or CI, or
# a teammate mid-demo) that the setup succeeded when it did not. A skip is different: it is a
# known-missing key, reported as such, and not a failure.
if [[ $FAILED -gt 0 ]]; then
  echo
  echo "  $FAILED step(s) were rejected by the harness. It is NOT fully configured."
  exit 1
fi
