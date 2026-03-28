#!/bin/bash
# Beeper MCP Read Operations - Auto-approved
# Usage: beeper-read.sh <tool_name> [json_params]

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

# Validate tool is read-only (includes focus_app — non-destructive UI navigation)
case "$TOOL" in
  search|get_accounts|get_chat|search_chats|list_messages|search_messages|search_docs|focus_app)
    ;;
  *)
    echo "Error: '$TOOL' is not a read-only tool. Use beeper-send.sh or beeper-write.sh for write operations." >&2
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
  # SSE response — parse normally
  echo "$SSE_DATA" | jq -r '.result.content[0].text // .error.message // .'
else
  # Non-SSE response (server error) — show raw response
  cat "$TMPFILE" >&2
  rm -f "$TMPFILE"
  exit 1
fi

rm -f "$TMPFILE"
