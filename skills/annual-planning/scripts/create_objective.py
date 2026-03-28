#!/usr/bin/env python3
"""
Create an annual Objective/Goal in an Airtable base.

Usage:
    python3 create_objective.py --base <personal|aitb|bb> \
        --name "Specific annual goal" \
        --description "Measurements: [how we know it's done]" \
        [--category <mental|physical|community|work|financial|relationships|personal>] \
        [--year 2027] \
        [--priority <1-5>] \
        [--status <not_started|on_track|done|off_track>] \
        [--organization <bb|sbai>] \
        [--notes "Additional context"] \
        [--config path/to/config.yaml]

Output:
    JSON with id, name, base, airtable_url.

Per-base differences:
    Personal: Name + Measurements + Status + Area of Focus + Year + Priority (1-5)
    AITB:     Name + Notes + Status
    BB:       Objective + Description + Status + Years + Organization + Notes

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
# Objective table config per base
# ---------------------------------------------------------------------------

OBJECTIVE_CONFIG = {
    "personal": {
        "table": "1yr Goals",
        "table_id": "tbll1AUS4uBF9Cgnh",
        "name_field": "Name",
        "description_field": "Measurements",
        "status_field": "Status",
        "category_field": "Area of Focus",
        "year_field": "Year",
        "priority_field": "Priority",
        "organization_field": None,
        "notes_field": None,
    },
    "aitb": {
        "table": "Objectives (1y)",
        "table_id": "tblZIpLbkqFjAniNR",
        "name_field": "Name",
        "description_field": "Notes",
        "status_field": "Status",
        "category_field": None,
        "year_field": None,
        "priority_field": None,
        "organization_field": None,
        "notes_field": None,
    },
    "bb": {
        "table": "Objectives (1y)",
        "table_id": "tblAYaj2ZYhZtgp2a",
        "name_field": "Objective",
        "description_field": "Description",
        "status_field": "Status",
        "category_field": None,
        "year_field": "Years",
        "priority_field": None,
        "organization_field": "Organization",
        "notes_field": "Notes",
    },
}

# Per-base status value mapping
OBJECTIVE_STATUS_VALUES = {
    "personal": {
        "not_started": "Not Started",
        "on_track": "On Track",
        "done": "Done",
        "off_track": "Off Track",
    },
    "aitb": {
        "not_started": "Todo",
        "on_track": "In progress",
        "done": "Done",
    },
    "bb": {
        "not_started": "Not Started",
        "on_track": "On Track",
        "done": "Completed",
        "off_track": "At Risk",
        "archived": "Archived",
    },
}

# Personal Area of Focus valid values
AREA_OF_FOCUS_VALUES = {
    "mental": "Mental",
    "physical": "Physical",
    "community": "Community",
    "work": "Work/Intuit",
    "financial": "Financial",
    "relationships": "Key Relationships",
    "personal": "Personal",
}


def resolve_objective_status(semantic: str, base_key: str) -> str:
    """Translate semantic status to base-specific literal value."""
    mapping = OBJECTIVE_STATUS_VALUES.get(base_key, {})
    if semantic in mapping:
        return mapping[semantic]
    # Accept literal values directly
    all_values = list(mapping.values())
    if semantic in all_values:
        return semantic
    print(
        f"Error: Unknown objective status '{semantic}' for base '{base_key}'. "
        f"Valid: {list(mapping.keys())} or {all_values}",
        file=sys.stderr,
    )
    sys.exit(1)


def resolve_category(category: str) -> str:
    """Resolve category shorthand to Area of Focus value."""
    lower = category.lower()
    if lower in AREA_OF_FOCUS_VALUES:
        return AREA_OF_FOCUS_VALUES[lower]
    # Accept literal values directly
    if category in AREA_OF_FOCUS_VALUES.values():
        return category
    print(
        f"Error: Unknown category '{category}'. "
        f"Valid: {list(AREA_OF_FOCUS_VALUES.keys())} or "
        f"{list(AREA_OF_FOCUS_VALUES.values())}",
        file=sys.stderr,
    )
    sys.exit(1)


def create_objective(
    base_key: str,
    name: str,
    config: dict,
    description: str | None = None,
    category: str | None = None,
    year: str | None = None,
    priority: int | None = None,
    status: str | None = None,
    organization: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create an annual Objective/Goal record in the specified base."""
    if base_key not in OBJECTIVE_CONFIG:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    obj_cfg = OBJECTIVE_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]

    # Build fields
    fields = {obj_cfg["name_field"]: name}

    # Description/Measurements
    if description:
        fields[obj_cfg["description_field"]] = description
    else:
        print(
            "Warning: No description provided. Objectives should have "
            "measurable success criteria.",
            file=sys.stderr,
        )

    # Status
    if status:
        fields[obj_cfg["status_field"]] = resolve_objective_status(status, base_key)
    else:
        # Default per base
        defaults = {"personal": "Not Started", "aitb": "Todo", "bb": "Not Started"}
        fields[obj_cfg["status_field"]] = defaults[base_key]

    # Category (Personal only)
    if category and obj_cfg["category_field"]:
        fields[obj_cfg["category_field"]] = resolve_category(category)
    elif category and not obj_cfg["category_field"]:
        print(
            f"Warning: '{base_key}' base has no category field. "
            f"Category '{category}' ignored.",
            file=sys.stderr,
        )

    # Year
    if year and obj_cfg["year_field"]:
        fields[obj_cfg["year_field"]] = str(year)
    elif year and not obj_cfg["year_field"]:
        print(
            f"Warning: '{base_key}' base has no year field. Year '{year}' ignored.",
            file=sys.stderr,
        )

    # Priority (Personal only, 1-5 rating)
    if priority is not None and obj_cfg["priority_field"]:
        fields[obj_cfg["priority_field"]] = priority
    elif priority is not None and not obj_cfg["priority_field"]:
        print(
            f"Warning: '{base_key}' base has no priority field. "
            f"Priority {priority} ignored.",
            file=sys.stderr,
        )

    # Organization (BB only)
    if organization and obj_cfg["organization_field"]:
        fields[obj_cfg["organization_field"]] = organization.upper()
    elif organization and not obj_cfg["organization_field"]:
        print(
            f"Warning: '{base_key}' base has no organization field. "
            f"Organization '{organization}' ignored.",
            file=sys.stderr,
        )

    # Notes (BB only -- AITB uses Notes as description_field)
    if notes and obj_cfg["notes_field"]:
        fields[obj_cfg["notes_field"]] = notes
    elif notes and not obj_cfg["notes_field"]:
        print(
            f"Warning: '{base_key}' base has no separate notes field.",
            file=sys.stderr,
        )

    # Create via Airtable API
    encoded_table = urllib.parse.quote(obj_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="POST"
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())

    record_id = data["id"]
    airtable_url = f"https://airtable.com/{base_id}/{obj_cfg['table_id']}/{record_id}"

    return {
        "id": record_id,
        "name": name,
        "base": base_key,
        "airtable_url": airtable_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create an annual Objective/Goal in Airtable"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to create the objective in",
    )
    parser.add_argument("--name", required=True, help="Objective/Goal name")
    parser.add_argument(
        "--description",
        help="Measurements / success criteria",
    )
    parser.add_argument(
        "--category",
        choices=list(AREA_OF_FOCUS_VALUES.keys()),
        help="Area of Focus (Personal base only)",
    )
    parser.add_argument("--year", help="Year (e.g., 2027)")
    parser.add_argument(
        "--priority",
        type=int,
        choices=range(1, 6),
        help="Priority 1-5 (Personal base only)",
    )
    parser.add_argument(
        "--status",
        default="not_started",
        help="Initial status (default: not_started)",
    )
    parser.add_argument(
        "--organization",
        choices=["bb", "sbai", "BB", "SBAI"],
        help="Organization (BB base only)",
    )
    parser.add_argument("--notes", help="Additional context (BB base only)")
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    result = create_objective(
        base_key=args.base,
        name=args.name,
        config=config,
        description=args.description,
        category=args.category,
        year=args.year,
        priority=args.priority,
        status=args.status,
        organization=args.organization,
        notes=args.notes,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
