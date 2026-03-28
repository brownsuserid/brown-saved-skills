#!/usr/bin/env python3
"""
Query goals from an Airtable base.

Usage:
    python3 query_goals.py --base [personal|aitb|bb] --type [annual|monthly|weekly] [--config path/to/config.yaml]

Output:
    JSON array of goals with name, status, linked records, and IDs.

Table mapping:
    Personal: annual = "1yr Goals" (no monthly/weekly tables yet)
    AITB:     annual = "Objectives (1y)", monthly = "Mountains (30d)", weekly = "Rocks (7d)"
    BB:       annual = "Objectives (1y)", monthly = "Mountains (30d)", weekly = "Rocks (7d)"
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402


def fetch_goals(base_key, goal_type, config, year=None):
    """Fetch goals from the correct Airtable table for this base/type."""
    goal_tables = config["bases"].get(base_key, {}).get("goals", {})
    if not goal_tables:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    goal_cfg = goal_tables.get(goal_type)
    if not goal_cfg:
        print(
            f"Error: '{base_key}' base does not have a '{goal_type}' goals table.",
            file=sys.stderr,
        )
        sys.exit(1)

    encoded_table = urllib.parse.quote(goal_cfg["table"])
    url = f"https://api.airtable.com/v0/{goal_cfg['base_id']}/{encoded_table}"

    params = {}
    if goal_cfg["sort_field"]:
        params["sort[0][field]"] = goal_cfg["sort_field"]
        params["sort[0][direction]"] = goal_cfg["sort_direction"]

    formulas = []
    if year and goal_cfg.get("year_field"):
        formulas.append(f"{{{goal_cfg['year_field']}}}='{year}'")

    if formulas:
        params["filterByFormula"] = (
            f"AND({','.join(formulas)})" if len(formulas) > 1 else formulas[0]
        )

    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=airtable_config.api_headers())

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            goals = []
            for record in data.get("records", []):
                fields = record.get("fields", {})
                goal = {
                    "id": record.get("id"),
                    "name": fields.get(goal_cfg["name_field"]),
                    "status": fields.get("Status"),
                    "description": fields.get(goal_cfg["description_field"], ""),
                    "priority": fields.get("Priority"),
                }
                if goal_cfg["linked_projects"]:
                    goal["linked_projects"] = fields.get(
                        goal_cfg["linked_projects"], []
                    )
                if goal_cfg["linked_down"]:
                    goal["linked_down"] = fields.get(goal_cfg["linked_down"], [])
                if goal_cfg["linked_up"]:
                    goal["linked_up"] = fields.get(goal_cfg["linked_up"], [])

                goals.append(goal)

            return goals

    except urllib.error.HTTPError as e:
        print(f"Error fetching goals: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Query goals from Airtable")
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to query",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["annual", "monthly", "weekly"],
        help="Type of goals to fetch (annual/monthly/weekly)",
    )
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    goals = fetch_goals(args.base, args.type, config)
    print(json.dumps(goals, indent=2))


if __name__ == "__main__":
    main()
