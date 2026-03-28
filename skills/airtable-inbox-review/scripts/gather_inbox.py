#!/usr/bin/env python3
"""
Fetch inbox tasks from all Airtable bases (Personal, AITB, BB).

Inbox tasks are those linked to the base's "Inbox" project. Outputs structured JSON for the AI agent
to analyze clarity and route tasks.

Usage:
    python3 gather_inbox.py [--config path/to/config.yaml]

Output:
    JSON with bases (personal, aitb, bb) and summary.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Import shared Airtable config
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402

# Assignee IDs considered "in scope" for inbox review
SCOPE_PEOPLE = ["aaron", "pablo"]


def build_inbox_filter(base_key: str, config: dict) -> str:
    """Build an Airtable filterByFormula for inbox tasks in a base.

    Inbox tasks are those linked to the base's designated Inbox project,
    AND not in a done status.
    """
    base_cfg = airtable_config.get_base(config, base_key)
    project_field = base_cfg["project_field"]

    # Only include tasks linked to the Inbox project (not unrouted tasks
    # with no project). ARRAYJOIN returns display names, not record IDs.
    inbox_condition = f"FIND('Inbox', ARRAYJOIN({{{project_field}}}))"

    # Exclude done statuses
    done_conditions = [f"{{Status}}!='{s}'" for s in base_cfg["done_statuses"]]

    all_conditions = [inbox_condition] + done_conditions
    return f"AND({','.join(all_conditions)})"


def classify_project_status(task: dict, base_key: str, config: dict) -> str:
    """Classify a task's project status.

    Returns:
        "unrouted" -- no project linked
        "inbox"    -- linked to the inbox project
        "routed"   -- has a real (non-inbox) project
    """
    base_cfg = airtable_config.get_base(config, base_key)
    project_ids = task.get("project_ids", [])

    if not project_ids:
        return "unrouted"

    inbox_id = base_cfg["inbox_project_id"]
    # If the only project is the inbox project, it's inbox
    if project_ids == [inbox_id]:
        return "inbox"

    # Has at least one non-inbox project
    non_inbox = [pid for pid in project_ids if pid != inbox_id]
    if non_inbox:
        return "routed"

    return "inbox"


def _in_scope(assignee_ids: list, base_key: str, config: dict) -> bool:
    """Check if a task's assignees are in scope (Aaron, Pablo, or unassigned)."""
    if not assignee_ids:
        return True

    people = airtable_config.get_people(config)
    scope_ids = set()
    for person in SCOPE_PEOPLE:
        if person in people and base_key in people[person]:
            scope_ids.add(people[person][base_key])

    return any(aid in scope_ids for aid in assignee_ids)


def fetch_inbox_tasks(base_key: str, config: dict) -> list[dict]:
    """Fetch inbox tasks from a single base with pagination.

    Returns a list of task dicts with normalized field names.
    Tasks are filtered locally to only include those assigned to
    Aaron, Pablo, or unassigned.
    """
    base_cfg = airtable_config.get_base(config, base_key)
    base_url = f"https://api.airtable.com/v0/{base_cfg['base_id']}/{base_cfg['tasks_table_id']}"

    formula = build_inbox_filter(base_key, config)

    all_records: list[dict] = []
    offset: str | None = None
    max_pages = 5  # Safety cap: 500 records max

    for _ in range(max_pages):
        params: dict[str, str] = {
            "filterByFormula": formula,
            "sort[0][field]": base_cfg["score_field"],
            "sort[0][direction]": "desc",
        }
        if offset:
            params["offset"] = offset

        url = base_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=airtable_config.api_headers())

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Error querying {base_key}: {e.read().decode()}",
                file=sys.stderr,
            )
            return all_records
        except Exception as e:
            print(f"Warning: Error querying {base_key}: {e}", file=sys.stderr)
            return all_records

        for record in data.get("records", []):
            fields = record.get("fields", {})
            assignee_ids = fields.get(base_cfg["assignee_field"], [])

            # Local scope filtering
            if not _in_scope(assignee_ids, base_key, config):
                continue

            project_ids = fields.get(base_cfg["project_field"], [])
            # Normalize: Airtable returns "" for empty linked fields sometimes
            if isinstance(project_ids, str):
                project_ids = [] if project_ids == "" else [project_ids]

            task_dict = {
                "id": record["id"],
                "task": fields.get(base_cfg["task_field"], ""),
                "description": fields.get(base_cfg["description_field"], ""),
                "status": fields.get(base_cfg["status_field"], ""),
                "score": fields.get(base_cfg["score_field"], ""),
                "due_date": fields.get(base_cfg["due_date_field"], ""),
                "notes": fields.get(base_cfg["notes_field"], ""),
                "base": base_key,
                "airtable_url": airtable_config.airtable_record_url(
                    base_cfg["base_id"], base_cfg["tasks_table_id"], record["id"]
                ),
                "assignee_ids": assignee_ids,
                "project_ids": project_ids,
            }
            task_dict["project_status"] = classify_project_status(
                task_dict, base_key, config
            )

            # Drop tasks that already have a real project -- they matched
            # the formula only because their project name contains "Inbox"
            if task_dict["project_status"] == "routed":
                continue

            all_records.append(task_dict)

        offset = data.get("offset")
        if not offset:
            break

    return all_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch inbox tasks from all bases")
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    bases = airtable_config.get_bases(config)

    bases_result: dict[str, list] = {}
    total = 0

    for base_key in bases:
        tasks = fetch_inbox_tasks(base_key, config)
        bases_result[base_key] = tasks
        total += len(tasks)

    per_base = {k: len(v) for k, v in bases_result.items()}

    result = {
        "bases": bases_result,
        "summary": {
            "total_inbox_tasks": total,
            "per_base": per_base,
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
