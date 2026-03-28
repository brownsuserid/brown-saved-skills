#!/bin/bash
# Beeper MCP Write Operations - Requires Approval
# Usage: beeper-write.sh <tool_name> <json_params>

BEEPER_URL="http://localhost:23373/v0/mcp"

if [ -z "$BEEPER_TOKEN" ]; then
  echo "Error: BEEPER_TOKEN environment variable is not set." >&2
  exit 1
fi

TOOL="$1"
PARAMS="$2"
if [ -z "$PARAMS" ]; then
  PARAMS='{}'
fi

# Validate tool is a write operation (focus_app moved to beeper-read.sh)
case "$TOOL" in
  send_message|archive_chat|set_chat_reminder|clear_chat_reminder)
    ;;
  focus_app)
    echo "Error: 'focus_app' is now in beeper-read.sh (non-destructive). Use beeper-read.sh focus_app instead." >&2
    exit 1
    ;;
  *)
    echo "Error: '$TOOL' is not a write tool. Use beeper-read.sh for read operations." >&2
    exit 1
    ;;
esac

# Build request body using jq to properly escape all values
REQUEST=$(jq -n --arg tool "$TOOL" --argjson params "$PARAMS" \
  '{jsonrpc: "2.0", method: "tools/call", params: {name: $tool, arguments: $params}, id: 1}')

# Make request and extract JSON from SSE response
TMPFILE=$(mktemp)
curl -s -X POST "$BEEPER_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $BEEPER_TOKEN" \
  -d "$REQUEST" > "$TMPFILE"

# Extract data line from SSE response
SSE_DATA=$(sed -n 's/^data: //p' "$TMPFILE")

if [ -n "$SSE_DATA" ]; then
  echo "$SSE_DATA" | jq -r '.result.content[0].text // .error.message // .'
else
  cat "$TMPFILE" >&2
  rm -f "$TMPFILE"
  exit 1
fi

rm -f "$TMPFILE"
