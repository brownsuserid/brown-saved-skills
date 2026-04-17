#!/usr/bin/env python3
"""
Create a speaking opportunity deal in BB Airtable.

Creates a deal record with linked contact and organization,
sets campaign to 'Speaking Opps', and creates a follow-up task.

Usage:
    python3 create_deal.py --event-name "AI Meetup Denver" \
        --org-name "Denver Tech Group" \
        --contact-name "Jane Smith" \
        --contact-email "jane@example.com"

    python3 create_deal.py --event-name "AI Meetup Denver" \
        --org-name "Denver Tech Group" \
        --config /path/to/config.yaml

Output:
    JSON with created deal, contact, and org record IDs.
"""

import argparse
import json
import os
import subprocess  # nosec B404 - used to call search-airtable.sh
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"))

from airtable_config import (
    api_headers,
    get_base,
    get_people,
    load_config,
    resolve_assignee,
    resolve_config_path,
)

# Deal field IDs
DEAL_FIELDS = {
    "name": "fldY0uE3xwZLzK0J8",
    "status": "fld84ZYnfhVUYbA7f",
    "organization": "fldNbTbG8PjugeCrd",
    "deal_contacts": "fldBAcqAE0N3CaqPl",
    "tasks": "fldxSrK1KDt3UfcGn",
    "assignee": "fldw7L6yCDpT2QBiV",
    "type": "fld4mUh4oUA8VQ3jP",
    "campaign": "fldFyWKc7rUdtk4sI",
}

SEARCH_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "looking-up-contacts", "search-airtable.sh"
)


