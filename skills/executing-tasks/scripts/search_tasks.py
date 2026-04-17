#!/usr/bin/env python3
"""
Search and filter tasks across Airtable bases.

Usage:
    python3 search_tasks.py --base [personal|aitb|bb|all] \
        [--assignee pablo|aaron] \
        [--status "In Progress"] \
        [--query "search text"] \
        [--max 20] \
        [--include-done] \
        [--title-only]
        [--config path/to/config.yaml]

Output:
    JSON array of task summaries sorted by Score descending.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Import shared Airtable config
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)
from airtable_config import (  # noqa: E402
    api_headers,
    airtable_record_url,
    get_base,
    get_bases,
    get_people,
    load_config,
    resolve_config_path,
)


def _hitl_action_hint(hitl_status: str, hitl_brief: str, task_status: str) -> str:
    """Return an action hint based on HITL status to guide the calling agent."""
    if hitl_status == "Response Submitted":
        return "EXECUTE NOW: Aaron approved. Run --phase pick-up, then execute the plan, then --phase work-done."
    if hitl_status == "Processed" and hitl_brief:
        # Plan is written but Aaron has NOT yet approved it. Do NOT execute.
        return "WAIT_APPROVAL: Plan is written and awaiting Aaron's approval. Do NOT execute. Aaron must set HITL Status='Response Submitted' to approve."
    if hitl_status == "Pending Review":
        return "SKIP: Waiting for Aaron's review. Do not work on this task."
    if hitl_status == "Completed":
        return "SKIP: HITL cycle complete. Aaron will set Status=Completed."
    if not hitl_status and not hitl_brief:
        return "PLAN: No plan yet. Write plan to HITL Brief, then --phase plan-ready."
    return ""


def resolve_assignee_id(config: dict, assignee: str, base_key: str) -> str | None:
    """Resolve assignee name to record ID for local filtering."""
    if not assignee:
        return None
    people = get_people(config)
    assignee_lower = assignee.lower()
    if assignee_lower in people and base_key in people[assignee_lower]:
        return people[assignee_lower][base_key]
    if assignee.startswith("rec"):
        return assignee
    return None


def build_filter(
    config: dict,
    base_key: str,
    status: str | None,
    query: str | None,
    include_done: bool,
    title_only: bool = False,
) -> str:
    """Build an Airtable filterByFormula string.

    Note: Assignee filtering is done locally after fetch because
    ARRAYJOIN on linked records returns display names, not record IDs.
    """
    base_cfg = get_base(config, base_key)
    conditions = []

    if status:
        mapping = base_cfg["status_values"]
        status_list = [s.strip() for s in status.split(",")]
        status_conditions = []
        for s in status_list:
            actual_status = mapping.get(s, s)
            status_conditions.append(f"{{Status}}='{actual_status}'")
        if len(status_conditions) == 1:
            conditions.append(status_conditions[0])
        else:
            conditions.append(f"OR({','.join(status_conditions)})")

    if query:
        safe_query = query.replace("'", "\\'").replace(":", "")
        if title_only:
            conditions.append(
                f"FIND(LOWER('{safe_query}'), SUBSTITUTE(LOWER({{Task}}), ':', ''))"
            )
        else:
            desc_field = base_cfg["description_field"]
            notes_field = base_cfg["notes_field"]
            conditions.append(
                f"OR(FIND(LOWER('{safe_query}'), SUBSTITUTE(LOWER({{Task}}), ':', '')), "
                f"FIND(LOWER('{safe_query}'), SUBSTITUTE(LOWER({{{desc_field}}}), ':', '')), "
                f"FIND(LOWER('{safe_query}'), SUBSTITUTE(LOWER({{{notes_field}}}), ':', '')))"
            )

    if not include_done:
        done_conditions = [f"{{Status}}!='{s}'" for s in base_cfg["done_statuses"]]
        conditions.extend(done_conditions)

    if not conditions:
        return ""
    if len(conditions) == 1:
        return conditions[0]
    return f"AND({','.join(conditions)})"


def search_base(
    config: dict,
    base_key: str,
    formula: str,
    max_records: int,
    assignee_id: str | None,
) -> list:
    """Query a single base and return task summaries."""
    base_cfg = get_base(config, base_key)
    base_url = f"https://api.airtable.com/v0/{base_cfg['base_id']}/{base_cfg['tasks_table_id']}"

    # Fetch more records than needed if filtering locally by assignee
    fetch_limit = max_records * 10 if assignee_id else max_records

    base_params = {}
    if formula:
        base_params["filterByFormula"] = formula
    base_params["sort[0][field]"] = base_cfg["score_field"]
    base_params["sort[0][direction]"] = "desc"
    base_params["pageSize"] = "100"

    all_records: list = []
    offset: str | None = None
    while len(all_records) < fetch_limit:
        params = dict(base_params)
        if offset:
            params["offset"] = offset
        url = base_url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=api_headers())
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(
                f"Warning: Error querying {base_key}: {e.read().decode()}",
                file=sys.stderr,
            )
            return []
        except Exception as e:
            print(f"Warning: Error querying {base_key}: {e}", file=sys.stderr)
            return []
        all_records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break

    tasks = []
    for record in all_records:
        fields = record.get("fields", {})

        # Local assignee filtering -- check if the record ID is in the Assignee array
        if assignee_id:
            assignees = fields.get(base_cfg["assignee_field"], [])
            if assignee_id not in assignees:
                continue

        task_data = {
            "id": record["id"],
            "task": fields.get(base_cfg["task_field"], ""),
            "description": fields.get(base_cfg["description_field"], ""),
            "status": fields.get(base_cfg["status_field"], ""),
            "score": fields.get(base_cfg["score_field"], ""),
            "due_date": fields.get(base_cfg["due_date_field"], ""),
            "notes": fields.get(base_cfg["notes_field"], ""),
            "base": base_key,
            "project_ids": fields.get(base_cfg["project_field"], []),
            "airtable_url": airtable_record_url(
                base_cfg["base_id"], base_cfg["tasks_table_id"], record["id"]
            ),
        }

        # Include dependency fields
        depends_on_field = config.get("depends_on_field")
        if depends_on_field:
            task_data["depends_on"] = fields.get(depends_on_field, [])
        is_blocked_field = config.get("is_blocked_field")
        if is_blocked_field:
            task_data["is_blocked"] = fields.get(is_blocked_field, False)
        deps_count_field = config.get("dependencies_count_field")
        if deps_count_field:
            task_data["dependencies_count"] = fields.get(deps_count_field, 0)
        dep_status_field = config.get("dependency_status_field")
        if dep_status_field:
            task_data["dependency_status"] = fields.get(dep_status_field, "")

        # Include HITL fields if present
        hitl_brief_field = base_cfg.get("hitl_brief_field")
        if hitl_brief_field:
            hitl_status = fields.get(base_cfg.get("hitl_status_field", ""), "")
            hitl_brief = fields.get(hitl_brief_field, "")
            task_data["hitl_brief"] = hitl_brief
            task_data["hitl_response"] = fields.get(
                base_cfg.get("hitl_response_field", ""), ""
            )
            task_data["hitl_status"] = hitl_status
            task_data["task_output"] = fields.get(
                base_cfg.get("task_output_field", ""), ""
            )
            # Action hint: tell the calling agent what to do next
            task_data["action"] = _hitl_action_hint(
                hitl_status, hitl_brief, task_data["status"]
            )

        tasks.append(task_data)
        if len(tasks) >= max_records:
            break

    return tasks


def _fetch_record(base_id: str, table_id: str, record_id: str) -> dict | None:
    """Fetch a single Airtable record by ID. table_id can be a name or ID."""
    encoded_table = urllib.parse.quote(table_id)
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Warning: Could not fetch {table_id}/{record_id}: {e}", file=sys.stderr)
        return None


def resolve_hierarchy(
    config: dict,
    tasks: list,
    include_mountains: bool = True,
    include_goals: bool = False,
) -> list:
    """Annotate tasks with project_name, mountain_name, goal_name by resolving linked records.

    Batches API calls: one per unique project, mountain, goal record.
    Uses caching to avoid duplicate fetches across tasks.
    """
    bases = get_bases(config)

    # Cache: record_id -> resolved data
    project_cache: dict[str, dict] = {}
    mountain_cache: dict[str, dict] = {}
    goal_cache: dict[str, dict] = {}

    for task in tasks:
        base_key = task.get("base")
        if not base_key or base_key not in bases:
            continue
        base_cfg = bases[base_key]

        # Resolve project/rock
        project_ids = task.get("project_ids", [])
        if not project_ids:
            continue

        project_id = project_ids[0]
        if project_id not in project_cache:
            record = _fetch_record(
                base_cfg["base_id"], base_cfg["project_table"], project_id
            )
            if record:
                fields = record.get("fields", {})
                project_cache[project_id] = {
                    "name": fields.get(base_cfg["project_name_field"], ""),
                    "mountain_ids": fields.get(
                        base_cfg.get("project_mountain_field", ""), []
                    ),
                }
            else:
                project_cache[project_id] = {"name": "", "mountain_ids": []}

        project_data = project_cache[project_id]
        task["project_name"] = project_data["name"]

        if not include_mountains:
            continue

        # Resolve mountain
        mountain_ids = project_data.get("mountain_ids", [])
        if not mountain_ids:
            continue

        mountain_id = mountain_ids[0]
        if mountain_id not in mountain_cache:
            mountain_table_id = base_cfg.get("mountain_table_id", "")
            if mountain_table_id:
                record = _fetch_record(
                    base_cfg["base_id"], mountain_table_id, mountain_id
                )
                if record:
                    fields = record.get("fields", {})
                    mountain_cache[mountain_id] = {
                        "name": fields.get(
                            base_cfg.get("mountain_name_field", "Title"), ""
                        ),
                        "goal_ids": fields.get(
                            base_cfg.get("mountain_goal_field", ""), []
                        ),
                    }
                else:
                    mountain_cache[mountain_id] = {"name": "", "goal_ids": []}
            else:
                mountain_cache[mountain_id] = {"name": "", "goal_ids": []}

        mountain_data = mountain_cache[mountain_id]
        task["mountain_name"] = mountain_data["name"]

        if not include_goals:
            continue

        # Resolve annual goal
        goal_ids = mountain_data.get("goal_ids", [])
        if not goal_ids:
            continue

        goal_id = goal_ids[0]
        if goal_id not in goal_cache:
            goal_table_id = base_cfg.get("mountain_goal_table_id", "")
            if goal_table_id:
                record = _fetch_record(base_cfg["base_id"], goal_table_id, goal_id)
                if record:
                    fields = record.get("fields", {})
                    goal_cache[goal_id] = {
                        "name": fields.get(
                            base_cfg.get("mountain_goal_name_field", "Name"), ""
                        ),
                    }
                else:
                    goal_cache[goal_id] = {"name": ""}
            else:
                goal_cache[goal_id] = {"name": ""}

        task["goal_name"] = goal_cache[goal_id]["name"]

    return tasks


def main():
    parser = argparse.ArgumentParser(description="Search Airtable tasks")
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb", "all"],
        help="Which base to search (or 'all' for all bases)",
    )
    parser.add_argument(
        "--assignee", help="Filter by assignee: pablo, aaron, or record ID"
    )
    parser.add_argument("--status", help="Filter by status (semantic or literal)")
    parser.add_argument("--query", help="Text search in task title and description")
    parser.add_argument(
        "--max", type=int, default=20, help="Maximum results (default: 20)"
    )
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Include completed/cancelled tasks",
    )
    parser.add_argument(
        "--title-only",
        action="store_true",
        dest="title_only",
        help="Search only in task titles (Task field), not description or notes",
    )
    parser.add_argument(
        "--include-rocks",
        action="store_true",
        dest="include_rocks",
        help="Include project/rock names for each task",
    )
    parser.add_argument(
        "--include-mountains",
        action="store_true",
        dest="include_mountains",
        help="Include mountain names (implies --include-rocks)",
    )
    parser.add_argument(
        "--include-goals",
        action="store_true",
        dest="include_goals",
        help="Include annual goal names (implies --include-rocks --include-mountains)",
    )
    parser.add_argument("--config", help="Path to Airtable config YAML")

    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    bases = get_bases(config)

    bases_to_search = list(bases.keys()) if args.base == "all" else [args.base]

    all_tasks = []
    for base_key in bases_to_search:
        assignee_id = (
            resolve_assignee_id(config, args.assignee, base_key)
            if args.assignee
            else None
        )
        formula = build_filter(
            config,
            base_key,
            args.status,
            args.query,
            args.include_done,
            args.title_only,
        )
        tasks = search_base(config, base_key, formula, args.max, assignee_id)
        all_tasks.extend(tasks)

    # Sort by score descending, handle missing scores
    all_tasks.sort(key=lambda t: t.get("score") or 0, reverse=True)

    # Apply max limit across all bases
    all_tasks = all_tasks[: args.max]

    # Resolve hierarchy if requested
    want_rocks = args.include_rocks or args.include_mountains or args.include_goals
    want_mountains = args.include_mountains or args.include_goals
    if want_rocks:
        resolve_hierarchy(
            config,
            all_tasks,
            include_mountains=want_mountains,
            include_goals=args.include_goals,
        )

    print(json.dumps(all_tasks, indent=2))


if __name__ == "__main__":
    main()
