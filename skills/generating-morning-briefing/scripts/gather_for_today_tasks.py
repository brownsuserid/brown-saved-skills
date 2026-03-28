#!/usr/bin/env python3
"""
Fetch all tasks marked "For Today" across all Airtable bases that are not complete.

By default, only actionable tasks are returned (excludes In Progress, Blocked,
Human Review, Validating, Completed, and Archived). Use flags to widen the filter.

Usage:
    python3 gather_for_today_tasks.py [--assignee NAME] [--include-in-progress] [--include-blocked] [--include-human-review] [--include-all] [--config path/to/config.yaml]

Output:
    JSON with for_today_tasks array and total_count.

Examples:
    python3 gather_for_today_tasks.py                               # Not Started tasks only (default)
    python3 gather_for_today_tasks.py --assignee aaron              # Aaron's Not Started tasks
    python3 gather_for_today_tasks.py --include-in-progress         # Include In Progress tasks
    python3 gather_for_today_tasks.py --include-blocked             # Include Blocked tasks
    python3 gather_for_today_tasks.py --include-human-review        # Include Human Review tasks
    python3 gather_for_today_tasks.py --include-all                 # Include all active statuses
    python3 gather_for_today_tasks.py --assignee all --include-all  # Everyone, all active
"""

import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from typing import Any, Optional

# Import shared Airtable config
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402

# Base name display mapping
BASE_NAMES = {"personal": "Personal", "aitb": "AITB", "bb": "BB"}