def _airtable_create(base_id: str, table_id: str, fields: dict[str, Any]) -> dict:
    """Create a record in Airtable."""
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="POST"
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def search_existing_contact(name: str) -> str | None:
    """Search BB contacts for an existing record. Returns record ID or None."""
    try:
        result = subprocess.run(  # nosec B603 B607
            ["bash", SEARCH_SCRIPT, name, "bb"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            contacts = data.get("contacts", [])
            if contacts:
                return contacts[0].get("id")
    except Exception as e:
        print(f"Warning: Contact search failed: {e}", file=sys.stderr)
    return None


def search_existing_org(name: str) -> str | None:
    """Search BB orgs for an existing record. Returns record ID or None."""
    try:
        result = subprocess.run(  # nosec B603 B607
            ["bash", SEARCH_SCRIPT, name, "bb"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            orgs = data.get("organizations", [])
            if orgs:
                return orgs[0].get("id")
    except Exception as e:
        print(f"Warning: Org search failed: {e}", file=sys.stderr)
    return None


def create_contact(
    base_id: str, contacts_table_id: str, name: str, email: str | None = None
) -> str:
    """Create a new contact in BB. Returns record ID."""
    parts = name.strip().rsplit(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    fields: dict[str, Any] = {
        "fldd7Immee8MrNkQC": first_name,  # First Name
        "fldjnk4gLIeLg6P8T": last_name,  # Last Name
    }
    if email:
        fields["fldEadLCLfw8yLkiy"] = email  # Email (Work)
    record = _airtable_create(base_id, contacts_table_id, fields)
    print(f"Created contact: {name} ({record['id']})", file=sys.stderr)
    return record["id"]


def create_org(base_id: str, orgs_table_id: str, name: str) -> str:
    """Create a new organization in BB. Returns record ID."""
    fields = {"Name": name}
    record = _airtable_create(base_id, orgs_table_id, fields)
    print(f"Created org: {name} ({record['id']})", file=sys.stderr)
    return record["id"]


def create_deal(
    base_id: str,
    deals_table_id: str,
    event_name: str,
    org_id: str | None,
    contact_id: str | None,
    aaron_bb_id: str,
    assignee_id: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    """Create a speaking opportunity deal in BB."""
    fields: dict[str, Any] = {
        DEAL_FIELDS["name"]: f"{event_name} - Speaking",
        DEAL_FIELDS["status"]: ["recPA9aoE2dZQuFQY"],  # 01-Identified & Enriched
        DEAL_FIELDS["type"]: "New Business",
        DEAL_FIELDS["assignee"]: [assignee_id or aaron_bb_id],
    }

    if org_id:
        fields[DEAL_FIELDS["organization"]] = [org_id]
    if campaign_id:
        fields[DEAL_FIELDS["campaign"]] = [campaign_id]

    record = _airtable_create(base_id, deals_table_id, fields)
    print(f"Created deal: {event_name} - Speaking ({record['id']})", file=sys.stderr)
    return record


DEAL_CONTACTS_TABLE_ID = "tbltrHekUeRLmpzGM"


def link_deal_contact(base_id: str, deal_id: str, contact_id: str) -> dict:
    """Create a junction record linking a deal to a contact."""
    fields: dict[str, Any] = {
        "fld3WIE7KjDp0anjn": [deal_id],  # Deal
        "fldYNJKXDYAu56S44": [contact_id],  # Contact
    }
    record = _airtable_create(base_id, DEAL_CONTACTS_TABLE_ID, fields)
    print(f"Linked deal to contact ({record['id']})", file=sys.stderr)
    return record


def create_followup_task(
    base_id: str, tasks_table_id: str, deal_id: str, event_name: str, aaron_bb_id: str
) -> dict:
    """Create a follow-up task linked to the deal."""
    fields: dict[str, Any] = {
        "Task": f"Follow up on {event_name} speaking outreach",
        "Status": "Not Started",
        "Assignee": [aaron_bb_id],
        "Deals": [deal_id],
    }

    record = _airtable_create(base_id, tasks_table_id, fields)
    print(f"Created follow-up task ({record['id']})", file=sys.stderr)
    return record


def main():
    parser = argparse.ArgumentParser(
        description="Create a speaking opportunity deal in BB Airtable"
    )
    parser.add_argument("--event-name", required=True, help="Event/group name")
    parser.add_argument("--org-name", required=True, help="Organization name")
    parser.add_argument("--contact-name", help="Organizer contact name")
    parser.add_argument("--contact-email", help="Organizer email")
    parser.add_argument(
        "--assignee",
        default="aaron",
        help="Assignee name (aaron, josh, pablo, juan) or raw record ID",
    )
    parser.add_argument(
        "--campaign",
        help="Campaign record ID to link the deal to",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: ../airtable-config/configs/all.yaml)",
    )
    args = parser.parse_args()

    # Load config
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)

    bb = get_base(config, "bb")
    people = get_people(config)
    bb_base_id = bb["base_id"]
    contacts_table_id = bb["contacts_table_id"]
    orgs_table_id = bb["orgs_table"]
    tasks_table_id = bb["tasks_table_id"]
    deals_table_id = bb["deals_table_id"]
    aaron_bb_id = people["aaron"]["bb"]

    # Resolve assignee name to record ID
    assignee_id = resolve_assignee(config, args.assignee, "bb")

    # Search or create org
    org_id = search_existing_org(args.org_name)
    if not org_id and not args.dry_run:
        org_id = create_org(bb_base_id, orgs_table_id, args.org_name)
    elif org_id:
        print(f"Found existing org: {args.org_name} ({org_id})", file=sys.stderr)

    # Search or create contact
    contact_id = None
    if args.contact_name:
        contact_id = search_existing_contact(args.contact_name)
        if not contact_id and not args.dry_run:
            contact_id = create_contact(
                bb_base_id, contacts_table_id, args.contact_name, args.contact_email
            )
        elif contact_id:
            print(
                f"Found existing contact: {args.contact_name} ({contact_id})",
                file=sys.stderr,
            )

    if args.dry_run:
        result = {
            "dry_run": True,
            "would_create": {
                "deal": f"{args.event_name} - Speaking",
                "org": args.org_name if not org_id else f"(existing: {org_id})",
                "contact": (
                    args.contact_name if not contact_id else f"(existing: {contact_id})"
                ),
            },
        }
    else:
        deal = create_deal(
            bb_base_id,
            deals_table_id,
            args.event_name,
            org_id,
            contact_id,
            aaron_bb_id,
            assignee_id,
            args.campaign,
        )
        deal_contact_id = None
        if contact_id:
            junction = link_deal_contact(bb_base_id, deal["id"], contact_id)
            deal_contact_id = junction["id"]
        task = create_followup_task(
            bb_base_id, tasks_table_id, deal["id"], args.event_name, aaron_bb_id
        )
        result = {
            "deal_id": deal["id"],
            "deal_url": (
                f"https://airtable.com/{bb_base_id}/{deals_table_id}/{deal['id']}"
            ),
            "org_id": org_id,
            "contact_id": contact_id,
            "deal_contact_id": deal_contact_id,
            "task_id": task["id"],
        }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
