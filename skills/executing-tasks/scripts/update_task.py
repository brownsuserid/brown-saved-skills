#!/usr/bin/env python3
"""
Update fields on an Airtable task record.

Usage:
    # Individual field updates:
    python3 update_task.py --base [personal|aitb|bb] --id <recordId> \
        [--status "In Progress"] \
        [--notes "Added context..."] \
        [--hitl-brief "Plan: ..."] \
        [--task-output "Deliverable: ..."]

    # Phase shortcuts (set multiple fields at once):
    python3 update_task.py --base bb --id recXXX --phase start
    python3 update_task.py --base bb --id recXXX --phase plan-ready --hitl-brief "Plan: ..."
    python3 update_task.py --base bb --id recXXX --phase pick-up
    python3 update_task.py --base bb --id recXXX --phase work-done --hitl-brief "Summary: ..." --task-output "Draft in Gmail..."
    python3 update_task.py --base bb --id recXXX --phase blocked --notes "Waiting on..."
    python3 update_task.py --base bb --id recXXX --phase archive

Phases:
    start       -> Status: In Progress
    plan-ready  -> Status: In Progress, HITL Status: Processed
                   (requires --hitl-brief)
    pick-up     -> HITL Status: Processed
                   (use after Aaron approves plan, Status already In Progress)
    work-done   -> Status: Human Review, HITL Status: Pending Review
                   (requires --hitl-brief and --task-output)
    blocked     -> Status: Blocked (requires --notes)
    archive     -> Status: Archived

Only specified fields are updated (PATCH semantics).
Status values are translated from semantic names automatically.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

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

# ---------------------------------------------------------------------------
# Phase definitions: shorthand for multi-field HITL transitions
# ---------------------------------------------------------------------------

PHASES = {
    "start": {
        "sets": {"status": "in_progress"},
        "requires": [],
        "next_step": 'Write your execution plan, then run: --phase plan-ready --hitl-brief "Plan: ..."',
    },
    "plan-ready": {
        "sets": {"status": "in_progress", "hitl_status": "Processed"},
        "requires": ["hitl_brief"],
        "next_step": "Plan saved to HITL Brief. STOP — do NOT execute. Aaron must set HITL Status=Response Submitted to approve before execution can begin.",
    },
    "pick-up": {
        "sets": {"hitl_status": "Processed"},
        "requires": [],
        "next_step": 'Execute the approved plan. Store deliverable in --task-output. Then run: --phase work-done --hitl-brief "Summary: ..." --task-output "..."',
    },
    "work-done": {
        "sets": {"status": "human_review", "hitl_status": "Pending Review"},
        "requires": ["hitl_brief", "task_output"],
        "next_step": "STOP. Wait for Aaron to review. He will set Status=Completed + HITL Status=Completed.",
    },
    "blocked": {
        "sets": {"status": "blocked"},
        "requires": ["notes"],
        "next_step": "Move to next task. Aaron will see this in his Blocked queue.",
    },
    "archive": {
        "sets": {"status": "archived"},
        "requires": [],
        "next_step": "Task archived. No further action needed.",
    },
}


def fetch_current_hitl_status(base_key: str, record_id: str) -> str:
    """Fetch the current HITL Status value for a task record."""
    config = BASES[base_key]
    url = f"https://api.airtable.com/v0/{config['base_id']}/{config['tasks_table_id']}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("fields", {}).get(config.get("hitl_status_field", ""), "")
    except Exception as e:
        print(
            f"Warning: Could not verify HITL status before pick-up: {e}",
            file=sys.stderr,
        )
        return ""


def update_task(
    base_key: str,
    record_id: str,
    updates: dict,
    force: bool = False,
    phase: str | None = None,
) -> dict:
    """PATCH an Airtable task record with the given field updates."""
    config = BASES[base_key]

    # SAFETY GATE: --phase pick-up is only allowed when Aaron has set HITL Status=Response Submitted.
    # This prevents execution of tasks that have not been approved by Aaron.
    if phase == "pick-up" and not force:
        current_hitl = fetch_current_hitl_status(base_key, record_id)
        if current_hitl != "Response Submitted":
            print(
                f"Error: --phase pick-up requires HITL Status='Response Submitted' (Aaron's approval). "
                f"Current HITL Status is '{current_hitl}'. "
                f"Aaron must approve this plan before it can be executed. "
                f"Use --force to override this check (for admin use only).",
                file=sys.stderr,
            )
            sys.exit(1)

    # Build the fields payload
    fields = {}

    if "status" in updates:
        status_val = resolve_status(updates["status"], base_key)
        if status_val in ("Cancelled",) and not force:
            print(
                "Error: Setting status to 'Cancelled' requires --force flag.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[config["status_field"]] = status_val

        # Auto-set Date Complete when marking as Completed
        if status_val == config["status_values"]["complete"]:
            from datetime import datetime, timedelta, timezone

            phoenix_tz = timezone(timedelta(hours=-7))
            fields["Date Complete"] = datetime.now(phoenix_tz).strftime("%Y-%m-%d")

    if "notes" in updates:
        fields[config["notes_field"]] = updates["notes"]

    if "description" in updates:
        fields[config["description_field"]] = updates["description"]

    if "assignee" in updates:
        assignee_id = resolve_assignee(updates["assignee"], base_key)
        # Assignee is an array of linked record IDs
        fields[config["assignee_field"]] = [assignee_id]

    if "project" in updates:
        project_field = config.get("project_field")
        if not project_field:
            print(
                f"Error: Base '{base_key}' does not have a project_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Project is an array of linked record IDs
        fields[project_field] = [updates["project"]]

    if "due" in updates:
        due_field = config.get("due_date_field")
        if not due_field:
            print(
                f"Error: Base '{base_key}' does not have a due_date_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[due_field] = updates["due"]

    if "recurrence" in updates:
        fields["Recurrence"] = updates["recurrence"]

    if "hitl_brief" in updates:
        fields[config["hitl_brief_field"]] = updates["hitl_brief"]

    if "hitl_response" in updates:
        fields[config["hitl_response_field"]] = updates["hitl_response"]

    if "hitl_status" in updates:
        fields[config["hitl_status_field"]] = updates["hitl_status"]

    if "task_output" in updates:
        fields[config["task_output_field"]] = updates["task_output"]

    if "depends_on" in updates:
        fields[config["depends_on_field"]] = updates["depends_on"]

    if "for_today" in updates:
        fields[config["for_today_field"]] = updates["for_today"]

    if "title" in updates:
        fields[config["task_field"]] = updates["title"]

    if not fields:
        print(
            "Error: No fields to update. Use --phase <phase> or specify individual fields.",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"https://api.airtable.com/v0/{config['base_id']}/{config['tasks_table_id']}/{record_id}"
    payload = json.dumps({"fields": fields, "typecast": True}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="PATCH"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"Error updating task: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Update an Airtable task. Use --phase for HITL workflow shortcuts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Phases (HITL workflow shortcuts):
  start       Status -> In Progress. Begin planning.
  plan-ready  Status -> In Progress, HITL -> Processed. Requires --hitl-brief.
  pick-up     HITL -> Processed. Resume after Aaron approves plan.
  work-done   Status -> Human Review, HITL -> Pending Review. Requires --hitl-brief + --task-output.
  blocked     Status -> Blocked. Requires --notes.
  archive     Status -> Archived.
""",
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base the task is in",
    )
    parser.add_argument("--id", required=True, help="The Airtable record ID (recXXX)")
    parser.add_argument(
        "--phase",
        choices=list(PHASES.keys()),
        help="HITL phase shortcut (sets multiple fields automatically)",
    )
    parser.add_argument(
        "--status",
        help="New status (semantic: in_progress, complete, blocked, etc. or literal)",
    )
    parser.add_argument("--notes", help="New value for Notes field")
    parser.add_argument("--description", help="New value for Description field")
    parser.add_argument("--title", help="New task title/name")
    parser.add_argument(
        "--assignee",
        help="New assignee: aaron, pablo, juan, josh, sven (bb-only: josh, sven), or raw record ID",
    )
    parser.add_argument("--project", help="Project record ID (recXXX) to link task to")
    parser.add_argument("--due", help="Due date in YYYY-MM-DD format")
    parser.add_argument(
        "--recurrence",
        choices=["Daily", "Weekly", "Bi-weekly", "Monthly", "Quarterly", "Annually"],
        help="Recurrence pattern for recurring tasks",
    )
    parser.add_argument(
        "--hitl-brief",
        help="Execution plan or completion summary for Aaron's review",
    )
    parser.add_argument(
        "--hitl-response",
        help="Aaron's approval or feedback",
    )
    parser.add_argument(
        "--hitl-status",
        choices=["Pending Review", "Response Submitted", "Processed", "Completed"],
        help="HITL workflow status",
    )
    parser.add_argument(
        "--task-output",
        help="Work product or deliverable",
    )
    parser.add_argument(
        "--depends-on",
        nargs="+",
        help="Record IDs of tasks this task depends on (recXXX ...)",
    )
    parser.add_argument(
        "--for-today",
        action="store_true",
        default=None,
        help="Set the For Today checkbox",
    )
    parser.add_argument(
        "--not-for-today",
        action="store_true",
        default=None,
        help="Clear the For Today checkbox",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow dangerous status changes (e.g., Cancelled)",
    )

    args = parser.parse_args()

    updates = {}

    # Apply phase shortcut first (individual flags can override)
    phase_def = None
    if args.phase:
        phase_def = PHASES[args.phase]

        # Check required fields
        missing = []
        for req_field in phase_def["requires"]:
            arg_name = req_field.replace("_", "-")
            if not getattr(args, req_field.replace("-", "_"), None):
                missing.append(f"--{arg_name}")
        if missing:
            print(
                f"Error: --phase {args.phase} requires: {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Apply phase defaults
        updates.update(phase_def["sets"])

    # Individual flags override phase defaults
    if args.status:
        updates["status"] = args.status
    if args.notes:
        updates["notes"] = args.notes
    if args.description:
        updates["description"] = args.description
    if args.title:
        updates["title"] = args.title
    if args.assignee:
        updates["assignee"] = args.assignee
    if args.project:
        updates["project"] = args.project
    if args.due:
        updates["due"] = args.due
    if args.recurrence:
        updates["recurrence"] = args.recurrence
    if args.hitl_brief:
        # Agents often pass literal \n; convert to real newlines for Airtable readability.
        updates["hitl_brief"] = args.hitl_brief.replace("\\n", "\n")
    if args.hitl_response:
        updates["hitl_response"] = args.hitl_response
    if args.hitl_status:
        updates["hitl_status"] = args.hitl_status
    if args.task_output:
        updates["task_output"] = args.task_output
    if args.depends_on:
        updates["depends_on"] = args.depends_on
    if args.for_today:
        updates["for_today"] = True
    if args.not_for_today:
        updates["for_today"] = False

    result = update_task(
        args.base, args.id, updates, force=args.force, phase=args.phase
    )

    # Print confirmation with next step guidance
    fields = result.get("fields", {})
    config = BASES[args.base]
    output = {
        "id": result["id"],
        "task": fields.get(config["task_field"], ""),
        "status": fields.get(config["status_field"], ""),
        "hitl_status": fields.get(config.get("hitl_status_field", ""), ""),
        "base": args.base,
        "airtable_url": airtable_record_url(
            config["base_id"], config["tasks_table_id"], result["id"]
        ),
        "updated_fields": list(updates.keys()),
    }

    if phase_def:
        output["phase"] = args.phase
        output["next_step"] = phase_def["next_step"]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
