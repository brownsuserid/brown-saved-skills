#!/bin/bash
# Check Claude Code and Antigravity usage limits.
# Requires: jq, python3, macOS Keychain with Claude Code credentials (user:profile scope)
# Antigravity section requires: npx, antigravity-usage, Antigravity IDE running
#
# Usage: check_usage.sh [--json]

set -euo pipefail

JSON_OUTPUT=false
[[ "${1:-}" == "--json" ]] && JSON_OUTPUT=true

# ── Display helpers ───────────────────────────────────────────────────
bar() {
  local pct=${1%.*}  # truncate to int
  (( pct < 0 )) && pct=0
  (( pct > 100 )) && pct=100
  local width=30
  local filled=$(( pct * width / 100 ))
  local empty=$(( width - filled ))
  printf '['
  [ "$filled" -gt 0 ] && printf '%0.s█' $(seq 1 "$filled")
  [ "$empty"  -gt 0 ] && printf '%0.s░' $(seq 1 "$empty")
  printf ']'
}

color_pct() {
  local pct=${1%.*}
  if   (( pct >= 90 )); then printf '\033[1;31m%s%%\033[0m' "$1"   # red
  elif (( pct >= 70 )); then printf '\033[1;33m%s%%\033[0m' "$1"   # yellow
  else                        printf '\033[1;32m%s%%\033[0m' "$1"   # green
  fi
}

format_reset() {
  local ts="$1"
  [ -z "$ts" ] && return
  python3 -c "
from datetime import datetime
import sys
ts = sys.argv[1]
dt = datetime.fromisoformat(ts)
local = dt.astimezone()
print(local.strftime('%a %b %d %I:%M %p %Z'))
" "$ts" 2>/dev/null || echo "$ts"
}

# ══════════════════════════════════════════════════════════════════════
# Claude Code
# ══════════════════════════════════════════════════════════════════════
fetch_claude() {
  local token
  token=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty') || true

  if [ -z "$token" ]; then
    echo '{"error": "No OAuth token. Run: claude auth logout && claude auth login"}'
    return 1
  fi

  local resp
  resp=$(curl -sf "https://api.anthropic.com/api/oauth/usage" \
    -H "Authorization: Bearer $token" \
    -H "anthropic-beta: oauth-2025-04-20" 2>/dev/null) || {
    echo '{"error": "API call failed. Token may need user:profile scope."}'
    return 1
  }

  if echo "$resp" | jq -e '.error' >/dev/null 2>&1; then
    echo "$resp"
    return 1
  fi

  echo "$resp"
}

render_claude() {
  local resp="$1"

  if echo "$resp" | jq -e '.error' >/dev/null 2>&1; then
    printf "  \033[1;31mError:\033[0m %s\n\n" "$(echo "$resp" | jq -r '.error.message // .error')"
    return
  fi

  local five_hr five_reset seven_day seven_reset seven_opus seven_sonnet extra_enabled extra_util
  five_hr=$(echo "$resp" | jq -r '.five_hour.utilization // "n/a"')
  five_reset=$(echo "$resp" | jq -r '.five_hour.resets_at // empty')
  seven_day=$(echo "$resp" | jq -r '.seven_day.utilization // "n/a"')
  seven_reset=$(echo "$resp" | jq -r '.seven_day.resets_at // empty')
  seven_opus=$(echo "$resp" | jq -r '.seven_day_opus.utilization // empty')
  seven_sonnet=$(echo "$resp" | jq -r '.seven_day_sonnet.utilization // empty')
  extra_enabled=$(echo "$resp" | jq -r '.extra_usage.is_enabled // false')
  extra_util=$(echo "$resp" | jq -r '.extra_usage.utilization // empty')

  # Weekly (7-day)
  if [ "$seven_day" != "n/a" ]; then
    local pct_7d=${seven_day%.*}
    printf "  Weekly  (7-day):  "
    color_pct "$seven_day"
    printf "  "
    bar "$pct_7d"
    echo ""
    [ -n "$seven_reset" ] && printf "                    resets %s\n" "$(format_reset "$seven_reset")"
  fi

  # Session (5-hour)
  if [ "$five_hr" != "n/a" ]; then
    local pct_5h=${five_hr%.*}
    printf "  Session (5-hr):   "
    color_pct "$five_hr"
    printf "  "
    bar "$pct_5h"
    echo ""
    [ -n "$five_reset" ] && printf "                    resets %s\n" "$(format_reset "$five_reset")"
  fi

  # Model-specific limits
  if [ -n "$seven_opus" ] && [ "$seven_opus" != "0" ]; then
    local pct_o=${seven_opus%.*}
    printf "  Opus   (7-day):   "
    color_pct "$seven_opus"
    printf "  "
    bar "$pct_o"
    echo ""
  fi

  if [ -n "$seven_sonnet" ] && [ "$seven_sonnet" != "0" ]; then
    local pct_s=${seven_sonnet%.*}
    printf "  Sonnet (7-day):   "
    color_pct "$seven_sonnet"
    printf "  "
    bar "$pct_s"
    echo ""
  fi

  # Extra usage
  if [ "$extra_enabled" == "true" ] && [ -n "$extra_util" ]; then
    local pct_e=${extra_util%.*}
    printf "  Extra usage:      "
    color_pct "$extra_util"
    printf "  "
    bar "$pct_e"
    echo ""
  fi
}

