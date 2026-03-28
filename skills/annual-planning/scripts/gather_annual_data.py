#!/usr/bin/env python3
"""
Gather annual planning data from all Airtable bases.

Fetches annual objectives/goals from all 3 bases, along with
mountain completion rates, project completion stats, and goal statuses
to produce a consolidated annual briefing.

Usage:
    python3 gather_annual_data.py [--config path/to/config.yaml]

Output:
    JSON object with per-base data for objectives, mountains, projects,
    and completion stats.

Requires AIRTABLE_TOKEN environment variable.
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
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "routing-airtable-tasks"
    ),
)

import airtable_config  # noqa: E402
from query_goals import fetch_goals  # noqa: E402

# ---------------------------------------------------------------------------
# Objective table config per base (table IDs for URL construction)
# ---------------------------------------------------------------------------

OBJECTIVE_TABLE_IDS = {
    "personal": "tbll1AUS4uBF9Cgnh",
    "aitb": "tblZIpLbkqFjAniNR",
    "bb": "tblAYaj2ZYhZtgp2a",
}

# Mountain table config per base -- includes completed/archived for stats
MOUNTAIN_CONFIG = {
    "personal": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "status_field": "Status",
        "objective_field": "1yr Goals",
    },
    "aitb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "status_field": "Status",
        "objective_field": "Objective",
    },
    "bb": {
        "table": "Mountains (30d)",
        "name_field": "Title",
        "status_field": "Status",
        "objective_field": "Objective (1y)",
    },
}


def fetch_all_mountains(base_key: str, config: dict) -> list[dict]:
    """Fetch ALL Mountains from a base (including completed/archived) for stats."""
    mtn_cfg = MOUNTAIN_CONFIG[base_key]
    base_id = airtable_config.get_base(config, base_key)["base_id"]
    encoded_table = urllib.parse.quote(mtn_cfg["table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"

    all_records = []
    offset = None

    while True:
        params = {}
        if offset:
            params["offset"] = offset
        req_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(req_url, headers=airtable_config.api_headers())

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                for record in data.get("records", []):
                    fields = record.get("fields", {})
                    all_records.append(
                        {
                            "id": record["id"],
                            "title": fields.get(mtn_cfg["name_field"], ""),
                            "status": fields.get(mtn_cfg["status_field"], ""),
                            "objective_ids": fields.get(mtn_cfg["objective_field"], []),
                        }
                    )
                offset = data.get("offset")
                if not offset:
                    break
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Failed to fetch mountains for {base_key}: {e.read().decode()}",
                file=sys.stderr,
            )
            break

    return all_records


def fetch_project_stats(base_key: str, config: dict) -> dict:
    """Fetch project completion stats from a base."""
    base_cfg = airtable_config.get_base(config, base_key)
    base_id = base_cfg["base_id"]
    encoded_table = urllib.parse.quote(base_cfg["project_table"])
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"

    all_projects = []
    offset = None

    while True:
        params = {"fields[]": base_cfg["project_status_field"]}
        if offset:
            params["offset"] = offset
        req_url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(req_url, headers=airtable_config.api_headers())

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                for record in data.get("records", []):
                    fields = record.get("fields", {})
                    all_projects.append(
                        fields.get(base_cfg["project_status_field"], "")
                    )
                offset = data.get("offset")
                if not offset:
                    break
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Failed to fetch projects for {base_key}: {e.read().decode()}",
                file=sys.stderr,
            )
            break

    done_statuses = {"Complete", "Done", "Completed", "Archived"}
    total = len(all_projects)
    completed = sum(1 for s in all_projects if s in done_statuses)

    return {
        "total": total,
        "completed": completed,
        "active": total - completed,
        "completion_rate": round(completed / total * 100, 1) if total else 0,
    }


def compute_mountain_stats(
    mountains: list[dict], objective_id: str | None = None
) -> dict:
    """Compute mountain completion stats, optionally filtered by objective."""
    if objective_id:
        filtered = [m for m in mountains if objective_id in m.get("objective_ids", [])]
    else:
        filtered = mountains

    total = len(filtered)
    completed = sum(1 for m in filtered if m["status"] == "Complete")
    active = sum(1 for m in filtered if m["status"] not in ("Complete", "Archived", ""))
    archived = sum(1 for m in filtered if m["status"] == "Archived")

    return {
        "total": total,
        "completed": completed,
        "active": active,
        "archived": archived,
        "completion_rate": round(completed / total * 100, 1) if total else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Gather annual planning data")
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)

    result = {}

    for base_key in ["personal", "aitb", "bb"]:
        base_data = {"base": base_key}

        # Annual goals/objectives
        goal_type = "annual"
        base_goals = airtable_config.get_base(config, base_key).get("goals", {})
        if goal_type in base_goals:
            goals = fetch_goals(base_key, goal_type, config)
        else:
            goals = []

        # All mountains (including completed) for stats
        all_mountains = fetch_all_mountains(base_key, config)

        # Enrich each goal with mountain stats
        for goal in goals:
            goal["mountain_stats"] = compute_mountain_stats(all_mountains, goal["id"])

        base_data["objectives"] = goals
        base_data["mountain_stats_total"] = compute_mountain_stats(all_mountains)

        # Project stats
        base_data["project_stats"] = fetch_project_stats(base_key, config)

        # Objective summary
        total = len(goals)
        statuses = {}
        for g in goals:
            s = g.get("status", "Unknown") or "Unknown"
            statuses[s] = statuses.get(s, 0) + 1

        base_data["objective_summary"] = {
            "total": total,
            "by_status": statuses,
        }

        # Airtable URL for objectives table
        table_id = OBJECTIVE_TABLE_IDS.get(base_key)
        base_id = airtable_config.get_base(config, base_key)["base_id"]
        if table_id:
            base_data["objectives_url"] = f"https://airtable.com/{base_id}/{table_id}"

        result[base_key] = base_data

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
