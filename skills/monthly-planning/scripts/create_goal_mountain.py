#!/usr/bin/env python3
"""
Create a Mountain (30d monthly goal) in an Airtable base.

Usage:
    python3 create_goal_mountain.py --base <personal|aitb|bb> \
        --title "Mountain title" \
        --description "Done when [outcome]" \
        --objective <objectiveRecordId> \
        [--priority <1-10>] \
        [--status <not_started|on_track|at_risk|on_hold>] \
        [--notes "Additional context"] \
        [--month "YYYY-MM"] \
        [--config path/to/config.yaml]

Output:
    JSON with id, title, base, airtable_url.

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

# ---------------------------------------------------------------------------
# Mountain table config per base
# ---------------------------------------------------------------------------

MOUNTAIN_CONFIG = {
    "personal": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "1yr Goal",
        "priority_field": "Priority",
        "notes_field": "Notes",
    },
    "aitb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "Objective",
        "priority_field": "Priority",
        "notes_field": "Notes",
    },
    "bb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "Objective (1y)",
        "priority_field": "Priority",
        "notes_field": "Notes",
    },
}

# Semantic status keys mapped to actual Airtable values per base.
# Each base has its own casing/naming conventions.
MOUNTAIN_STATUS_MAP = {
    "personal": {
        "not_started": "Not started",
        "on_track": "On track",
        "at_risk": "At risk",
        "on_hold": "On Hold",
        "complete": "Complete",
        "archived": "Archived",
    },
    "aitb": {
        "not_started": "Not Started",
        "in_progress": "In progress",
        "on_track": "In progress",  # AITB has no "On track", map to closest
        "completed": "Completed",
        "complete": "Completed",
        "archived": "Archived",
    },
    "bb": {
        "not_started": "Not started",
        "on_track": "On track",
        "at_risk": "At risk",
        "on_hold": "On Hold",
        "complete": "Complete",
        "archived": "Archived",
    },
}


def resolve_mountain_status(semantic: str, base_key: str = "bb") -> str:
    """Translate semantic status to the literal Airtable value for a base."""
    status_map = MOUNTAIN_STATUS_MAP.get(base_key, MOUNTAIN_STATUS_MAP["bb"])
    if semantic in status_map:
        return status_map[semantic]
    # Accept literal values directly if they match any value in this base
    if semantic in status_map.values():
        return semantic
    print(
        f"Error: Unknown mountain status '{semantic}' for base '{base_key}'. "
        f"Valid: {list(status_map.keys())} or "
        f"{list(status_map.values())}",
        file=sys.stderr,
    )
    sys.exit(1)


def _current_month() -> str:
    """Return current month in YYYY-MM format (America/Phoenix, UTC-7)."""
    from datetime import datetime, timedelta, timezone

    phoenix_tz = timezone(timedelta(hours=-7))
    return datetime.now(phoenix_tz).strftime("%Y-%m")


def create_mountain(
    base_key: str,
    title: str,
    config: dict,
    description: str | None = None,
    objective_id: str | None = None,
    priority: int | None = None,
    status: str | None = None,
    notes: str | None = None,
    month: str | None = None,
) -> dict:
    """Create a Mountain record in the specified base."""
    if base_key not in MOUNTAIN_CONFIG:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    mtn_cfg = MOUNTAIN_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]

    # Build fields
    fields = {mtn_cfg["name_field"]: title}

    if description:
        fields[mtn_cfg["description_field"]] = description
    else:
        print(
            "Warning: No description provided. Mountains should have a "
            "Definition of Done.",
            file=sys.stderr,
        )

    if objective_id:
        fields[mtn_cfg["objective_field"]] = [objective_id]
    else:
        print(
            "Error: --objective is required. Mountains must connect to an "
            "annual Objective. Orphaned mountains break the goal hierarchy.",
            file=sys.stderr,
        )
        sys.exit(1)

    if priority is not None:
        fields[mtn_cfg["priority_field"]] = priority

    if status:
        fields[mtn_cfg["status_field"]] = resolve_mountain_status(status, base_key)
    else:
        fields[mtn_cfg["status_field"]] = resolve_mountain_status("on_track", base_key)

    if notes:
        fields[mtn_cfg["notes_field"]] = notes

    # Month field — defaults to current month in YYYY-MM format
    fields["Month"] = month or _current_month()

    # Create via Airtable API
    encoded_table = urllib.parse.quote(mtn_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code} creating Mountain: {body}", file=sys.stderr)
        sys.exit(1)

    record_id = data["id"]
    airtable_url = f"https://airtable.com/{base_id}/{record_id}"

    return {
        "id": record_id,
        "title": title,
        "base": base_key,
        "airtable_url": airtable_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create a Mountain (30d goal) in Airtable"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to create the Mountain in",
    )
    parser.add_argument("--title", required=True, help="Mountain title")
    parser.add_argument("--description", required=True, help="Definition of Done")
    parser.add_argument("--objective", help="Annual Objective record ID to link to")
    parser.add_argument(
        "--priority", type=int, choices=range(1, 11), help="Priority 1-10"
    )
    parser.add_argument(
        "--status",
        default="on_track",
        help="Initial status (default: on_track)",
    )
    parser.add_argument("--notes", help="Additional context")
    parser.add_argument(
        "--month",
        help="Month in YYYY-MM format (default: current month)",
    )
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    result = create_mountain(
        base_key=args.base,
        title=args.title,
        config=config,
        description=args.description,
        objective_id=args.objective,
        priority=args.priority,
        status=args.status,
        notes=args.notes,
        month=args.month,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
