#!/bin/bash
# check-email-dashes.sh
# PreToolUse hook: blocks gmail_reply/gmail_send if the body contains
# em dashes or double dashes. Claude will then rewrite and retry.

INPUT=$(cat)

BODY=$(echo "$INPUT" | jq -r '.tool_input.body // empty')

if [ -z "$BODY" ]; then
  exit 0
fi

# Check for em dash or double dash
if echo "$BODY" | grep -qP '\x{2014}|--'; then
  echo "BLOCKED: Email body contains em dashes or double dashes. Rewrite the affected sentences to remove all em dashes (—) and double dashes (--). Do NOT replace with a hyphen. Restructure the sentence instead." >&2
  exit 2
fi

exit 0
