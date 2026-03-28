#!/bin/bash
# Gather AI newsletter digest emails from Gmail
# Usage: gather-ai-digests.sh [days]
#   days: number of days to look back (default: 7)
# Output: JSON file path containing digest email metadata and bodies
set -euo pipefail

source ~/.openclaw/skills/_shared/config.sh

DAYS="${1:-7}"
ACCOUNT="aaroneden77@gmail.com"
OUTPUT_FILE="/tmp/ai-digests-$(date +%Y%m%d-%H%M%S).json"

# Cleanup temp files on exit
cleanup() {
  rm -f /tmp/ai-digest-messages-*.json
}
trap cleanup EXIT

echo "Gathering AI digest emails (last ${DAYS} days)..." >&2

# Search for digest-labeled emails
echo "  - Searching Gmail for label:digest..." >&2
SEARCH_RESULTS=$(gog gmail messages search "label:digest newer_than:${DAYS}d" \
  --account "$ACCOUNT" \
  --max 50 \
  --json 2>/dev/null || echo '[]')

# Count results
MSG_COUNT=$(echo "$SEARCH_RESULTS" | jq 'if type == "array" then length else .messages // [] | length end' 2>/dev/null || echo "0")
echo "  - Found ${MSG_COUNT} digest emails" >&2

if [ "$MSG_COUNT" -eq 0 ]; then
  cat > "$OUTPUT_FILE" <<EOF
{
  "gathered_at": "$(date -Iseconds)",
  "period_days": ${DAYS},
  "account": "${ACCOUNT}",
  "total_messages": 0,
  "messages": []
}
EOF
  echo "$OUTPUT_FILE"
  exit 0
fi

# Extract message IDs
MSG_IDS=$(echo "$SEARCH_RESULTS" | jq -r 'if type == "array" then .[].id else .messages[]?.id end' 2>/dev/null || echo "")

# Fetch each message
MESSAGES="[]"
for msg_id in $MSG_IDS; do
  echo "  - Fetching message ${msg_id}..." >&2
  MSG_DATA=$(gog gmail get "$msg_id" \
    --account "$ACCOUNT" \
    --json 2>/dev/null || echo '{}')

  if [ -n "$MSG_DATA" ] && [ "$MSG_DATA" != "{}" ]; then
    MESSAGES=$(echo "$MESSAGES" | jq --argjson msg "$MSG_DATA" '. + [$msg]')
  fi
done

# Write output
cat > "$OUTPUT_FILE" <<EOF
{
  "gathered_at": "$(date -Iseconds)",
  "period_days": ${DAYS},
  "account": "${ACCOUNT}",
  "total_messages": $(echo "$MESSAGES" | jq 'length'),
  "messages": $(echo "$MESSAGES" | jq '.')
}
EOF

echo "$OUTPUT_FILE"
