#!/usr/bin/env python3
"""
Update a Mountain (30d monthly goal) in an Airtable base.

Usage:
    python3 update_mountain.py --base <personal|aitb|bb> --id <recordId> \
        [--status <not_started|on_track|at_risk|on_hold|complete|archived>] \
        [--priority <1-10>] \
        [--title "New title"] \
        [--description "Updated definition of done"] \
        [--notes "Additional context"] \
        [--config path/to/config.yaml]

Output:
    JSON with id, updated fields, base, airtable_url.

Requires AIRTABLE_TOKEN environment variable.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402

# Import mountain config from create_goal_mountain
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_goal_mountain import MOUNTAIN_CONFIG  # noqa: E402
from create_goal_mountain import resolve_mountain_status  # noqa: E402


def update_mountain(
    base_key: str,
    record_id: str,
    config: dict,
    status: str | None = None,
    priority: int | None = None,
    title: str | None = None,
    description: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update a Mountain record in the specified base."""
    if base_key not in MOUNTAIN_CONFIG:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    mtn_cfg = MOUNTAIN_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]

    # Build fields to update
    fields = {}
    updated_fields = []

    if status:
        fields[mtn_cfg["status_field"]] = resolve_mountain_status(status, base_key)
        updated_fields.append("status")

    if priority is not None:
        fields[mtn_cfg["priority_field"]] = priority
        updated_fields.append("priority")

    if title:
        fields[mtn_cfg["name_field"]] = title
        updated_fields.append("title")

    if description:
        fields[mtn_cfg["description_field"]] = description
        updated_fields.append("description")

    if notes:
        fields[mtn_cfg["notes_field"]] = notes
        updated_fields.append("notes")

    if not fields:
        print("Error: No fields to update. Provide at least one flag.", file=sys.stderr)
        sys.exit(1)

    # Update via Airtable API
    encoded_table = urllib.parse.quote(mtn_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="PATCH"
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code} updating Mountain: {body}", file=sys.stderr)
        sys.exit(1)

    airtable_url = f"https://airtable.com/{base_id}/{record_id}"

    return {
        "id": data["id"],
        "base": base_key,
        "updated_fields": updated_fields,
        "airtable_url": airtable_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update a Mountain (30d goal) in Airtable"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base the Mountain is in",
    )
    parser.add_argument("--id", required=True, help="Mountain record ID")
    parser.add_argument(
        "--status",
        help="New status (not_started, on_track, at_risk, on_hold, complete, archived)",
    )
    parser.add_argument(
        "--priority", type=int, choices=range(1, 11), help="Priority 1-10"
    )
    parser.add_argument("--title", help="New title")
    parser.add_argument("--description", help="New Definition of Done")
    parser.add_argument("--notes", help="Additional context")
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    result = update_mountain(
        base_key=args.base,
        record_id=args.id,
        config=config,
        status=args.status,
        priority=args.priority,
        title=args.title,
        description=args.description,
        notes=args.notes,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
