#!/usr/bin/env python3
"""
Gather monthly planning data from all Airtable bases.

Fetches annual goals, monthly goals (Mountains), active projects,
and task completion stats to produce a consolidated briefing.

Usage:
    python3 gather_monthly_data.py [--config path/to/config.yaml]

Output:
    JSON object with per-base data for annual goals, mountains,
    active projects, and task stats.

Requires AIRTABLE_TOKEN environment variable.
"""

import argparse
from datetime import datetime
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
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "routing-airtable-tasks"
    ),
)

import airtable_config  # noqa: E402
from query_goals import fetch_goals  # noqa: E402


# ---------------------------------------------------------------------------
# Mountain config per base (fields specific to Mountains tables)
# ---------------------------------------------------------------------------

MOUNTAIN_CONFIG = {
    "personal": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "1yr Goal",
        "priority_field": "Priority",
    },
    "aitb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "Objective",
        "priority_field": "Priority",
    },
    "bb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "description_field": "Definition of Done",
        "status_field": "Status",
        "objective_field": "Objective (1y)",
        "priority_field": "Priority",
    },
}


def fetch_mountains(
    base_key: str, config: dict, month: str | None = None
) -> list[dict]:
    """Fetch all Mountains for a specific month from a base."""
    mtn_cfg = MOUNTAIN_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]
    encoded_table = urllib.parse.quote(mtn_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"

    params = {
        "sort[0][field]": mtn_cfg["priority_field"],
        "sort[0][direction]": "desc",
    }

    if month:
        params["filterByFormula"] = f"{{Month}}='{month}'"
    else:
        params["filterByFormula"] = "AND({Status}!='Archived', {Status}!='Complete')"

    url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=airtable_config.api_headers())
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            mountains = []
            for record in data.get("records", []):
                fields = record.get("fields", {})
                mountains.append(
                    {
                        "id": record["id"],
                        "title": fields.get(mtn_cfg["name_field"], ""),
                        "description": fields.get(mtn_cfg["description_field"], ""),
                        "status": fields.get(mtn_cfg["status_field"], ""),
                        "objective_ids": fields.get(mtn_cfg["objective_field"], []),
                        "priority": fields.get(mtn_cfg["priority_field"]),
                    }
                )
            return mountains
    except urllib.error.HTTPError as e:
        print(
            f"Warning: Failed to fetch mountains for {base_key}: {e.read().decode()}",
            file=sys.stderr,
        )
        return []


def fetch_active_projects(base_key: str, config: dict) -> list[dict]:
    """Fetch active (non-done) projects from a base."""
    base_cfg = airtable_config.get_base(config, base_key)
    encoded_table = urllib.parse.quote(base_cfg["project_table"])
    url = f"https://api.airtable.com/v0/{base_cfg['base_id']}/{encoded_table}"

    # Exclude done projects -- status values differ per base
    done_formulas = [
        f"{{{base_cfg['project_status_field']}}}!='{s}'"
        for s in ["Complete", "Done", "Archived", "Completed"]
    ]
    formula = f"AND({', '.join(done_formulas)})"
    params = {"filterByFormula": formula}
    url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=airtable_config.api_headers())
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            projects = []
            for record in data.get("records", []):
                fields = record.get("fields", {})
                projects.append(
                    {
                        "id": record["id"],
                        "name": fields.get(base_cfg["project_name_field"], ""),
                        "status": fields.get(base_cfg["project_status_field"], ""),
                    }
                )
            return projects
    except urllib.error.HTTPError as e:
        print(
            f"Warning: Failed to fetch projects for {base_key}: {e.read().decode()}",
            file=sys.stderr,
        )
        return []


def fetch_task_stats(base_key: str, config: dict) -> dict:
    """Fetch task counts: total active, completed, blocked."""
    base_cfg = airtable_config.get_base(config, base_key)
    base_id = base_cfg["base_id"]
    table_id = base_cfg["tasks_table_id"]
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"

    stats = {"active": 0, "completed": 0, "blocked": 0}

    for status_key, count_key in [
        (
            "NOT(OR({Status}='Completed',{Status}='Cancelled',{Status}='Archived'))",
            "active",
        ),
        ("{Status}='Completed'", "completed"),
        ("{Status}='Blocked'", "blocked"),
    ]:
        params = {
            "filterByFormula": status_key,
            "pageSize": 1,
            "returnFieldsByFieldId": "true",
        }
        req_url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(req_url, headers=airtable_config.api_headers())
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                records = data.get("records", [])
                if records:
                    # Re-fetch without pageSize limit to count
                    count_params = {
                        "filterByFormula": status_key,
                        "fields[]": base_cfg["task_field"],
                    }
                    count_url = url + "?" + urllib.parse.urlencode(count_params)
                    count_req = urllib.request.Request(
                        count_url, headers=airtable_config.api_headers()
                    )

                    all_records = []
                    with urllib.request.urlopen(count_req) as count_response:
                        page_data = json.loads(count_response.read().decode())
                        all_records.extend(page_data.get("records", []))
                        offset = page_data.get("offset")

                    while offset:
                        next_params = {**count_params, "offset": offset}
                        next_url = url + "?" + urllib.parse.urlencode(next_params)
                        next_req = urllib.request.Request(
                            next_url, headers=airtable_config.api_headers()
                        )
                        with urllib.request.urlopen(next_req) as next_response:
                            page_data = json.loads(next_response.read().decode())
                            all_records.extend(page_data.get("records", []))
                            offset = page_data.get("offset")

                    stats[count_key] = len(all_records)
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Failed to fetch {count_key} task count for {base_key}: "
                f"{e.read().decode()}",
                file=sys.stderr,
            )

    return stats


def main():
    parser = argparse.ArgumentParser(description="Gather monthly planning data")
    parser.add_argument(
        "--month",
        help="Month to review (YYYY-MM)",
        default=datetime.now().strftime("%Y-%m"),
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)

    year = (
        args.month.split("-")[0]
        if args.month and "-" in args.month
        else str(datetime.now().year)
    )
    result = {"review_month": args.month, "review_year": year}

    for base_key in ["personal", "aitb", "bb"]:
        base_data = {"base": base_key}

        # Annual goals
        goal_type = "annual"
        base_goals = airtable_config.get_base(config, base_key).get("goals", {})
        if goal_type in base_goals:
            base_data["annual_goals"] = fetch_goals(
                base_key, goal_type, config, year=year
            )
        else:
            base_data["annual_goals"] = []

        # Monthly goals (Mountains)
        base_data["mountains"] = fetch_mountains(base_key, config, month=args.month)

        # Active projects
        base_data["active_projects"] = fetch_active_projects(base_key, config)

        # Task stats
        base_data["task_stats"] = fetch_task_stats(base_key, config)

        result[base_key] = base_data

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
