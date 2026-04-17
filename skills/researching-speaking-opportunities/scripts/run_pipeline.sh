#!/usr/bin/env bash
# Orchestrate the speaking opportunity research pipeline.
#
# Usage:
#   ./run_pipeline.sh [--days 90] [--dry-run]
#
# Phases:
#   1. Fetch upcoming trips from TripIt
#   2. (Interactive) Confirm region scope per trip
#   3. (Interactive) Research events via web search
#   4. (Interactive) Create deals and draft emails
#
# This script runs Phase 1 automatically. Phases 2-4 are interactive
# and require Pablo to work with Aaron to research and create outreach.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../../data/speaking-opportunities"
DAYS="${1:-90}"

# Ensure data directory exists
mkdir -p "$DATA_DIR"

echo "=== Speaking Opportunity Research Pipeline ==="
echo "Looking ${DAYS} days ahead..."
echo ""

# Phase 1: Fetch trips
echo "--- Phase 1: Fetching TripIt events ---"
python3 "${SCRIPT_DIR}/fetch_trips.py" --days "$DAYS" --state "${DATA_DIR}/processed-trips.json"
