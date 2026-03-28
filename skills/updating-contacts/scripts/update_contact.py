#!/usr/bin/env python3
"""
Update fields on an Airtable contact record.

Usage:
    python3 update_contact.py --base bb --id recXXX \
        [--name "John Smith"] \
        [--first-name "John"] \
        [--last-name "Smith"] \
        [--email "john@example.com"] \
        [--phone "+1-555-0100"] \
        [--title "VP Engineering"] \
        [--organization recOrgXXX] \
        [--config /path/to/config.yaml]

Only specified fields are updated (PATCH semantics).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"
    ),
)
from airtable_config import (  # noqa: E402
    api_headers,
    airtable_record_url,
    load_config,
)

# Module-level config — loaded lazily or via main()
_config: dict | None = None


def _ensure_config(config_path: str | None = None) -> dict:
    """Load config if not already loaded. Returns the full config."""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def update_contact(base_key: str, record_id: str, updates: dict) -> dict:
    """PATCH an Airtable contact record with the given field updates."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]

    fields = {}

    if "name" in updates:
        fields[config["contacts_name_field"]] = updates["name"]

    if "first_name" in updates:
        field_key = config.get("contacts_first_name_field")
        if not field_key:
            print(
                f"Error: Base '{base_key}' does not have a contacts_first_name_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[field_key] = updates["first_name"]

    if "last_name" in updates:
        field_key = config.get("contacts_last_name_field")
        if not field_key:
            print(
                f"Error: Base '{base_key}' does not have a contacts_last_name_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[field_key] = updates["last_name"]

    if "email" in updates:
        fields[config["contacts_email_field"]] = updates["email"]

    if "phone" in updates:
        fields[config["contacts_phone_field"]] = updates["phone"]

    if "title" in updates:
        fields[config["contacts_title_field"]] = updates["title"]

    if "organization" in updates:
        fields[config["contacts_org_field"]] = [updates["organization"]]

    if not fields:
        print(
            "Error: No fields to update. Specify at least one field flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"https://api.airtable.com/v0/{config['base_id']}/{config['contacts_table_id']}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="PATCH"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"Error updating contact: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def check_data_quality(result: dict, base_key: str) -> None:
    """Print warnings for missing data quality fields."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]
    fields = result.get("fields", {})
    org_value = fields.get(config["contacts_org_field"])
    if not org_value:
        print(
            "Warning: Contact has no Organization linked. Use --organization recXXX to fix.",
            file=sys.stderr,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Update an Airtable contact record (PATCH semantics).",
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["bb", "aitb"],
        help="Which base the contact is in",
    )
    parser.add_argument("--id", required=True, help="The Airtable record ID (recXXX)")
    parser.add_argument("--name", help="Full name / display name")
    parser.add_argument("--first-name", help="First name (BB only)")
    parser.add_argument("--last-name", help="Last name (BB only)")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--phone", help="Phone number")
    parser.add_argument("--title", help="Job title")
    parser.add_argument("--organization", help="Organization record ID (recXXX)")
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )

    args = parser.parse_args()

    # Load config
    _ensure_config(args.config)

    updates = {}
    if args.name:
        updates["name"] = args.name
    if args.first_name:
        updates["first_name"] = args.first_name
    if args.last_name:
        updates["last_name"] = args.last_name
    if args.email:
        updates["email"] = args.email
    if args.phone:
        updates["phone"] = args.phone
    if args.title:
        updates["title"] = args.title
    if args.organization:
        updates["organization"] = args.organization

    result = update_contact(args.base, args.id, updates)

    check_data_quality(result, args.base)

    cfg = _ensure_config()
    config = cfg["bases"][args.base]
    fields = result.get("fields", {})
    org_value = fields.get(config["contacts_org_field"], "")
    if isinstance(org_value, list):
        org_value = org_value[0] if org_value else ""

    output = {
        "id": result["id"],
        "name": fields.get(config["contacts_name_field"], ""),
        "organization": org_value,
        "base": args.base,
        "airtable_url": airtable_record_url(
            config["base_id"], config["contacts_table_id"], result["id"]
        ),
        "updated_fields": list(updates.keys()),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
