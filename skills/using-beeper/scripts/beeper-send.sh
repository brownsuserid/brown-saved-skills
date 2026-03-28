#!/bin/bash
# Beeper MCP Send Message - Requires Approval
# Usage: beeper-send.sh <chatID> <message_text> [replyToMessageID]

BEEPER_URL="http://localhost:23373/v0/mcp"

if [ -z "$BEEPER_TOKEN" ]; then
  echo "Error: BEEPER_TOKEN environment variable is not set." >&2
  exit 1
fi

CHAT_ID="${1//\\!/!}"
TEXT="$2"
REPLY_TO="$3"

if [ -z "$CHAT_ID" ] || [ -z "$TEXT" ]; then
  echo "Usage: beeper-send.sh <chatID> <message_text> [replyToMessageID]" >&2
  exit 1
fi

# Build arguments JSON using jq to properly escape all values
if [ -n "$REPLY_TO" ]; then
  PARAMS=$(jq -n --arg cid "$CHAT_ID" --arg txt "$TEXT" --arg rid "$REPLY_TO" \
    '{chatID: $cid, text: $txt, replyToMessageID: $rid}')
else
  PARAMS=$(jq -n --arg cid "$CHAT_ID" --arg txt "$TEXT" \
    '{chatID: $cid, text: $txt}')
fi

# Build request body using jq
REQUEST=$(jq -n --argjson params "$PARAMS" \
  '{jsonrpc: "2.0", method: "tools/call", params: {name: "send_message", arguments: $params}, id: 1}')

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
