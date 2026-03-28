#!/usr/bin/env python3
"""
Scan tasks for stale follow-up tasks assigned to Aaron.

Identifies tasks with follow-up intent (keywords in task name),
calculates staleness in days, and prioritizes by urgency tier.

Config-driven: reads base IDs, table IDs, and people from YAML config.

Output: JSON to stdout with prioritized list of stale follow-ups.

Usage:
    python3 scan_stale_followups.py
    python3 scan_stale_followups.py --config /path/to/config.yaml
    python3 scan_stale_followups.py --base bb
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import api_headers, airtable_record_url, load_config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FOLLOW_UP_KEYWORDS = [
    "follow up",
    "follow-up",
    "followup",
    "send email",
    "send proposal",
    "send materials",
    "send docs",
    "send demo",
    "send final",
    "send written",
    "send partnership",
    "send whitepaper",
    "reach out",
    "reach-out",
    "schedule call",
    "schedule zoom",
    "schedule meeting",
    "check in",
    "check-in",
    "send to",
    "forward to",
    "pitch ",
]

DONE_STATUSES = {"Completed", "Archived", "Cancelled"}

# Staleness thresholds in days
CRITICAL_DAYS = 14
WARNING_DAYS = 7
WATCH_DAYS = 3


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def fetch_records(
    base_id: str,
    table_id: str,
    headers: dict,
    formula: str | None = None,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch all records from Airtable with pagination."""
    import urllib.parse
    import urllib.request

    records: list[dict[str, Any]] = []
    offset = None

    while True:
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        params: dict[str, Any] = {}
        if formula:
            params["filterByFormula"] = formula
        if offset:
            params["offset"] = offset

        if fields:
            field_params = "&".join(
                f"fields%5B%5D={urllib.parse.quote(f)}" for f in fields
            )
            base_params = urllib.parse.urlencode(params)
            query = "&".join(p for p in [base_params, field_params] if p)
        else:
            query = urllib.parse.urlencode(params)

        full_url = f"{url}?{query}" if query else url
        req = urllib.request.Request(full_url, headers=headers)

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    return records


def lookup_field(
    base_id: str, table_id: str, record_id: str, field_name: str, headers: dict
) -> str | None:
    """Look up a single field value from a record."""
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("fields", {}).get(field_name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def is_followup_task(task_name: str) -> bool:
    """Return True if task name contains follow-up intent keywords."""
    name_lower = task_name.lower()
    return any(kw in name_lower for kw in FOLLOW_UP_KEYWORDS)


def calculate_days_stale(fields: dict[str, Any]) -> int:
    """
    Calculate days a task has been stale.
    Uses deadline if overdue, else days since creation.
    """
    today = date.today()

    deadline_str = fields.get("Deadline")
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str[:10])
            if deadline < today:
                return (today - deadline).days
        except ValueError:
            pass

    created_str = fields.get("Created")
    if created_str:
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00")).date()
            return (today - created).days
        except ValueError:
            pass

    return 0


def classify_priority(days: int) -> str:
    if days >= CRITICAL_DAYS:
        return "critical"
    if days >= WARNING_DAYS:
        return "warning"
    if days >= WATCH_DAYS:
        return "watch"
    return "fresh"


def get_deal_info(
    deal_ids: list[str],
    base_id: str,
    deals_table: str,
    orgs_table: str | None,
    headers: dict,
) -> dict[str, Any]:
    """Fetch name, status, and org for the first linked deal."""
    if not deal_ids:
        return {}

    import urllib.request

    deal_id = deal_ids[0]
    url = f"https://api.airtable.com/v0/{base_id}/{deals_table}/{deal_id}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            deal = json.loads(response.read().decode())
            df = deal.get("fields", {})

            org_ids = df.get("Organization", [])
            org_name = None
            if org_ids and orgs_table:
                org_name = lookup_field(
                    base_id, orgs_table, org_ids[0], "Name", headers
                )

            return {
                "deal_id": deal_id,
                "deal_name": df.get("Name", "Unknown Deal"),
                "deal_status": df.get("Status", "Unknown"),
                "deal_type": df.get("Type", ""),
                "deal_org": org_name or "No Organization",
                "airtable_deal_url": airtable_record_url(base_id, deals_table, deal_id),
            }
    except Exception as exc:
        print(f"Warning: could not fetch deal {deal_id}: {exc}", file=sys.stderr)
        return {"deal_id": deal_id, "deal_name": "Unknown", "deal_status": "Unknown"}


