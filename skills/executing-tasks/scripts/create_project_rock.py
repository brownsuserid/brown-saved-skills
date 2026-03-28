#!/usr/bin/env python3
"""
Create a new project (Personal/AITB) or Rock (BB) in Airtable.

Usage:
    python3 create_project_rock.py --base [personal|aitb|bb] \
        --name "Project name" \
        --description "Definition of Done" \
        [--driver pablo|aaron|juan|<recordId>] \
        [--goal <goalRecordId>] \
        [--status "Not Started"] \
        [--notes "Additional context"] \
        [--for-this-week] \
        [--config path/to/config.yaml]

Quality standard: see managing-projects/references/creating-projects.md
Warnings are printed to stderr when key fields are missing.

Output:
    JSON with the created record ID, name, base, and Airtable URL.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Import shared Airtable config
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)
from airtable_config import (  # noqa: E402
    api_headers,
    get_base,
    load_config,
    resolve_assignee,
    resolve_config_path,
    resolve_status,
)


def create_project(
    config: dict,
    base_key: str,
    name: str,
    description: str | None = None,
    driver: str | None = None,
    goal_id: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    for_this_week: bool = False,
) -> dict:
    """POST a new project/rock record to the specified Airtable base."""
    base_cfg = get_base(config, base_key)

    fields = {
        base_cfg["project_name_field"]: name,
    }

    # Default status
    if status:
        fields[base_cfg["project_status_field"]] = resolve_status(
            config, status, base_key
        )
    else:
        fields[base_cfg["project_status_field"]] = base_cfg["status_values"][
            "not_started"
        ]

    if description:
        fields[base_cfg["project_description_field"]] = description

    # Goal linkage
    if goal_id:
        if base_key == "bb" and base_cfg["project_mountain_field"]:
            # BB Rocks link to Mountains
            fields[base_cfg["project_mountain_field"]] = [goal_id]
        elif base_cfg["project_goals_field"]:
            # Personal links to 1yr Goals
            fields[base_cfg["project_goals_field"]] = [goal_id]
        else:
            # AITB has no goal field -- append to notes
            goal_note = f"\nGoal linkage: {goal_id}"
            notes = (notes or "") + goal_note

    # Driver
    if driver and base_cfg["project_driver_field"]:
        fields[base_cfg["project_driver_field"]] = [
            resolve_assignee(config, driver, base_key)
        ]
    elif driver and not base_cfg["project_driver_field"]:
        print(
            f"Warning: {base_key} base has no Driver field on projects. "
            f"Driver '{driver}' ignored.",
            file=sys.stderr,
        )

    if notes:
        # Use notes_field from task config -- projects share the same Notes field name
        fields["Notes"] = notes.strip()

    if for_this_week:
        for_this_week_field = base_cfg.get("project_for_this_week_field")
        if for_this_week_field:
            fields[for_this_week_field] = True
        else:
            print(
                f"Warning: {base_key} base has no 'For This Week' field configured. Flag ignored.",
                file=sys.stderr,
            )

    table = base_cfg["project_table"]
    url = (
        f"https://api.airtable.com/v0/{base_cfg['base_id']}/{urllib.parse.quote(table)}"
    )
    payload = json.dumps({"fields": fields}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"Error creating project: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Create a new Airtable project or Rock"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to create the project in",
    )
    parser.add_argument("--name", required=True, help="Project/Rock name")
    parser.add_argument("--description", required=True, help="Definition of Done")
    parser.add_argument(
        "--driver",
        help="Driver: pablo, aaron, juan, or record ID (required for AITB/BB)",
    )
    parser.add_argument(
        "--goal",
        help="Goal record ID to link (1yr Goals for Personal, Mountain for BB)",
    )
    parser.add_argument("--status", help="Initial status (default: Not Started)")
    parser.add_argument("--notes", help="Additional context")
    parser.add_argument(
        "--for-this-week",
        action="store_true",
        help="Set 'For This Week' = true on the created project/rock",
    )
    parser.add_argument("--config", help="Path to Airtable config YAML")

    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)

    # Quality warnings (stderr only, not errors)
    if not args.description:
        print(
            "Warning: No --description (Definition of Done). "
            "See creating-projects.md quality standard.",
            file=sys.stderr,
        )
    if not args.goal:
        if args.base in ("personal", "bb"):
            label = "Mountain" if args.base == "bb" else "1yr Goal"
            print(
                f"Error: --goal is required. Projects/Rocks without a {label} "
                "are orphaned from the goal hierarchy. "
                "See creating-projects.md quality standard.",
                file=sys.stderr,
            )
            sys.exit(1)
        elif args.base == "aitb":
            print(
                "Warning: No --goal. AITB has no goal field on Projects -- "
                "document which objective this serves in --notes.",
                file=sys.stderr,
            )
    if not args.driver and args.base in ("aitb", "bb"):
        print(
            f"Warning: No --driver for {args.base} base. "
            "See creating-projects.md quality standard.",
            file=sys.stderr,
        )

    result = create_project(
        config=config,
        base_key=args.base,
        name=args.name,
        description=args.description,
        driver=args.driver,
        goal_id=args.goal,
        status=args.status,
        notes=args.notes,
        for_this_week=args.for_this_week,
    )

    base_cfg = get_base(config, args.base)
    # Resolve the project table ID for the URL
    # Use tasks_table_id as a fallback base for URL -- project table IDs aren't in config
    # Build URL with base_id and project table name
    output = {
        "id": result["id"],
        "name": result.get("fields", {}).get(base_cfg["project_name_field"], ""),
        "base": args.base,
        "airtable_url": f"https://airtable.com/{base_cfg['base_id']}/{urllib.parse.quote(base_cfg['project_table'])}/{result['id']}",
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