# ══════════════════════════════════════════════════════════════════════
# Antigravity
# ══════════════════════════════════════════════════════════════════════
fetch_antigravity() {
  npx antigravity-usage --method local --json 2>/dev/null || {
    echo '{"error": "Failed to fetch. Is Antigravity IDE running?"}'
    return 1
  }
}

render_antigravity() {
  local resp="$1"

  if echo "$resp" | jq -e '.error' >/dev/null 2>&1; then
    printf "  \033[1;31mError:\033[0m %s\n\n" "$(echo "$resp" | jq -r '.error // .error.message')"
    return
  fi

  local email
  email=$(echo "$resp" | jq -r '.email // "unknown"')
  printf "  Account: %s\n" "$email"

  # Show non-autocomplete models that have been used (remaining < 100%)
  # or all models if none used — show top models by name for a clean view
  echo "$resp" | jq -r '.models[] | select(.isAutocompleteOnly == false) | "\(.label)|\(.remainingPercentage)|\(.resetTime // empty)"' | \
  while IFS='|' read -r label remaining reset; do
    local used_pct
    # remainingPercentage is 0-1, convert to used percentage 0-100
    used_pct=$(echo "$remaining" | awk '{printf "%d", (1 - $1) * 100}')
    # Shorten long labels for alignment
    local short_label="${label}"
    short_label="${short_label/Claude /C.}"
    short_label="${short_label/Gemini /G.}"
    short_label="${short_label/GPT-OSS /GPT-}"
    short_label="${short_label/ (Thinking)/ Think}"
    local label_padded
    label_padded=$(printf "%-20s" "$short_label")
    printf "  %s " "$label_padded"
    color_pct "$used_pct"
    printf "  "
    bar "$used_pct"
    echo ""
  done

  # Reset time (same for all models)
  local reset_time
  reset_time=$(echo "$resp" | jq -r '.models[0].resetTime // empty')
  if [ -n "$reset_time" ]; then
    printf "  Resets:                   %s\n" "$(format_reset "$reset_time")"
  fi

  # Prompt credits
  local credits_avail credits_monthly credits_used_pct
  credits_avail=$(echo "$resp" | jq -r '.promptCredits.available // empty')
  credits_monthly=$(echo "$resp" | jq -r '.promptCredits.monthly // empty')
  credits_used_pct=$(echo "$resp" | jq -r '.promptCredits.usedPercentage // empty')
  if [ -n "$credits_avail" ] && [ -n "$credits_monthly" ]; then
    local used_credits_pct
    used_credits_pct=$(echo "$credits_used_pct" | awk '{printf "%d", $1 * 100}')
    printf "  Prompt credits:           %s / %s (" "$credits_avail" "$credits_monthly"
    color_pct "$used_credits_pct"
    printf " used)\n"
  fi
}

# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

# Fetch both in parallel
CLAUDE_RESP=$(fetch_claude 2>/dev/null || true)
AG_RESP=$(fetch_antigravity 2>/dev/null || true)

# ── JSON output mode ──────────────────────────────────────────────────
if $JSON_OUTPUT; then
  jq -n \
    --argjson claude "$(echo "${CLAUDE_RESP:-null}" | jq '.' 2>/dev/null || echo 'null')" \
    --argjson antigravity "$(echo "${AG_RESP:-null}" | jq '.' 2>/dev/null || echo 'null')" \
    '{claude_code: $claude, antigravity: $antigravity}'
  exit 0
fi

# ── Render ────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          AI Coding Tool Usage            ║"
echo "  ╚══════════════════════════════════════════╝"

echo ""
echo "  Claude Code"
echo "  ─────────────────────────────────────────"
if [ -n "$CLAUDE_RESP" ]; then
  render_claude "$CLAUDE_RESP"
else
  printf "  \033[1;31mUnavailable\033[0m\n"
fi

echo ""
echo "  Antigravity"
echo "  ─────────────────────────────────────────"
if [ -n "$AG_RESP" ]; then
  render_antigravity "$AG_RESP"
else
  printf "  \033[1;31mUnavailable\033[0m (is the IDE running?)\n"
fi

echo ""
