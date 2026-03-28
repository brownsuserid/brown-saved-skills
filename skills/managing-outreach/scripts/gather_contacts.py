#!/usr/bin/env python3
"""
Gather outreach contacts from Beeper for an event.

Lists all LinkedIn chats via search_chats (paginating through every page)
to find all conversations where outreach was sent.

Usage:
    python3 gather_contacts.py --config path/to/config.json

Output:
    JSON to stdout: {"scan_date": "...", "contacts": [...]}
    Status messages to stderr.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BEEPER_READ = os.path.join(
    os.path.dirname(SCRIPT_DIR), "using-beeper", "beeper-read.sh"
)

# Regex to parse search_chats output
# Format: ## Name (chatID: !xxx:beeper.local)
CHAT_LINE_RE = re.compile(r"^## (.+?) \(chatID: ([^)]+)\)$", re.MULTILINE)

# Regex to extract pagination cursor (base64-encoded for search_chats)
CURSOR_RE = re.compile(r"Next page \(older\): cursor='([^']+)', direction='(\w+)'")


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_deps() -> None:
    """Check that required dependencies are available."""
    if not os.environ.get("BEEPER_TOKEN"):
        print("Error: BEEPER_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(BEEPER_READ):
        print(f"Error: beeper-read.sh not found at {BEEPER_READ}", file=sys.stderr)
        sys.exit(1)


def call_beeper(tool: str, params: dict) -> str | None:
    """Call beeper-read.sh and return the text output, or None on failure."""
    try:
        result = subprocess.run(
            [BEEPER_READ, tool, json.dumps(params)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(
                f"  Warning: beeper-read.sh {tool} failed: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  Warning: beeper-read.sh {tool} timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Warning: beeper-read.sh {tool} error: {e}", file=sys.stderr)
        return None


def list_all_linkedin_chats() -> list[dict]:
    """Paginate through search_chats to get ALL LinkedIn conversations."""
    all_chats: list[dict] = []
    seen_ids: set[str] = set()
    cursor: str | None = None
    page = 0

    while True:
        page += 1
        params: dict = {"accountIDs": ["linkedin"]}
        if cursor:
            params["cursor"] = cursor
            params["direction"] = "before"

        print(f"  Listing LinkedIn chats page {page}...", file=sys.stderr)
        raw = call_beeper("search_chats", params)
        if raw is None:
            break

        # Parse chat entries from ## headers
        matches = CHAT_LINE_RE.findall(raw)
        if not matches:
            break

        new_count = 0
        for name, chat_id in matches:
            if chat_id in seen_ids:
                continue
            seen_ids.add(chat_id)
            new_count += 1
            all_chats.append(
                {
                    "name": name.strip(),
                    "chat_id": chat_id.strip(),
                    "channel": "LinkedIn",
                }
            )

        print(
            f"    {len(matches)} chats on page ({new_count} new, {len(all_chats)} total)",
            file=sys.stderr,
        )

        # Check for next page
        cursor_match = CURSOR_RE.search(raw)
        if cursor_match:
            next_cursor = cursor_match.group(1)
            if next_cursor != cursor:
                cursor = next_cursor
            else:
                break
        else:
            break

    return all_chats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gather outreach contacts from Beeper for an event"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to event config.json",
    )
    args = parser.parse_args()

    validate_deps()
    load_config(args.config)  # validate config exists

    # List ALL LinkedIn chats — every one is a potential outreach contact
    print("Listing all LinkedIn conversations from Beeper...", file=sys.stderr)
    chats = list_all_linkedin_chats()
    print(f"  Found {len(chats)} LinkedIn conversations", file=sys.stderr)

    # Build contacts (status defaults to "Invited" — update phase will refine)
    today = datetime.now(timezone.utc).date().isoformat()
    contacts = []
    for chat in chats:
        contacts.append(
            {
                "name": chat["name"],
                "chat_id": chat["chat_id"],
                "channel": chat["channel"],
                "status": "Invited",
                "response": "",
                "last_check": today,
            }
        )

    output = {
        "scan_date": datetime.now(timezone.utc).isoformat(),
        "contacts": contacts,
    }
    print(json.dumps(output, indent=2))
    print(f"\nGather complete: {len(contacts)} contacts", file=sys.stderr)


if __name__ == "__main__":
    main()
