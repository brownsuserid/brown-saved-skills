#!/usr/bin/env python3
"""
Roll all incomplete tasks from one project/rock to another.

Works across all bases (personal, aitb, bb). Handles full Airtable
pagination so no tasks are missed regardless of table size.

Usage:
    python3 roll_project_tasks.py \
        --base bb \
        --from-rock recXXXXXXXXXXXXXX \
        --to-rock   recYYYYYYYYYYYYYY \
        [--config path/to/config.yaml]

    python3 roll_project_tasks.py \
        --base personal \
        --from-rock recXXXXXXXXXXXXXX \
        --to-rock   recYYYYYYYYYYYYYY \
        --dry-run

Options:
    --base          Which Airtable base: personal | aitb | bb
    --from-rock     Record ID of the source project/rock
    --to-rock       Record ID of the destination project/rock
    --dry-run       Print what would be moved without making changes
    --include-done  Also move Completed/Cancelled/Archived tasks (rarely needed)
    --config        Path to YAML config file

Statuses moved by default:
    Not Started, In Progress, Blocked, Human Review, Validating

Statuses skipped by default:
    Completed, Cancelled, Archived
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

DONE_STATUSES = {"Completed", "Cancelled", "Archived"}


def fetch_all_tasks(
    base_key: str, from_rock: str, include_done: bool, config: dict
) -> list[dict]:
    """
    Paginate through the entire tasks table and return all tasks
    linked to from_rock. Uses per-request timeouts to avoid hangs.
    """
    base_cfg = airtable_config.get_base(config, base_key)
    base_id = base_cfg["base_id"]
    table = base_cfg["tasks_table_id"]
    project_field = base_cfg[
        "project_field"
    ]  # "Rock" for bb, "Project" for personal/aitb

    found = []
    offset = None
    page = 0

    while True:
        page += 1
        params = {
            "pageSize": "100",
            "fields[]": [
                base_cfg["task_field"],
                base_cfg["status_field"],
                project_field,
            ],
        }
        if offset:
            params["offset"] = offset

        url = (
            f"https://api.airtable.com/v0/{base_id}/{table}?"
            + urllib.parse.urlencode(params, doseq=True)
        )
        req = urllib.request.Request(url, headers=airtable_config.api_headers())
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"Error on page {page}: {e}", file=sys.stderr)
            sys.exit(1)

        for record in data.get("records", []):
            fields = record.get("fields", {})
            if from_rock not in fields.get(project_field, []):
                continue
            status = fields.get(base_cfg["status_field"], "")
            if not include_done and status in DONE_STATUSES:
                continue
            found.append(
                {
                    "id": record["id"],
                    "task": fields.get(base_cfg["task_field"], ""),
                    "status": status,
                }
            )

        offset = data.get("offset")
        if not offset:
            break

    return found


def move_task(base_key: str, task_id: str, to_rock: str, config: dict) -> dict:
    """PATCH a single task to point at the new rock/project."""
    base_cfg = airtable_config.get_base(config, base_key)
    base_id = base_cfg["base_id"]
    table = base_cfg["tasks_table_id"]
    project_field = base_cfg["project_field"]

    url = f"https://api.airtable.com/v0/{base_id}/{table}/{task_id}"
    payload = json.dumps({"fields": {project_field: [to_rock]}}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error moving {task_id}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Roll incomplete tasks from one project/rock to another."
    )
    parser.add_argument("--base", required=True, choices=["personal", "aitb", "bb"])
    parser.add_argument(
        "--from-rock", required=True, help="Source project/rock record ID"
    )
    parser.add_argument(
        "--to-rock", required=True, help="Destination project/rock record ID"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tasks that would be moved without making changes",
    )
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Also move Completed/Cancelled/Archived tasks",
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    base_cfg = airtable_config.get_base(config, args.base)

    print(f"Scanning {args.base} base for tasks in {args.from_rock}...")
    tasks = fetch_all_tasks(args.base, args.from_rock, args.include_done, config)

    if not tasks:
        print("No incomplete tasks found — nothing to roll.")
        return

    print(f"\nFound {len(tasks)} task(s) to roll:")
    for t in tasks:
        print(f"  [{t['status']}] {t['task'][:70]}")

    if args.dry_run:
        print(
            f"\nDry run — no changes made. Would have moved {len(tasks)} task(s) to {args.to_rock}."
        )
        return

    print(f"\nRolling to {args.to_rock}...")
    moved = 0
    for t in tasks:
        result = move_task(args.base, t["id"], args.to_rock, config)
        task_name = result.get("fields", {}).get(base_cfg["task_field"], t["id"])
        print(f"  ✓ {task_name[:70]}")
        moved += 1

    print(f"\nDone — {moved} task(s) rolled.")

    # Output JSON summary for scripting
    summary = {
        "base": args.base,
        "from_rock": args.from_rock,
        "to_rock": args.to_rock,
        "tasks_moved": moved,
        "tasks": [
            {"id": t["id"], "task": t["task"], "status": t["status"]} for t in tasks
        ],
    }
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
