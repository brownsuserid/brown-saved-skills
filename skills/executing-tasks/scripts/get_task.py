#!/usr/bin/env python3
"""
Fetch a single Airtable task with full context resolution.

Resolves linked records: task -> project -> goal chain.
For BB and AITB: also resolves deal/organization if present.

Usage:
    python3 get_task.py --base [personal|aitb|bb] --id <recordId> \
        [--no-resolve-links] [--config path/to/config.yaml]

Output:
    JSON object with task fields and resolved linked records.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Import shared Airtable config
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)
from airtable_config import (  # noqa: E402
    api_headers,
    api_url,
    airtable_record_url,
    get_base,
    load_config,
    resolve_config_path,
)


def fetch_record(base_id: str, table: str, record_id: str) -> dict | None:
    """Fetch a single record by ID from an Airtable table."""
    url = f"{api_url(base_id, table)}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(
            f"Warning: Could not fetch {table}/{record_id}: {error_body}",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"Warning: Could not fetch {table}/{record_id}: {e}", file=sys.stderr)
        return None


def resolve_project(base_key: str, base_cfg: dict, project_ids: list) -> dict | None:
    """Fetch the first linked project and return structured data."""
    if not project_ids:
        return None
    project_id = project_ids[0]
    record = fetch_record(base_cfg["base_id"], base_cfg["project_table"], project_id)
    if not record:
        return None
    fields = record.get("fields", {})
    project = {
        "id": record["id"],
        "name": fields.get(base_cfg["project_name_field"], ""),
        "description": fields.get(base_cfg["project_description_field"], ""),
        "status": fields.get(base_cfg["project_status_field"], ""),
    }
    return project


def resolve_mountain(base_cfg: dict, project_fields: dict) -> tuple[dict | None, dict]:
    """Fetch the first linked mountain from a project record's fields.

    Returns (mountain_dict, mountain_fields) so the caller can follow the goal chain.
    """
    mountain_field = base_cfg.get("project_mountain_field")
    if not mountain_field:
        return None, {}
    mountain_ids = project_fields.get(mountain_field, [])
    if not mountain_ids:
        return None, {}
    mountain_id = mountain_ids[0]
    mountain_table_id = base_cfg.get("mountain_table_id", "")
    if not mountain_table_id:
        return None, {}
    record = fetch_record(base_cfg["base_id"], mountain_table_id, mountain_id)
    if not record:
        return None, {}
    fields = record.get("fields", {})
    return {
        "id": record["id"],
        "name": fields.get(base_cfg.get("mountain_name_field", "Title"), ""),
        "status": fields.get("Status", ""),
    }, fields


def resolve_goal_from_mountain(base_cfg: dict, mountain_fields: dict) -> dict | None:
    """Fetch the first linked annual goal from a mountain record's fields."""
    goal_field = base_cfg.get("mountain_goal_field")
    if not goal_field:
        return None
    goal_ids = mountain_fields.get(goal_field, [])
    if not goal_ids:
        return None
    goal_id = goal_ids[0]
    goal_table_id = base_cfg.get("mountain_goal_table_id", "")
    if not goal_table_id:
        return None
    record = fetch_record(base_cfg["base_id"], goal_table_id, goal_id)
    if not record:
        return None
    fields = record.get("fields", {})
    return {
        "id": record["id"],
        "name": fields.get(base_cfg.get("mountain_goal_name_field", "Name"), ""),
        "status": fields.get("Status", ""),
        "type": base_cfg["goal_type"],
    }


def resolve_goal(base_key: str, base_cfg: dict, project_fields: dict) -> dict | None:
    """Fetch the first linked goal from a project record's fields (legacy path)."""
    goals_field = base_cfg.get("project_goals_field")
    if not goals_field:
        return None
    goal_ids = project_fields.get(goals_field, [])
    if not goal_ids:
        return None
    goal_id = goal_ids[0]
    record = fetch_record(base_cfg["base_id"], base_cfg["goals_table"], goal_id)
    if not record:
        return None
    fields = record.get("fields", {})
    return {
        "id": record["id"],
        "name": fields.get(base_cfg["goal_name_field"], ""),
        "status": fields.get("Status", ""),
        "type": base_cfg["goal_type"],
    }


