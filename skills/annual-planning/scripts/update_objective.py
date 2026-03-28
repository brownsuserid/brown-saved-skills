#!/usr/bin/env python3
"""
Update an annual Objective/Goal in an Airtable base.

Usage:
    python3 update_objective.py --base <personal|aitb|bb> \
        --id <recordId> \
        [--status <not_started|on_track|done|off_track|archived>] \
        [--name "Updated name"] \
        [--description "Updated measurements"] \
        [--config path/to/config.yaml]

Output:
    JSON with id, name, base, updated_fields.

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

from create_objective import (  # noqa: E402
    OBJECTIVE_CONFIG,
    resolve_objective_status,
)


def update_objective(
    base_key: str,
    record_id: str,
    config: dict,
    status: str | None = None,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    """Update an Objective/Goal record in the specified base."""
    if base_key not in OBJECTIVE_CONFIG:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    obj_cfg = OBJECTIVE_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]

    fields = {}

    if status:
        fields[obj_cfg["status_field"]] = resolve_objective_status(status, base_key)

    if name:
        fields[obj_cfg["name_field"]] = name

    if description:
        fields[obj_cfg["description_field"]] = description

    if not fields:
        print(
            "Error: No fields to update. Provide --status, --name, or --description.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Update via Airtable API
    encoded_table = urllib.parse.quote(obj_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="PATCH"
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())

    return {
        "id": record_id,
        "name": data.get("fields", {}).get(obj_cfg["name_field"], ""),
        "base": base_key,
        "updated_fields": list(fields.keys()),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update an annual Objective/Goal in Airtable"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base the objective is in",
    )
    parser.add_argument("--id", required=True, help="Record ID to update")
    parser.add_argument("--status", help="New status")
    parser.add_argument("--name", help="Updated name")
    parser.add_argument("--description", help="Updated measurements/description")
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    result = update_objective(
        base_key=args.base,
        record_id=args.id,
        config=config,
        status=args.status,
        name=args.name,
        description=args.description,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
