#!/usr/bin/env python3
"""
Create a new task in an Airtable base.

Usage:
    python3 create_task.py --base [personal|aitb|bb] \
        --title "Task title" \
        [--description "What needs to be done"] \
        [--assignee pablo|aaron|<recordId>] \
        [--project <projectRecordId>] \
        [--status "Not Started"] \
        [--due-date "2026-02-15"] \
        [--notes "Additional context"] \
        [--linked-task <originalTaskId>] \
        [--for-today] \
        [--deal <dealRecordId>] \
        [--recurrence Daily|Weekly|Bi-weekly|Monthly|Quarterly|Annually] \
        [--depends-on recXXX recYYY ...]

Quality standard: see managing-projects/references/creating-tasks.md
Warnings are printed to stderr when key fields are missing.

Output:
    JSON with the created record ID and Airtable URL.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

import os

# Import shared Airtable config
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
from _config import (  # noqa: E402
    BASES,
    api_headers,
    airtable_record_url,
    resolve_assignee,
    resolve_status,
)


def link_task_to_deal(base_key: str, deal_id: str, task_id: str) -> bool:
    """Add a task to a deal's Tasks linked record field."""
    config = BASES[base_key]

    # First get the current Tasks on the deal
    url = f"https://api.airtable.com/v0/{config['base_id']}/Deals/{deal_id}"
    req = urllib.request.Request(url, headers=api_headers(), method="GET")

    try:
        with urllib.request.urlopen(req) as resp:
            deal_data = json.loads(resp.read().decode())
            current_tasks = deal_data.get("fields", {}).get("Tasks", [])
    except urllib.error.HTTPError:
        current_tasks = []

    # Add the new task ID
    updated_tasks = current_tasks + [task_id]

    # Update the deal
    update_payload = json.dumps({"fields": {"Tasks": updated_tasks}}).encode()
    req = urllib.request.Request(
        url, data=update_payload, headers=api_headers(), method="PATCH"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return True
    except urllib.error.HTTPError as e:
        print(
            f"Warning: Failed to link task to deal: {e.read().decode()}",
            file=sys.stderr,
        )
        return False


def create_task(
    base_key: str,
    title: str,
    description: str | None = None,
    assignee: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    notes: str | None = None,
    linked_task: str | None = None,
    for_today: bool = False,
    deal_id: str | None = None,
    recurrence: str | None = None,
    depends_on: list[str] | None = None,
) -> dict:
    """POST a new task record to the specified Airtable base."""
    config = BASES[base_key]

    fields = {
        config["task_field"]: title,
    }

    # Default status per base
    if status:
        fields[config["status_field"]] = resolve_status(status, base_key)
    else:
        fields[config["status_field"]] = config["status_values"]["not_started"]

    # Default assignee to Aaron
    if assignee:
        fields[config["assignee_field"]] = [resolve_assignee(assignee, base_key)]
    else:
        fields[config["assignee_field"]] = [resolve_assignee("aaron", base_key)]

    if description:
        fields[config["description_field"]] = description

    if project_id:
        fields[config["project_field"]] = [project_id]

    if due_date:
        fields[config["due_date_field"]] = due_date

    # Handle notes - append linked task reference if provided
    notes_text = notes or ""
    if linked_task:
        link_ref = f"\n\n---\nFollow-up from: {linked_task}"
        notes_text = (notes_text + link_ref).strip()
    if notes_text:
        fields[config["notes_field"]] = notes_text

    if for_today:
        fields[config["for_today_field"]] = True

    if recurrence:
        fields["Recurrence"] = recurrence

    if depends_on:
        fields[config["depends_on_field"]] = depends_on

    url = f"https://api.airtable.com/v0/{config['base_id']}/{config['tasks_table_id']}"
    payload = json.dumps({"fields": fields}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

            # Link task to deal if provided
            if deal_id and base_key in ("bb", "aitb"):
                linked = link_task_to_deal(base_key, deal_id, data["id"])
                data["_deal_linked"] = linked

            return data
    except urllib.error.HTTPError as e:
        print(f"Error creating task: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a new Airtable task")
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to create the task in",
    )
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--description", help="Task description")
    parser.add_argument(
        "--assignee", help="Assignee: aaron (default), pablo, or record ID"
    )
    parser.add_argument("--project", help="Project record ID to link")
    parser.add_argument(
        "--status", help="Initial status (default: Not Started / Pending per base)"
    )
    parser.add_argument("--due-date", help="Due date in YYYY-MM-DD format")
    parser.add_argument("--notes", help="Notes field content")
    parser.add_argument(
        "--linked-task",
        help="Record ID of the originating task (for follow-up tracking)",
    )
    parser.add_argument(
        "--for-today",
        action="store_true",
        help="Set the For Today checkbox (for same-day urgency)",
    )
    parser.add_argument(
        "--deal",
        help="Deal record ID to link this task to (bb and aitb only)",
    )
    parser.add_argument(
        "--recurrence",
        choices=["Daily", "Weekly", "Bi-weekly", "Monthly", "Quarterly", "Annually"],
        help="Recurrence pattern for recurring tasks",
    )
    parser.add_argument(
        "--depends-on",
        nargs="+",
        help="Record IDs of tasks this task depends on (recXXX ...)",
    )

    args = parser.parse_args()

    # Quality warnings (stderr only, not errors)
    if not args.description:
        print(
            "Warning: No --description (Definition of Done). "
            "See creating-tasks.md quality standard.",
            file=sys.stderr,
        )
    if not args.project:
        print(
            "Error: --project is required. Tasks without a project have broken "
            "score calculation and fall off priority lists. "
            "See creating-tasks.md quality standard.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = create_task(
        base_key=args.base,
        title=args.title,
        description=args.description,
        assignee=args.assignee,
        project_id=args.project,
        status=args.status,
        due_date=args.due_date,
        notes=args.notes,
        linked_task=args.linked_task,
        for_today=args.for_today,
        deal_id=args.deal,
        recurrence=args.recurrence,
        depends_on=args.depends_on,
    )

    config = BASES[args.base]
    output = {
        "id": result["id"],
        "task": result.get("fields", {}).get(config["task_field"], ""),
        "status": result.get("fields", {}).get(config["status_field"], ""),
        "base": args.base,
        "airtable_url": airtable_record_url(
            config["base_id"], config["tasks_table_id"], result["id"]
        ),
    }
    if result.get("_deal_linked"):
        output["deal_linked"] = True
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
