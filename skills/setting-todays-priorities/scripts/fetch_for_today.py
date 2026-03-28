#!/usr/bin/env python3
"""
Fetch current "For Today" flags and top task recommendations across all Airtable bases.

Reuses executing-tasks infrastructure (search_tasks).

Usage:
    python3 fetch_for_today.py [--assignee aaron] [--max-recommendations 10] [--config path/to/config.yaml]

Output:
    JSON with current_for_today, recommendations, and summary.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Import shared config and executing-tasks helpers
SHARED_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
)
TASK_EXEC_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "executing-tasks",
)
sys.path.insert(0, SHARED_DIR)
sys.path.insert(0, TASK_EXEC_DIR)

import airtable_config  # noqa: E402
from search_tasks import build_filter, resolve_assignee_id, search_base  # noqa: E402


def fetch_for_today_tasks(assignee: str | None, config: dict) -> list:
    """Fetch tasks with For Today=TRUE across all bases, excluding done statuses."""
    bases = airtable_config.get_bases(config)
    all_flagged: list = []
    for base_key, base_cfg in bases.items():
        for_today_field = base_cfg["for_today_field"]
        done_conditions = [f"{{Status}}!='{s}'" for s in base_cfg["done_statuses"]]
        formula_parts = [f"{{{for_today_field}}}=TRUE()"] + done_conditions
        formula = f"AND({','.join(formula_parts)})"

        base_url = f"https://api.airtable.com/v0/{base_cfg['base_id']}/{base_cfg['tasks_table_id']}"
        params: dict[str, str] = {
            "filterByFormula": formula,
            "sort[0][field]": base_cfg["score_field"],
            "sort[0][direction]": "desc",
        }
        url = base_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=airtable_config.api_headers())

        assignee_id = (
            resolve_assignee_id(config, assignee, base_key) if assignee else None
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Error querying {base_key} for For Today: {e.read().decode()}",
                file=sys.stderr,
            )
            continue
        except Exception as e:
            print(
                f"Warning: Error querying {base_key} for For Today: {e}",
                file=sys.stderr,
            )
            continue

        for record in data.get("records", []):
            fields = record.get("fields", {})

            if assignee_id:
                assignees = fields.get(base_cfg["assignee_field"], [])
                if assignee_id not in assignees:
                    continue

            all_flagged.append(
                {
                    "id": record["id"],
                    "task": fields.get(base_cfg["task_field"], ""),
                    "description": fields.get(base_cfg["description_field"], ""),
                    "status": fields.get(base_cfg["status_field"], ""),
                    "score": fields.get(base_cfg["score_field"], ""),
                    "due_date": fields.get(base_cfg["due_date_field"], ""),
                    "notes": fields.get(base_cfg["notes_field"], ""),
                    "base": base_key,
                    "project_ids": fields.get(base_cfg["project_field"], []),
                    "for_today": True,
                    "airtable_url": airtable_config.airtable_record_url(
                        base_cfg["base_id"],
                        base_cfg["tasks_table_id"],
                        record["id"],
                    ),
                }
            )

    all_flagged.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return all_flagged


def fetch_recommendations(
    assignee: str | None, max_results: int, exclude_ids: set[str], config: dict
) -> list:
    """Fetch top actionable tasks by score that are NOT already flagged For Today.

    Excludes blocked tasks -- recommendations should only be actionable items.
    """
    bases = airtable_config.get_bases(config)
    all_tasks: list = []
    for base_key in bases:
        assignee_id = (
            resolve_assignee_id(config, assignee, base_key) if assignee else None
        )
        formula = build_filter(
            config, base_key, status=None, query=None, include_done=False
        )
        # Also exclude blocked tasks -- recommendations should be actionable
        blocked_value = bases[base_key]["status_values"]["blocked"]
        blocked_exclusion = f"{{Status}}!='{blocked_value}'"
        if formula:
            formula = f"AND({formula},{blocked_exclusion})"
        else:
            formula = blocked_exclusion
        tasks = search_base(config, base_key, formula, max_results * 2, assignee_id)
        all_tasks.extend(tasks)

    # Defense-in-depth: also filter locally in case Airtable returns stale data
    blocked_statuses = {bases[bk]["status_values"]["blocked"] for bk in bases}
    all_tasks = [t for t in all_tasks if t.get("status") not in blocked_statuses]

    all_tasks.sort(key=lambda t: t.get("score") or 0, reverse=True)

    recommendations = []
    for task in all_tasks:
        if task["id"] in exclude_ids:
            continue
        recommendations.append({**task, "for_today": False})
        if len(recommendations) >= max_results:
            break

    return recommendations


def main() -> None:
    from search_tasks import resolve_hierarchy  # noqa: E402

    parser = argparse.ArgumentParser(
        description="Fetch For Today flags and recommendations"
    )
    parser.add_argument(
        "--assignee",
        default="aaron",
        help="Filter by assignee (default: aaron)",
    )
    parser.add_argument(
        "--max-recommendations",
        type=int,
        default=10,
        help="Max recommendations to return (default: 10)",
    )
    parser.add_argument(
        "--no-mountains",
        action="store_true",
        dest="no_mountains",
        help="Exclude mountain names from output",
    )
    parser.add_argument(
        "--include-goals",
        action="store_true",
        dest="include_goals",
        help="Include annual goal names",
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)

    current = fetch_for_today_tasks(args.assignee, config)
    flagged_ids = {t["id"] for t in current}
    recommendations = fetch_recommendations(
        args.assignee, args.max_recommendations, flagged_ids, config
    )

    # Resolve hierarchy: rocks always included, mountains by default
    include_mountains = not args.no_mountains
    all_tasks = current + recommendations
    resolve_hierarchy(
        config,
        all_tasks,
        include_mountains=include_mountains,
        include_goals=args.include_goals,
    )

    result = {
        "current_for_today": current,
        "recommendations": recommendations,
        "summary": {
            "currently_flagged": len(current),
            "recommendations_count": len(recommendations),
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