def make_request(url: str, token: str) -> dict[str, Any]:
    """Make authenticated request to Airtable API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"Airtable API error: {e.code} - {error_body}")
    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")


def resolve_assignee_id(
    assignee_name: str, base_key: str, people: dict
) -> Optional[str]:
    """Resolve assignee name to ID for a specific base."""
    assignee_lower = assignee_name.lower()
    if assignee_lower in people and base_key in people[assignee_lower]:
        return people[assignee_lower][base_key]
    return None


def fetch_for_today_tasks(
    base_key: str,
    token: str,
    config: dict,
    assignee: Optional[str] = None,
    include_in_progress: bool = False,
    include_blocked: bool = False,
    include_human_review: bool = False,
) -> list[dict[str, Any]]:
    """Fetch tasks marked For Today that are not complete for a specific base.

    Args:
        base_key: One of 'personal', 'aitb', 'bb'.
        token: Airtable API token.
        config: Loaded YAML config dict.
        assignee: Optional assignee name to filter by.
        include_in_progress: If True, include 'In Progress' tasks (excluded by default).
        include_blocked: If True, include 'Blocked' tasks (excluded by default).
        include_human_review: If True, include 'Human Review' tasks (excluded by default).
    """
    bases = airtable_config.get_bases(config)
    people = airtable_config.get_people(config)
    cfg = bases[base_key]
    base_id = cfg["base_id"]
    table_name = cfg["tasks_table_name"]
    status_field = cfg["status_field"]
    for_today_field = cfg["for_today_field"]
    score_field = cfg["score_field"]
    assignee_field = cfg["assignee_field"]
    description_field = cfg["description_field"]

    # Always exclude terminal statuses; conditionally exclude active ones
    excluded = ["Completed", "Archived", "Validating", "Cancelled"]
    if not include_human_review:
        excluded.append("Human Review")
    if not include_in_progress:
        excluded.append("In Progress")
    if not include_blocked:
        excluded.append("Blocked")

    exclusions = ",".join(f"{{{status_field}}}!='{s}'" for s in excluded)
    formula = f"AND({{{for_today_field}}}=1,{exclusions})"

    encoded_formula = urllib.parse.quote(formula)
    url = (
        f"https://api.airtable.com/v0/{base_id}/{table_name}"
        f"?filterByFormula={encoded_formula}"
        f"&sort[0][field]={score_field}&sort[0][direction]=desc"
    )

    response = make_request(url, token)

    tasks = []
    target_assignee_id = (
        resolve_assignee_id(assignee, base_key, people) if assignee else None
    )

    for record in response.get("records", []):
        fields = record.get("fields", {})

        if target_assignee_id:
            assignee_ids = fields.get(assignee_field, [])
            if target_assignee_id not in assignee_ids:
                continue

        task_name = fields.get("Task", "")
        task_data = {
            "id": record.get("id"),
            "task": task_name,
            "score": fields.get(score_field, 0),
            "status": fields.get(status_field),
            "definition_of_done": fields.get(description_field),
            "due": fields.get("Due"),
            "notes": fields.get("Notes"),
            "base": BASE_NAMES.get(base_key, base_key),
            "airtable_url": airtable_config.airtable_record_url(
                base_id, cfg["tasks_table_id"], record.get("id")
            ),
            "pablo_url": f"http://localhost:19280/task/{urllib.parse.quote(task_name.replace(':', ''))}",
        }
        tasks.append(task_data)

    return tasks


def main():
    parser = argparse.ArgumentParser(
        description="Fetch tasks marked 'For Today' across all Airtable bases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 gather_for_today_tasks.py                               # Not Started only (default)
  python3 gather_for_today_tasks.py --assignee aaron              # Aaron's Not Started tasks
  python3 gather_for_today_tasks.py --include-in-progress         # Include In Progress
  python3 gather_for_today_tasks.py --include-blocked             # Include Blocked
  python3 gather_for_today_tasks.py --include-human-review        # Include Human Review
  python3 gather_for_today_tasks.py --include-all                 # Include all active statuses
  python3 gather_for_today_tasks.py --assignee all --include-all  # Everyone, all active
        """,
    )
    parser.add_argument(
        "--assignee",
        default="aaron",
        help="Filter by assignee name (default: aaron). Use 'all' for no filter.",
    )
    parser.add_argument(
        "--include-in-progress",
        action="store_true",
        default=False,
        help="Include tasks with status 'In Progress' (excluded by default).",
    )
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        default=False,
        help="Include tasks with status 'Blocked' (excluded by default).",
    )
    parser.add_argument(
        "--include-human-review",
        action="store_true",
        default=False,
        help="Include tasks with status 'Human Review' (excluded by default).",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        default=False,
        help="Include all active statuses: In Progress, Blocked, and Human Review.",
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    # --include-all is a convenience shortcut
    if args.include_all:
        args.include_in_progress = True
        args.include_blocked = True
        args.include_human_review = True

    token = os.environ.get("AIRTABLE_TOKEN")
    if not token:
        print(
            json.dumps({"error": "AIRTABLE_TOKEN environment variable not set"}),
            file=sys.stderr,
        )
        sys.exit(1)

    config = airtable_config.load_config(args.config)
    bases = airtable_config.get_bases(config)

    all_for_today = []

    assignee_filter = None if args.assignee.lower() == "all" else args.assignee

    for base_key in bases:
        try:
            tasks = fetch_for_today_tasks(
                base_key,
                token,
                config,
                assignee=assignee_filter,
                include_in_progress=args.include_in_progress,
                include_blocked=args.include_blocked,
                include_human_review=args.include_human_review,
            )
            all_for_today.extend(tasks)
        except Exception as e:
            print(
                f"Error fetching from {BASE_NAMES.get(base_key, base_key)}: {e}",
                file=sys.stderr,
            )

    all_for_today.sort(key=lambda t: t.get("score") or 0, reverse=True)

    result = {
        "display_format": (
            "Present tasks as a numbered list sorted by score (highest first). "
            "No grouping by status. No emoji. Exact task names only (never paraphrase). "
            "For each task show: number, bold task name, score, base, status, and due date if set. "
            "On the next line show the definition_of_done. "
            "Then show both links on separate lines:\n"
            "  Airtable: {airtable_url}\n"
            "  Pablo: {pablo_url}\n"
            "Separate each task with a --- horizontal rule for readability. "
            "Number sequentially so the user can refer to tasks by number."
        ),
        "for_today_tasks": all_for_today,
        "total_count": len(all_for_today),
    }

    if assignee_filter:
        result["filter"] = f"assignee: {assignee_filter}"

    active_filters = []
    if args.include_in_progress:
        active_filters.append("in_progress")
    if args.include_blocked:
        active_filters.append("blocked")
    if args.include_human_review:
        active_filters.append("human_review")
    if active_filters:
        result["included_statuses"] = active_filters

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
