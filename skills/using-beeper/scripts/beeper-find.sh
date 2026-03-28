#!/bin/bash
# Beeper Smart Search - Find chats, people, and messages across all networks
# Automatically resolves contact names to phone numbers via macOS Contacts
# Usage: beeper-find.sh <query>

BEEPER_URL="http://localhost:23373/v0/mcp"

if [ -z "$BEEPER_TOKEN" ]; then
  echo "Error: BEEPER_TOKEN environment variable is not set." >&2
  exit 1
fi

QUERY="$1"

if [ -z "$QUERY" ]; then
  echo "Usage: beeper-find.sh <query>" >&2
  echo "Examples:" >&2
  echo "  beeper-find.sh 'John Motz'     # Find by contact name (auto-resolves phone)" >&2
  echo "  beeper-find.sh dinner          # Find messages mentioning 'dinner'" >&2
  echo "  beeper-find.sh 818-292-7118    # Find by phone number" >&2
  exit 1
fi

# Function to call Beeper MCP search
beeper_search() {
  local query="$1"
  local query_escaped
  query_escaped=$(printf '%s' "$query" | jq -Rs '.')
  local params="{\"query\":$query_escaped}"
  local request="{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"search\",\"arguments\":$params},\"id\":1}"

  local tmpfile
  tmpfile=$(mktemp)
  curl -s -X POST "$BEEPER_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Authorization: Bearer $BEEPER_TOKEN" \
    -d "$request" > "$tmpfile"

  local sse_data
  sse_data=$(sed -n 's/^data: //p' "$tmpfile")

  if [ -n "$sse_data" ]; then
    echo "$sse_data"
  else
    # Non-SSE error response
    echo "Error: $(cat "$tmpfile")" >&2
  fi
  rm -f "$tmpfile"
}

# Function to check if search found any chats
has_chats() {
  local result="$1"
  echo "$result" | jq -e '.result.content[0].text | contains("# Chats") and (contains("Found") or contains("chatID"))' >/dev/null 2>&1
}

# Function to lookup phone numbers from macOS Contacts
lookup_contact_phones() {
  local name="$1"
  local search_term="$name"
  local result

  # If name has multiple words, use last word (likely last name) for better matching
  if [[ "$name" =~ \  ]]; then
    search_term="${name##* }"
  fi

  result=$(osascript << EOF 2>/dev/null
tell application "Contacts"
    set matchingPeople to every person whose name contains "$search_term"
    set phoneList to ""
    repeat with p in matchingPeople
        try
            set pPhones to value of phones of p
            repeat with ph in pPhones
                set phoneList to phoneList & ph & linefeed
            end repeat
        end try
    end repeat
    return phoneList
end tell
EOF
)

  echo "$result"
}

# First, try direct search
echo "Searching for: $QUERY"
echo ""

RESULT=$(beeper_search "$QUERY")
TEXT=$(echo "$RESULT" | jq -r '.result.content[0].text // .error.message // empty')

# Check if we found chats
if echo "$TEXT" | grep -q "# Chats" && echo "$TEXT" | grep -q "chatID"; then
  echo "$TEXT"
  exit 0
fi

# If no chats found and query looks like a name (contains space or capital letters), try contact lookup
if [[ "$QUERY" =~ [A-Z] ]] && ! [[ "$QUERY" =~ ^[0-9+\-\ \(\)]+$ ]]; then
  echo "No direct matches. Checking macOS Contacts for '$QUERY'..."
  echo ""

  PHONES=$(lookup_contact_phones "$QUERY")

  if [ -n "$PHONES" ]; then
    echo "Found contact(s). Searching by phone number(s)..."
    echo ""

    while IFS= read -r phone; do
      if [ -n "$phone" ]; then
        # Clean phone number for search (remove formatting)
        CLEAN_PHONE=$(echo "$phone" | sed 's/[^0-9+]//g' | sed 's/^+1//' | tail -c 11)
        echo "--- Searching: $phone ---"
        PHONE_RESULT=$(beeper_search "$CLEAN_PHONE")
        PHONE_TEXT=$(echo "$PHONE_RESULT" | jq -r '.result.content[0].text // .error.message // empty')
        echo "$PHONE_TEXT"
        echo ""
      fi
    done <<< "$PHONES"
    exit 0
  else
    echo "No matching contacts found in macOS Contacts."
    echo ""
  fi
fi

# Fall back to original result
echo "$TEXT"
