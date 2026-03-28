#!/usr/bin/env python3
"""
Update outreach spreadsheet with contact data.

Reads piped JSON from gather_contacts.py (stdin) OR reads spreadsheet
directly if no piped input. Compares contacts with spreadsheet rows,
appends new contacts, updates changed statuses via gog CLI.
Optionally cross-references Airtable for registrations.

Usage:
    python3 gather_contacts.py --config cfg.json | python3 update_spreadsheet.py --config cfg.json
    python3 update_spreadsheet.py --config cfg.json

Output:
    JSON to stdout: {"updated": [...], "added": [...], "unchanged": [...], "summary": {...}}
    Status messages to stderr.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# STATE_FILE is derived at runtime from the config file's directory
STATE_FILE: str = ""


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_state() -> dict:
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def run_gog(args: list[str]) -> str | None:
    """Run a gog CLI command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["gog"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(
                f"  Warning: gog {' '.join(args[:3])}... failed: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        print("Error: gog CLI not found. Install it or add to PATH.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("  Warning: gog command timed out", file=sys.stderr)
        return None


def read_spreadsheet(config: dict) -> list[dict]:
    """Read current spreadsheet rows via gog CLI --json. Returns list of row dicts."""
    ss = config["spreadsheet"]
    tab = ss["developersTab"]
    columns = ss.get("columns", "A:F")
    raw = run_gog(
        [
            "sheets",
            "get",
            ss["id"],
            f"{tab}!{columns}",
            "--account",
            ss["account"],
            "--json",
        ]
    )
    if raw is None:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  Warning: Could not parse spreadsheet JSON", file=sys.stderr)
        return []

    values = data.get("values", [])
    if len(values) < 2:
        return []

    headers = values[0]
    rows = []
    for row_values in values[1:]:
        row = {}
        for i, header in enumerate(headers):
            row[header] = row_values[i] if i < len(row_values) else ""
        rows.append(row)

    return rows


def find_row_by_name(rows: list[dict], name: str) -> tuple[int | None, dict | None]:
    """Find a spreadsheet row by contact name. Returns (row_index_1based, row_dict)."""
    name_lower = name.lower()
    for i, row in enumerate(rows):
        # Check common column names for the name field
        for key in ("Name", "name", "Contact", "contact"):
            if key in row and row[key].lower() == name_lower:
                return i + 2, row  # +2 for 1-based indexing + header row
    return None, None


def append_contact(config: dict, contact: dict) -> bool:
    """Append a new contact row to the spreadsheet.

    Columns: Name | Company | Channel | Status | Notes | Email
    """
    ss = config["spreadsheet"]
    tab = ss["developersTab"]
    values = json.dumps(
        [
            [
                contact.get("name", ""),
                "",  # Company
                contact.get("channel", ""),
                contact.get("status", ""),
                contact.get("chat_id", ""),  # Notes — store chat_id for lookup
                "",  # Email
            ]
        ]
    )
    result = run_gog(
        [
            "sheets",
            "append",
            ss["id"],
            f"{tab}!A:F",
            "--values-json",
            values,
            "--account",
            ss["account"],
        ]
    )
    return result is not None


def update_status(config: dict, row_num: int, status: str) -> bool:
    """Update a specific cell's status in the spreadsheet."""
    ss = config["spreadsheet"]
    tab = ss["developersTab"]
    # Status is typically column D (4th column)
    cell_range = f"{tab}!D{row_num}"
    result = run_gog(
        [
            "sheets",
            "update",
            ss["id"],
            cell_range,
            "--values-json",
            json.dumps([[status]]),
            "--account",
            ss["account"],
        ]
    )
    return result is not None


def update_notes(config: dict, row_num: int, notes: str) -> bool:
    """Update the Notes column (E) for a row — used to backfill chat_id."""
    ss = config["spreadsheet"]
    tab = ss["developersTab"]
    cell_range = f"{tab}!E{row_num}"
    result = run_gog(
        [
            "sheets",
            "update",
            ss["id"],
            cell_range,
            "--values-json",
            json.dumps([[notes]]),
            "--account",
            ss["account"],
        ]
    )
    return result is not None


def check_airtable_tickets(config: dict) -> set[str]:
    """Check Airtable for ticket purchases. Returns set of attendee names."""
    token = os.environ.get("AIRTABLE_TOKEN")
    if not token:
        return set()

    at_config = config.get("airtable")
    if not at_config:
        return set()

    base_id = at_config["base_id"]
    table = at_config["table"]
    event_filter = at_config["event_filter"]

    formula = urllib.parse.quote(f"{{Event}}='{event_filter}'")
    url = f"https://api.airtable.com/v0/{base_id}/{urllib.parse.quote(table)}?filterByFormula={formula}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Warning: Airtable query failed: {e}", file=sys.stderr)
        return set()

    names = set()
    for record in data.get("records", []):
        fields = record.get("fields", {})
        name = fields.get("Name", fields.get("name", ""))
        if name:
            names.add(name.lower())

    print(f"  Airtable: {len(names)} ticket holders found", file=sys.stderr)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update outreach spreadsheet with contact data"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to event config.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to spreadsheet",
    )
    args = parser.parse_args()

    # Derive state file from config file location
    global STATE_FILE
    STATE_FILE = os.path.join(os.path.dirname(args.config), "outreach-state.json")

    config = load_config(args.config)

    # Read piped JSON from gather_contacts.py, or None
    gathered: dict | None = None
    if not sys.stdin.isatty():
        try:
            gathered = json.load(sys.stdin)
        except json.JSONDecodeError:
            print("Warning: Could not parse piped JSON input", file=sys.stderr)

    # Read current spreadsheet
    print("Reading spreadsheet...", file=sys.stderr)
    sheet_rows = read_spreadsheet(config)
    print(f"  Found {len(sheet_rows)} rows in spreadsheet", file=sys.stderr)

    # Check Airtable for ticket purchases
    ticket_holders = check_airtable_tickets(config)

    # Process contacts
    contacts = gathered["contacts"] if gathered else []
    added = []
    updated = []
    unchanged = []

    # Status priority — higher index = more specific, never overwrite with lower
    status_priority = [
        "Invited",
        "No Response",
        "Follow-up Sent",
        "Interested",
        "Interested - Follow-up Sent",
        "Declined",
        "RSVPd",
        "Ticket Purchased",
    ]

    def status_rank(s: str) -> int:
        s_lower = s.lower()
        for i, p in enumerate(status_priority):
            if p.lower() == s_lower:
                return i
        return -1  # unknown statuses don't override anything

    for contact in contacts:
        name = contact["name"]
        new_status = contact["status"]

        # Override status if Airtable shows ticket purchased
        if name.lower() in ticket_holders:
            new_status = "Ticket Purchased"

        row_num, existing_row = find_row_by_name(sheet_rows, name)

        if existing_row is None:
            # New contact — append to spreadsheet
            if args.dry_run:
                print(f"  [DRY RUN] Would add: {name} ({new_status})", file=sys.stderr)
            else:
                contact["status"] = new_status
                if append_contact(config, contact):
                    print(f"  Added: {name} ({new_status})", file=sys.stderr)
                else:
                    print(f"  Failed to add: {name}", file=sys.stderr)
            added.append({"name": name, "status": new_status})
        else:
            # Existing contact — only update if new status is more specific
            current_status = ""
            for key in ("Status", "status"):
                if key in existing_row:
                    current_status = existing_row[key]
                    break

            # Backfill chat_id into Notes column if missing
            current_notes = existing_row.get("Notes", existing_row.get("notes", ""))
            contact_chat_id = contact.get("chat_id", "")
            if contact_chat_id and not current_notes:
                if args.dry_run:
                    print(
                        f"  [DRY RUN] Would backfill chat_id for: {name}",
                        file=sys.stderr,
                    )
                else:
                    if update_notes(config, row_num, contact_chat_id):
                        print(f"  Backfilled chat_id: {name}", file=sys.stderr)

            new_rank = status_rank(new_status)
            current_rank = status_rank(current_status)

            if new_rank > current_rank and current_status != new_status:
                if args.dry_run:
                    print(
                        f"  [DRY RUN] Would update: {name} ({current_status} -> {new_status})",
                        file=sys.stderr,
                    )
                else:
                    if update_status(config, row_num, new_status):
                        print(
                            f"  Updated: {name} ({current_status} -> {new_status})",
                            file=sys.stderr,
                        )
                    else:
                        print(f"  Failed to update: {name}", file=sys.stderr)
                updated.append(
                    {
                        "name": name,
                        "old_status": current_status,
                        "new_status": new_status,
                    }
                )
            else:
                unchanged.append({"name": name, "status": current_status or new_status})

    # Also check sheet-only contacts against Airtable tickets
    gathered_names = {c["name"].lower() for c in contacts}
    for row in sheet_rows:
        row_name = row.get("Name", row.get("name", ""))
        if not row_name or row_name.lower() in gathered_names:
            continue
        if row_name.lower() in ticket_holders:
            row_num, _ = find_row_by_name(sheet_rows, row_name)
            if row_num and not args.dry_run:
                update_status(config, row_num, "Ticket Purchased")
            updated.append(
                {
                    "name": row_name,
                    "old_status": "unknown",
                    "new_status": "Ticket Purchased",
                }
            )

    # Re-read spreadsheet for final counts
    final_rows = read_spreadsheet(config) if not args.dry_run else sheet_rows
    status_counts: dict[str, int] = {}
    for row in final_rows:
        status = row.get("Status", row.get("status", "Unknown"))
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1

    # Update state file
    state = load_state()
    state["lastRun"] = datetime.now(timezone.utc).isoformat()
    state["contactsProcessed"] = len(contacts)
    state["stats"] = {
        "totalOnSpreadsheet": len(final_rows),
        **{k: v for k, v in status_counts.items()},
    }
    if not args.dry_run:
        save_state(state)

    # Output summary
    result = {
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "spreadsheet_rows": len(final_rows),
        "status_counts": status_counts,
        "summary": {
            "added_count": len(added),
            "updated_count": len(updated),
            "unchanged_count": len(unchanged),
            "total_on_spreadsheet": len(final_rows),
        },
    }

    print(json.dumps(result, indent=2))

    print(
        f"\nSpreadsheet update complete: +{len(added)} added, ~{len(updated)} updated, ={len(unchanged)} unchanged",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
