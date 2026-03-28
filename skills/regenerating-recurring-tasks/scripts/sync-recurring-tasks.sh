#!/bin/bash
# Recurring Tasks Skill - Main Script
# Called by the regenerating-recurring-tasks skill to regenerate completed recurring tasks

AIRTABLE_TOKEN="${AIRTABLE_TOKEN:-$1}"
if [ -z "$AIRTABLE_TOKEN" ]; then
    echo "Error: AIRTABLE_TOKEN not set"
    exit 1
fi

# Process Personal and AITB bases only (BB excluded per Aaron's request)
# Format: Name:BaseID:DueDateField
BASES=(
    "Personal:appvh0RXcE3IPCy6X:Due Date"
    "AITB:appweWEnmxwWfwHDa:Due Date"
)

TOTAL_CREATED=0
TOTAL_SKIPPED=0

# URL-encode a string for use in Airtable filterByFormula
urlencode() {
    python3 -c "import urllib.parse; print(urllib.parse.quote('''$1'''))"
}

# Get Unix timestamp for 24 hours ago
CUTOFF_TIME=$(date -v-24H +%s)

for BASE_INFO in "${BASES[@]}"; do
    IFS=':' read -r BASE_NAME BASE_ID DUE_DATE_FIELD <<< "$BASE_INFO"
    TABLE_NAME="Tasks"

    echo ""
    echo "Processing $BASE_NAME base..."

    # Temp file to track processed tasks within this run
    PROCESSED_FILE=$(mktemp /tmp/processed_tasks_${BASE_NAME}.XXXXXX)
    trap "rm -f $PROCESSED_FILE" EXIT

    # Query for completed tasks with recurrence (completed in last 24 hours)
    # We use Last Modified as a proxy for completion time since Status changes update this field
    CUTOFF_ISO=$(date -v-24H -u +%Y-%m-%dT%H:%M:%SZ)
    FILTER=$(urlencode "AND(Status='Completed',NOT(OR(Recurrence='None',Recurrence='')),DATETIME_PARSE(DATETIME_FORMAT({Last Modified},'YYYY-MM-DD HH:mm:ss'))>='${CUTOFF_ISO}')")
    
    COMPLETED_RECURRING=$(curl -s "https://api.airtable.com/v0/${BASE_ID}/${TABLE_NAME}?filterByFormula=${FILTER}" \
      -H "Authorization: Bearer ${AIRTABLE_TOKEN}")

    # Process each completed recurring task using process substitution (not pipe)
    # This avoids subshell isolation -- variables and file writes persist correctly
    while read -r task; do
        [ -z "$task" ] && continue

        _jq() {
            echo "$task" | base64 --decode | jq -r "$1"
        }

        RECORD_ID=$(_jq '.id')
        TASK_NAME=$(_jq '.fields.Task')
        RECURRENCE=$(_jq '.fields.Recurrence')
        ASSIGNEE=$(_jq '.fields.Assignee // empty')
        PROJECT=$(_jq '.fields.Project // empty')
        DEF_OF_DONE=$(_jq '.fields["Definition of Done"] // empty')
        NOTES=$(_jq '.fields.Notes // empty')
        LAST_MODIFIED=$(_jq '.fields["Last Modified"]')

        # Skip if we already processed this task name in this run
        if grep -qF "$TASK_NAME" "$PROCESSED_FILE" 2>/dev/null; then
            echo "  Skipping duplicate: $TASK_NAME (already processed this run)"
            ((TOTAL_SKIPPED++))
            continue
        fi
        echo "$TASK_NAME" >> "$PROCESSED_FILE"

        # Double-check: was this completed within the last 24 hours?
        TASK_MODIFIED_TIME=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${LAST_MODIFIED%%.*}" +%s 2>/dev/null || echo "0")
        if [ "$TASK_MODIFIED_TIME" -lt "$CUTOFF_TIME" ]; then
            echo "  Skipping $TASK_NAME - completed more than 24 hours ago"
            ((TOTAL_SKIPPED++))
            continue
        fi

        # Parse recurrence using Python helper (handles human-entered text)
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PARSE_RESULT=$(python3 "$SCRIPT_DIR/parse_recurrence.py" "$RECURRENCE" 2>&1)
        PARSE_EXIT=$?

        # Check for skip (placeholder text)
        if echo "$PARSE_RESULT" | jq -e '.skip' >/dev/null 2>&1; then
            SKIP_REASON=$(echo "$PARSE_RESULT" | jq -r '.reason')
            echo "  Skipping $TASK_NAME - $SKIP_REASON"
            ((TOTAL_SKIPPED++))
            continue
        fi

        # Check for parse error
        if [ $PARSE_EXIT -ne 0 ]; then
            PARSE_ERROR=$(echo "$PARSE_RESULT" | jq -r '.error // "unknown error"')
            echo "  WARNING: $PARSE_ERROR on $TASK_NAME ($RECORD_ID) - skipping"
            ((TOTAL_SKIPPED++))
            continue
        fi

        NEXT_DATE=$(echo "$PARSE_RESULT" | jq -r '.next_date')
        NORM_RECURRENCE=$(echo "$PARSE_RESULT" | jq -r '.canonical')

        # Check if an active instance already exists (URL-encode the formula)
        EXIST_FILTER=$(urlencode "AND(Task='${TASK_NAME}',Status!='Completed',Status!='Archived')")
        EXISTING_CHECK=$(curl -s "https://api.airtable.com/v0/${BASE_ID}/${TABLE_NAME}?filterByFormula=${EXIST_FILTER}" \
          -H "Authorization: Bearer ${AIRTABLE_TOKEN}")

        EXISTING_COUNT=$(echo "$EXISTING_CHECK" | jq '.records | length')

        if [ -z "$EXISTING_COUNT" ] || [ "$EXISTING_COUNT" -eq 0 ]; then
            echo "  Creating: $TASK_NAME (recurrence: $RECURRENCE, due: $NEXT_DATE, completed: $LAST_MODIFIED)"

            # Build payload using jq for proper JSON escaping
            PAYLOAD=$(jq -n \
                --arg task "$TASK_NAME" \
                --arg status "Not Started" \
                --arg recurrence "$NORM_RECURRENCE" \
                --arg assignee "$ASSIGNEE" \
                --arg project "$PROJECT" \
                --arg dod "$DEF_OF_DONE" \
                --arg notes "$NOTES" \
                --arg deadline "$NEXT_DATE" \
                --arg due_field "$DUE_DATE_FIELD" \
                '{fields: ({Task: $task, Status: $status, Recurrence: $recurrence}
                  + (if $assignee != "" then {Assignee: ($assignee | fromjson)} else {} end)
                  + (if $project != "" then {Project: ($project | fromjson)} else {} end)
                  + (if $dod != "" then {"Definition of Done": $dod} else {} end)
                  + (if $notes != "" then {Notes: $notes} else {} end)
                  + (if $deadline != "" then {($due_field): $deadline} else {} end))
                }')

            # Create new task
            RESULT=$(curl -s -X POST "https://api.airtable.com/v0/${BASE_ID}/${TABLE_NAME}" \
              -H "Authorization: Bearer ${AIRTABLE_TOKEN}" \
              -H "Content-Type: application/json" \
              -d "$PAYLOAD")

            if echo "$RESULT" | jq -e '.id' >/dev/null 2>&1; then
                echo "  Created: $TASK_NAME (due: $NEXT_DATE)"
                # Note: We do NOT modify the completed task - it stays as Completed with Recurrence intact
                ((TOTAL_CREATED++))
            else
                ERROR_MSG=$(echo "$RESULT" | jq -r '.error.message // "Unknown error"')
                # If due date field is computed, retry without it
                if echo "$ERROR_MSG" | grep -q "computed"; then
                    PAYLOAD=$(echo "$PAYLOAD" | jq --arg f "$DUE_DATE_FIELD" 'del(.fields[$f])')
                    RESULT=$(curl -s -X POST "https://api.airtable.com/v0/${BASE_ID}/${TABLE_NAME}" \
                      -H "Authorization: Bearer ${AIRTABLE_TOKEN}" \
                      -H "Content-Type: application/json" \
                      -d "$PAYLOAD")
                    if echo "$RESULT" | jq -e '.id' >/dev/null 2>&1; then
                        echo "  Created: $TASK_NAME (no deadline - computed field)"
                        ((TOTAL_CREATED++))
                    else
                        echo "  Failed to create: $TASK_NAME - $(echo "$RESULT" | jq -r '.error.message // "Unknown error"')"
                    fi
                else
                    echo "  Failed to create: $TASK_NAME - $ERROR_MSG"
                fi
            fi
        else
            echo "  Skipping $TASK_NAME - active instance exists ($EXISTING_COUNT found)"
            ((TOTAL_SKIPPED++))
        fi
    done < <(echo "$COMPLETED_RECURRING" | jq -r '.records[] | select(.fields.Recurrence != null and .fields.Recurrence != "None") | @base64' 2>/dev/null)
done

echo ""
echo "==========================================="
echo "Recurring Tasks Sync Complete"
echo "==========================================="
echo "Created: $TOTAL_CREATED new tasks"
echo "Skipped: $TOTAL_SKIPPED duplicates/existing/old"
echo ""
