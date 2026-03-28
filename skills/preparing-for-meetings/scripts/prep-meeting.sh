#!/bin/bash
# Pre-Meeting Prep Script
# Gathers context for meetings starting in 45-75 minutes
#
# Outputs MEETING| lines for the agent to process, then updates the state file.

set -euo pipefail

# Load shared config
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../../../_shared/config.sh
source "$SCRIPT_DIR/../../../_shared/config.sh"

STATE_FILE="${CLAWD_MEMORY}/prep-state.json"

# Ensure memory directory exists
mkdir -p "$CLAWD_MEMORY"

# Load state
if [[ -f "$STATE_FILE" ]]; then
    PREPPED_EVENTS=$(jq -r '.prepared // [] | .[]' "$STATE_FILE" 2>/dev/null || echo "")
else
    PREPPED_EVENTS=""
    echo '{"prepared": [], "lastRun": ""}' > "$STATE_FILE"
fi

# Calculate time window (45-75 minutes from now)
FROM=$(date -v+45M -u +%Y-%m-%dT%H:%M:%SZ)
TO=$(date -v+75M -u +%Y-%m-%dT%H:%M:%SZ)

echo "Checking for meetings between $FROM and $TO"

# Query all calendars
CALENDARS=(
    "aaron@brainbridge.app"
    "aaroneden77@gmail.com"
    "aaron@aitrailblazers.org"
)

FOUND_MEETINGS=0
NEW_EVENT_IDS=()

for CAL in "${CALENDARS[@]}"; do
    EVENTS=$(gog calendar events "$CAL" --from "$FROM" --to "$TO" --account "$CAL" --json 2>/dev/null || echo "[]")

    # Use process substitution to avoid subshell variable scoping issue
    while read -r event; do
        [[ -z "$event" ]] && continue

        EVENT_ID=$(echo "$event" | jq -r '.id // empty')
        SUMMARY=$(echo "$event" | jq -r '.summary // empty')
        START=$(echo "$event" | jq -r '.start.dateTime // .start.date // empty')

        [[ -z "$EVENT_ID" ]] && continue

        # Skip if already prepped
        if echo "$PREPPED_EVENTS" | grep -qF "$EVENT_ID" 2>/dev/null; then
            echo "Already prepped: $SUMMARY"
            continue
        fi

        # Skip Work/Intuit calendar
        if [[ "$CAL" == *"intuit"* ]] || [[ "$SUMMARY" == *"Intuit"* ]]; then
            echo "Skipping work meeting: $SUMMARY"
            continue
        fi

        # Skip all-day events (they have .start.date not .start.dateTime)
        if echo "$event" | jq -e '.start.date' > /dev/null 2>&1; then
            echo "Skipping all-day event: $SUMMARY"
            continue
        fi

        echo "Found meeting: $SUMMARY"
        ((FOUND_MEETINGS++))
        NEW_EVENT_IDS+=("$EVENT_ID")

        # Output for agent to process
        echo "MEETING|$CAL|$EVENT_ID|$SUMMARY|$START"
    done < <(echo "$EVENTS" | jq -c '.events[]' 2>/dev/null)
done

# Update state file with newly discovered events
if [[ ${#NEW_EVENT_IDS[@]} -gt 0 ]]; then
    # Build JSON array of new IDs
    NEW_IDS_JSON=$(printf '%s\n' "${NEW_EVENT_IDS[@]}" | jq -R . | jq -s .)

    # Merge into state file
    jq --argjson new "$NEW_IDS_JSON" \
       --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       '.prepared = (.prepared + $new | unique) | .lastRun = $now' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
else
    # Update lastRun even if no new meetings
    jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       '.lastRun = $now' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

if [[ $FOUND_MEETINGS -eq 0 ]]; then
    echo "No meetings need prep in this window"
fi