def scan_stale_followups(config: dict, base_key: str = "bb") -> dict[str, Any]:
    """Find and prioritize stale follow-up tasks."""
    headers = api_headers()
    base_cfg = config["bases"][base_key]
    people = config.get("people", {})

    base_id = base_cfg["base_id"]
    tasks_table = base_cfg["tasks_table_id"]
    deals_table = base_cfg.get("deals_table_id")
    orgs_table = base_cfg.get("orgs_table")
    aaron_id = people.get("aaron", {}).get(base_key)

    print(f"Fetching {base_key.upper()} tasks assigned to Aaron...", file=sys.stderr)

    # Fetch all non-done tasks, then filter by assignee client-side.
    formula = (
        "AND("
        "NOT({Status}='Completed'),"
        "NOT({Status}='Archived'),"
        "NOT({Status}='Cancelled')"
        ")"
    )

    all_tasks = fetch_records(
        base_id,
        tasks_table,
        headers,
        formula=formula,
        fields=[
            "Task",
            "Status",
            "Assignee",
            "Deals",
            "Definition of Done",
            "Notes",
            "Created",
            "Deadline",
        ],
    )

    # Filter to Aaron's tasks client-side using record IDs
    tasks = [
        t for t in all_tasks if aaron_id in t.get("fields", {}).get("Assignee", [])
    ]

    print(
        f"Found {len(tasks)} active tasks (of {len(all_tasks)} total), scanning for follow-up intent...",
        file=sys.stderr,
    )

    followups: list[dict[str, Any]] = []
    for task in tasks:
        tf = task.get("fields", {})
        task_name = tf.get("Task", "")

        if not is_followup_task(task_name):
            continue

        days_stale = calculate_days_stale(tf)
        priority = classify_priority(days_stale)

        if priority == "fresh":
            continue

        deal_ids = tf.get("Deals", [])
        deal_info = (
            get_deal_info(deal_ids, base_id, deals_table, orgs_table, headers)
            if deal_ids
            else {}
        )

        followups.append(
            {
                "task_id": task["id"],
                "task_name": task_name,
                "status": tf.get("Status", "Unknown"),
                "priority": priority,
                "days_stale": days_stale,
                "created_date": (tf["Created"][:10] if tf.get("Created") else None),
                "deadline": tf.get("Deadline"),
                "definition_of_done": tf.get("Definition of Done", ""),
                "notes": tf.get("Notes", ""),
                "deal_ids": deal_ids,
                **deal_info,
                "airtable_task_url": airtable_record_url(
                    base_id, tasks_table, task["id"]
                ),
            }
        )

    followups.sort(key=lambda x: x["days_stale"], reverse=True)

    counts = {
        "critical": sum(1 for f in followups if f["priority"] == "critical"),
        "warning": sum(1 for f in followups if f["priority"] == "warning"),
        "watch": sum(1 for f in followups if f["priority"] == "watch"),
    }

    print(
        f"Found {len(followups)} stale follow-ups: "
        f"{counts['critical']} critical, {counts['warning']} warning, "
        f"{counts['watch']} watch",
        file=sys.stderr,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"total": len(followups), **counts},
        "followups": followups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan for stale follow-up tasks assigned to Aaron"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )
    parser.add_argument(
        "--base",
        default="bb",
        help="Base key to scan (default: bb)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    try:
        result = scan_stale_followups(config, base_key=args.base)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
