#!/usr/bin/env python3
"""
Fetch top tasks and blocked-on-Aaron tasks from all Airtable bases.

Reuses executing-tasks infrastructure (search_tasks, get_task).

Usage:
    python3 gather_top_tasks.py --assignee aaron --max 10 [--config path/to/config.yaml]

Output:
    JSON with top_tasks, blocked_on_aaron, blocked_by_dependencies, and all_blocked arrays.
"""

import argparse
import json
import os
import re
import sys

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


def annotate_dependency_status(tasks: list) -> list:
    """Annotate tasks with dependency completion info using Airtable-computed fields.

    Reads the "Is Blocked" formula and "Dependency Status" rollup fields
    that are already populated by Airtable, avoiding extra API calls.

    Adds to each task:
    - dependencies_complete: bool (True if all dependencies are Completed or no deps)
    - blocked_by: list of dependency record IDs (when is_blocked is True)
    """
    for task in tasks:
        is_blocked = task.get("is_blocked", False)
        deps = task.get("depends_on", [])

        if not deps:
            task["dependencies_complete"] = True
            task["blocked_by"] = []
        elif is_blocked:
            task["dependencies_complete"] = False
            task["blocked_by"] = deps
        else:
            task["dependencies_complete"] = True
            task["blocked_by"] = []

    return tasks


def fetch_top_tasks(
    assignee: str, max_results: int, config: dict, exclude_incomplete_deps: bool = True
) -> list:
    """Fetch top actionable tasks across all bases for an assignee, sorted by score.

    Excludes blocked, human_review, and validating tasks (not actionable by assignee).
    Optionally excludes tasks with incomplete dependencies.
    """
    bases = airtable_config.get_bases(config)
    all_tasks = []
    for base_key in bases:
        assignee_id = resolve_assignee_id(config, assignee, base_key)
        formula = build_filter(
            config, base_key, status=None, query=None, include_done=False
        )
        # Exclude statuses that are not actionable by the assignee
        sv = bases[base_key]["status_values"]
        exclusions = []
        for status_key in ("blocked", "human_review", "validating"):
            if status_key in sv:
                exclusions.append(f"{{Status}}!='{sv[status_key]}'")
        exclusion_formula = ",".join(exclusions)
        if formula:
            formula = f"AND({formula},{exclusion_formula})"
        else:
            formula = f"AND({exclusion_formula})"
        tasks = search_base(config, base_key, formula, max_results, assignee_id)
        all_tasks.extend(tasks)

    # Defense-in-depth: also filter locally in case Airtable returns stale data
    excluded_statuses = set()
    for bk in bases:
        sv = bases[bk]["status_values"]
        for key in ("blocked", "human_review", "validating"):
            if key in sv:
                excluded_statuses.add(sv[key])
    all_tasks = [t for t in all_tasks if t.get("status") not in excluded_statuses]

    # Annotate with dependency status
    all_tasks = annotate_dependency_status(all_tasks)

    # Optionally filter out tasks with incomplete dependencies
    if exclude_incomplete_deps:
        all_tasks = [t for t in all_tasks if t.get("dependencies_complete", True)]

    all_tasks.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return all_tasks[:max_results]


def fetch_tasks_with_incomplete_deps(
    assignee: str, config: dict, max_results: int = 50
) -> list:
    """Fetch tasks that have incomplete dependencies (blocked by dependencies)."""
    bases = airtable_config.get_bases(config)
    all_tasks = []
    for base_key in bases:
        assignee_id = resolve_assignee_id(config, assignee, base_key)
        formula = build_filter(
            config, base_key, status=None, query=None, include_done=False
        )
        sv = bases[base_key]["status_values"]
        exclusions = []
        for status_key in ("blocked", "human_review", "validating", "complete"):
            if status_key in sv:
                exclusions.append(f"{{Status}}!='{sv[status_key]}'")
        if formula:
            formula = f"AND({formula},{','.join(exclusions)})"
        else:
            formula = f"AND({','.join(exclusions)})"
        tasks = search_base(config, base_key, formula, max_results, assignee_id)
        all_tasks.extend(tasks)

    # Annotate with dependency status
    all_tasks = annotate_dependency_status(all_tasks)

    # Filter to only tasks with incomplete dependencies
    blocked_by_deps = [t for t in all_tasks if not t.get("dependencies_complete", True)]

    blocked_by_deps.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return blocked_by_deps


def fetch_all_blocked(config: dict) -> list:
    """Fetch all blocked tasks across all bases (no assignee filter)."""
    bases = airtable_config.get_bases(config)
    all_blocked = []
    for base_key in bases:
        formula = build_filter(
            config, base_key, status="blocked", query=None, include_done=False
        )
        tasks = search_base(
            config, base_key, formula, max_records=100, assignee_id=None
        )
        all_blocked.extend(tasks)

    all_blocked = annotate_dependency_status(all_blocked)
    all_blocked.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return all_blocked


