#!/bin/bash
# Run the bi-weekly deal review
# This script gathers deals, generates a report, saves it, and sends it to Telegram

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
OUTPUT_DIR="$SKILL_DIR/output/sales-deal-review"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Generate timestamp for filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATA_FILE="$OUTPUT_DIR/deals_${TIMESTAMP}.json"
REPORT_FILE="$OUTPUT_DIR/report_${TIMESTAMP}.md"

echo "=== Deal Review (BB + AITB) ===" >&2
echo "Timestamp: $TIMESTAMP" >&2
echo "" >&2

# Check for Airtable token
if [ -z "$AIRTABLE_TOKEN" ]; then
    echo "Error: AIRTABLE_TOKEN not set in environment" >&2
    echo "Error: AIRTABLE_TOKEN must be set" >&2
    exit 1
fi

# Step 1: Gather deals
echo "Step 1: Gathering deals from BB + AITB Airtable..." >&2
python3 "$SCRIPT_DIR/gather_deals.py" > "$DATA_FILE"

if [ $? -ne 0 ]; then
    echo "Error gathering deals" >&2
    exit 1
fi

echo "Saved deal data to: $DATA_FILE" >&2
echo "" >&2

# Step 2: Generate report
echo "Step 2: Generating report..." >&2
python3 "$SCRIPT_DIR/generate_report.py" "$DATA_FILE" > "$REPORT_FILE"

if [ $? -ne 0 ]; then
    echo "Error generating report" >&2
    exit 1
fi

echo "Saved report to: $REPORT_FILE" >&2
echo "" >&2

# Step 3: Display report
echo "Step 3: Report preview:" >&2
echo "===================" >&2
cat "$REPORT_FILE"
echo "===================" >&2
echo "" >&2

# Step 4: Send to Telegram (optional - can be done manually by the agent)
echo "Report saved and ready for delivery." >&2
echo "To send via Telegram, use:" >&2
echo "  cat $REPORT_FILE | openclaw message send --channel telegram --target 1586059256:208299" >&2
echo "" >&2

# Return the report file path for the agent to use
echo "$REPORT_FILE"