def resolve_deal(base_cfg: dict, deal_ids: list) -> dict | None:
    """Fetch the first linked deal (BB/AITB only)."""
    if not base_cfg.get("deals_field") or not deal_ids:
        return None
    deal_id = deal_ids[0]
    record = fetch_record(base_cfg["base_id"], "Deals", deal_id)
    if not record:
        return None
    fields = record.get("fields", {})
    return {
        "id": record["id"],
        "name": fields.get("Name", fields.get("Deal Name", "")),
        "status": fields.get("Status", ""),
    }


def resolve_organization(base_cfg: dict, org_ids: list) -> dict | None:
    """Fetch the first linked organization (BB/AITB only)."""
    if not base_cfg.get("orgs_table") or not org_ids:
        return None
    org_id = org_ids[0]
    record = fetch_record(base_cfg["base_id"], base_cfg["orgs_table"], org_id)
    if not record:
        return None
    fields = record.get("fields", {})
    return {
        "id": record["id"],
        "name": fields.get("Name", ""),
    }


def get_task(
    config: dict, base_key: str, record_id: str, resolve_links: bool = True
) -> dict:
    """Fetch a task and optionally resolve all linked records."""
    base_cfg = get_base(config, base_key)
    record = fetch_record(base_cfg["base_id"], base_cfg["tasks_table_id"], record_id)
    if not record:
        print(f"Error: Task {record_id} not found in {base_key}", file=sys.stderr)
        sys.exit(1)

    fields = record.get("fields", {})
    task = {
        "id": record["id"],
        "task": fields.get(base_cfg["task_field"], ""),
        "status": fields.get(base_cfg["status_field"], ""),
        "description": fields.get(base_cfg["description_field"], ""),
        "notes": fields.get(base_cfg["notes_field"], ""),
        "due_date": fields.get(base_cfg["due_date_field"], ""),
        "score": fields.get(base_cfg["score_field"], ""),
        "assignee_ids": fields.get(base_cfg["assignee_field"], []),
        "hitl_brief": fields.get(base_cfg["hitl_brief_field"], ""),
        "hitl_response": fields.get(base_cfg["hitl_response_field"], ""),
        "hitl_status": fields.get(base_cfg["hitl_status_field"], ""),
        "task_output": fields.get(base_cfg["task_output_field"], ""),
        "base": base_key,
        "airtable_url": airtable_record_url(
            base_cfg["base_id"], base_cfg["tasks_table_id"], record["id"]
        ),
    }

    if not resolve_links:
        return task

    # Resolve project
    project_ids = fields.get(base_cfg["project_field"], [])
    project = resolve_project(base_key, base_cfg, project_ids)
    if project:
        task["project"] = project

        # Resolve mountain and goal via project -> mountain -> goal chain
        project_record = fetch_record(
            base_cfg["base_id"], base_cfg["project_table"], project_ids[0]
        )
        if project_record:
            project_fields = project_record.get("fields", {})

            # Mountain resolution (project -> mountain)
            mountain, mountain_fields = resolve_mountain(base_cfg, project_fields)
            if mountain:
                task["mountain"] = mountain

                # Goal resolution via mountain -> goal
                goal = resolve_goal_from_mountain(base_cfg, mountain_fields)
                if goal:
                    task["goal"] = goal

            # Fallback: direct project -> goal link (personal base has this)
            if "goal" not in task:
                goal = resolve_goal(base_key, base_cfg, project_fields)
                if goal:
                    task["goal"] = goal

    # Resolve deal (BB uses "Deals", AITB uses "Sponsor Deals")
    deals_field = base_cfg.get("deals_field")
    deal_ids = fields.get(deals_field, []) if deals_field else []
    if isinstance(deal_ids, list):
        deal = resolve_deal(base_cfg, deal_ids)
        if deal:
            task["deal"] = deal

    # Resolve organization (BB/AITB)
    org_ids = fields.get("Organization", fields.get("Organizations", []))
    if isinstance(org_ids, list):
        org = resolve_organization(base_cfg, org_ids)
        if org:
            task["organization"] = org

    return task


def main():
    parser = argparse.ArgumentParser(
        description="Fetch an Airtable task with full context"
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base the task is in",
    )
    parser.add_argument("--id", required=True, help="The Airtable record ID (recXXX)")
    parser.add_argument(
        "--no-resolve-links",
        action="store_true",
        help="Skip resolving linked records (project, goal, deal, org)",
    )
    parser.add_argument("--config", help="Path to Airtable config YAML")

    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)

    task = get_task(config, args.base, args.id, resolve_links=not args.no_resolve_links)
    print(json.dumps(task, indent=2))


if __name__ == "__main__":
    main()