def fetch_all_human_review(config: dict, assignees: list[str] | None = None) -> list:
    """Fetch Human Review tasks across all bases.

    Args:
        config: Loaded YAML config dict.
        assignees: If provided, only include tasks assigned to these people
                   (e.g. ["aaron", "pablo", "juan"]). None returns all.
    """
    bases = airtable_config.get_bases(config)
    review_tasks = []
    for base_key in bases:
        sv = bases[base_key]["status_values"]
        if "human_review" not in sv:
            continue
        formula = build_filter(
            config, base_key, status="human_review", query=None, include_done=False
        )
        if assignees:
            # Fetch for each assignee separately to use Airtable-side filtering
            for name in assignees:
                assignee_id = resolve_assignee_id(config, name, base_key)
                if assignee_id:
                    tasks = search_base(
                        config,
                        base_key,
                        formula,
                        max_records=100,
                        assignee_id=assignee_id,
                    )
                    review_tasks.extend(tasks)
        else:
            tasks = search_base(
                config, base_key, formula, max_records=100, assignee_id=None
            )
            review_tasks.extend(tasks)

    review_tasks = annotate_dependency_status(review_tasks)

    # Deduplicate in case same task matched multiple assignees
    seen: set[str] = set()
    deduped = []
    for t in review_tasks:
        if t["id"] not in seen:
            seen.add(t["id"])
            deduped.append(t)

    deduped.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return deduped


def fetch_blocked_for_assignee(assignee: str, config: dict) -> list:
    """Fetch all blocked tasks assigned to a specific person across all bases."""
    bases = airtable_config.get_bases(config)
    blocked = []
    for base_key in bases:
        assignee_id = resolve_assignee_id(config, assignee, base_key)
        if not assignee_id:
            continue
        formula = build_filter(
            config, base_key, status="blocked", query=None, include_done=False
        )
        tasks = search_base(
            config, base_key, formula, max_records=100, assignee_id=assignee_id
        )
        blocked.extend(tasks)

    blocked = annotate_dependency_status(blocked)
    blocked.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return blocked


def filter_blocked_on_person(tasks: list, person: str) -> list:
    """Filter tasks whose Notes field mentions a person (case-insensitive word match)."""
    pattern = re.compile(rf"\b{re.escape(person)}\b", re.IGNORECASE)
    return [t for t in tasks if pattern.search(t.get("notes", ""))]


def merge_and_deduplicate(*task_lists: list) -> list:
    """Merge multiple task lists and deduplicate by task ID."""
    seen: set[str] = set()
    merged = []
    for tasks in task_lists:
        for task in tasks:
            if task["id"] not in seen:
                seen.add(task["id"])
                merged.append(task)
    merged.sort(key=lambda t: t.get("score") or 0, reverse=True)
    return merged


def main():
    from search_tasks import resolve_hierarchy  # noqa: E402

    parser = argparse.ArgumentParser(description="Gather tasks for morning briefing")
    parser.add_argument(
        "--assignee",
        default="aaron",
        help="Assignee name for top tasks (default: aaron)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Max top tasks to return (default: 10)",
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
    parser.add_argument(
        "--include-deps-in-top",
        action="store_true",
        dest="include_deps_in_top",
        help="Include tasks with incomplete dependencies in top_tasks (default: exclude them)",
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)

    # Fetch top tasks (excluding incomplete dependencies by default)
    top_tasks = fetch_top_tasks(
        args.assignee,
        args.max,
        config,
        exclude_incomplete_deps=not args.include_deps_in_top,
    )

    # Fetch tasks blocked by incomplete dependencies
    blocked_by_dependencies = fetch_tasks_with_incomplete_deps(args.assignee, config)

    all_blocked = fetch_all_blocked(config)
    blocked_on_person = filter_blocked_on_person(all_blocked, args.assignee)

    # Also fetch all of Pablo's blocked tasks (all depend on Aaron)
    pablo_blocked = fetch_blocked_for_assignee("pablo", config)

    # Fetch Human Review tasks only for aaron, pablo, and juan
    human_review_tasks = fetch_all_human_review(
        config, assignees=["aaron", "pablo", "juan"]
    )

    # Merge notes-mention blocked, Pablo's blocked, and human review tasks
    blocked_on_aaron = merge_and_deduplicate(
        blocked_on_person, pablo_blocked, human_review_tasks
    )

    # Resolve hierarchy: rocks always included, mountains by default
    include_mountains = not args.no_mountains
    all_task_lists = (
        top_tasks + blocked_on_aaron + all_blocked + blocked_by_dependencies
    )
    resolve_hierarchy(
        config,
        all_task_lists,
        include_mountains=include_mountains,
        include_goals=args.include_goals,
    )

    result = {
        "top_tasks": top_tasks,
        "blocked_on_aaron": blocked_on_aaron,
        "blocked_by_dependencies": blocked_by_dependencies,
        "all_blocked": all_blocked,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
