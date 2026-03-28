#!/bin/bash
#
# Main orchestration script for event outreach
# Usage: ./run-outreach.sh --config <path-to-config.json> [gather|update|followup|all] [--dry-run]
#

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG=""
ACTION=""
DRY_RUN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="--dry-run"
      echo "[DRY RUN MODE]" >&2
      shift
      ;;
    *)
      if [[ -z "$ACTION" ]]; then
        ACTION="$1"
      fi
      shift
      ;;
  esac
done

ACTION="${ACTION:-all}"

if [[ -z "$CONFIG" ]]; then
  echo "Error: --config <path-to-config.json> is required" >&2
  echo "" >&2
  echo "Usage: $0 --config <path-to-config.json> [gather|update|followup|all] [--dry-run]" >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "Error: config file not found: $CONFIG" >&2
  exit 1
fi

# Validate dependencies
check_deps() {
  local missing=0

  if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found" >&2
    missing=1
  fi

  if ! command -v jq &>/dev/null; then
    echo "Error: jq not found" >&2
    missing=1
  fi

  if ! command -v gog &>/dev/null; then
    echo "Error: gog CLI not found" >&2
    missing=1
  fi

  local beeper_read="$SCRIPTS_DIR/using-beeper/beeper-read.sh"
  if [[ ! -f "$beeper_read" ]]; then
    # Fall back to parent scripts dir (sibling of managing-outreach)
    beeper_read="$(dirname "$SCRIPTS_DIR")/using-beeper/beeper-read.sh"
    if [[ ! -f "$beeper_read" ]]; then
      echo "Error: beeper-read.sh not found" >&2
      missing=1
    fi
  fi

  if [[ -z "${BEEPER_TOKEN:-}" ]]; then
    echo "Error: BEEPER_TOKEN environment variable is not set" >&2
    missing=1
  fi

  if [[ $missing -eq 1 ]]; then
    exit 1
  fi
}

run_gather() {
  echo "Phase: GATHER contacts from Beeper" >&2
  echo "-----------------------------------" >&2
  python3 "$SCRIPTS_DIR/gather_contacts.py" --config "$CONFIG"
}

run_update() {
  echo "Phase: UPDATE spreadsheet statuses" >&2
  echo "-----------------------------------" >&2
  python3 "$SCRIPTS_DIR/update_spreadsheet.py" --config "$CONFIG" $DRY_RUN
}

run_followup() {
  echo "Phase: DRAFT follow-up messages" >&2
  echo "--------------------------------" >&2
  python3 "$SCRIPTS_DIR/draft_beeper_followups.py" --config "$CONFIG"
}

check_deps

case "$ACTION" in
  gather)
    run_gather
    ;;

  update)
    run_update
    ;;

  followup)
    run_followup
    ;;

  all)
    echo "Running ALL phases" >&2
    echo "==================" >&2
    echo "" >&2

    # Pipeline: gather -> update -> followup
    # Each script reads stdin JSON and outputs JSON to stdout
    # Status messages go to stderr
    run_gather | run_update | run_followup
    ;;

  *)
    echo "Usage: $0 --config <path-to-config.json> [gather|update|followup|all] [--dry-run]" >&2
    echo "" >&2
    echo "Commands:" >&2
    echo "  gather   - Scan Beeper for event conversations" >&2
    echo "  update   - Update spreadsheet with current statuses" >&2
    echo "  followup - Draft follow-up messages for approval" >&2
    echo "  all      - Run all phases (gather | update | followup)" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --config <path>  Path to event config.json (required)" >&2
    echo "  --dry-run        Show what would change without writing" >&2
    exit 1
    ;;
esac

echo "" >&2
echo "Outreach skill run complete." >&2
