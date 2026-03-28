#!/usr/bin/env python3
"""
Project Quality Audit

Checks all incomplete projects across all 3 Airtable bases for:
1. No tasks (skips Backlog projects)
2. No definition of done
3. No mountain/goal linkage
4. No driver/assignee
5. All tasks completed but project still open (shows DoD + task titles)
6. All tasks blocked
7. No active (incomplete) tasks remaining

Usage:
  python3 audit_projects.py [--base personal|aitb|bb|all] [--driver aaron] [--json]
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))
from _config import BASES, api_headers, api_url  # noqa: E402

# Known Backlog mountain/goal IDs (created during project audit)
BACKLOG_IDS = {
    "personal": "recyqwgSQITGlup71",
    "aitb": "recCkDMa46Antmy27",
    "bb": "recafT1yDUOyWdeEC",
}


def fetch_all(base_id, table, fields, formula=None):
    """Fetch all records from an Airtable table, handling pagination."""
    records = []
    offset = None
    while True:
        params = [("fields[]", f) for f in fields]
        if formula:
            params.append(("filterByFormula", formula))
        if offset:
            params.append(("offset", offset))
        url = f"{api_url(base_id, table)}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=api_headers())
        resp = json.loads(urllib.request.urlopen(req).read())
        records.extend(resp.get("records", []))
        offset = resp.get("offset")
        if not offset:
            break
    return records


def is_backlog_project(fields, mountain_field, goals_field, base_key):
    """Check if a project is linked to the Backlog mountain/goal."""
    backlog_id = BACKLOG_IDS.get(base_key)
    if not backlog_id:
        return False
    if mountain_field:
        linked = fields.get(mountain_field, [])
        if backlog_id in linked:
            return True
    if goals_field:
        linked = fields.get(goals_field, [])
        if backlog_id in linked:
            return True
    return False


def audit_base(base_key, driver_filter=None):
    """Run all quality checks for a single base."""
    cfg = BASES[base_key]
    base_id = cfg["base_id"]
    project_table = cfg["project_table"]
    name_field = cfg["project_name_field"]
    dod_field = cfg["project_description_field"]
    status_field = cfg["project_status_field"]
    driver_field = cfg.get("project_driver_field")
    mountain_field = cfg.get("project_mountain_field")
    goals_field = cfg.get("project_goals_field")
    done_statuses = list(set(cfg["done_statuses"] + ["Complete", "Completed"]))
    inbox_id = cfg.get("inbox_project_id")

    # Exclude done projects
    done_conditions = ",".join(f'Status="{s}"' for s in done_statuses)
    formula = f"NOT(OR({done_conditions}))"

    # Fetch projects
    fields = [name_field, dod_field, status_field, "Tasks"]
    if driver_field:
        fields.append(driver_field)
    if mountain_field:
        fields.append(mountain_field)
    if goals_field:
        fields.append(goals_field)

    projects = fetch_all(base_id, project_table, fields, formula)

    # Fetch all tasks to check statuses per project
    task_fields = [cfg["task_field"], cfg["status_field"], cfg["project_field"]]
    all_tasks = fetch_all(base_id, cfg["tasks_table_name"], task_fields)

    # Build task lookup by project record ID
    tasks_by_project = {}
    for t in all_tasks:
        proj_ids = t["fields"].get(cfg["project_field"], [])
        if isinstance(proj_ids, list):
            for pid in proj_ids:
                tasks_by_project.setdefault(pid, []).append(t)
        elif proj_ids:
            tasks_by_project.setdefault(proj_ids, []).append(t)

    issues = []

    for proj in projects:
        f = proj["fields"]
        name = f.get(name_field, "(unnamed)")
        proj_id = proj["id"]
        status = f.get(status_field, "")
        proj_tasks = tasks_by_project.get(proj_id, [])
        task_statuses = [t["fields"].get(cfg["status_field"], "") for t in proj_tasks]
        in_backlog = is_backlog_project(f, mountain_field, goals_field, base_key)

        # Skip inbox project
        if proj_id == inbox_id:
            continue

        # Filter by driver if specified (skip projects driven by others)
        if driver_filter and driver_field:
            drivers = f.get(driver_field, [])
            if drivers and driver_filter not in drivers:
                continue

        proj_issues = []

        # 1. No tasks (skip Backlog projects, they're uncommitted)
        if not proj_tasks and not in_backlog:
            proj_issues.append(
                {
                    "issue": "no_tasks",
                    "detail": "Project has no tasks",
                    "severity": "error",
                }
            )

        # 2. No definition of done
        dod = f.get(dod_field, "")
        if not dod or not dod.strip():
            proj_issues.append(
                {
                    "issue": "no_definition_of_done",
                    "detail": "Missing Definition of Done",
                    "severity": "error",
                }
            )

        # 3. No mountain/goal linkage
        has_hierarchy = False
        if mountain_field and f.get(mountain_field):
            has_hierarchy = True
        if goals_field and f.get(goals_field):
            has_hierarchy = True
        if not has_hierarchy:
            link_type = "mountain" if mountain_field else "goal"
            proj_issues.append(
                {
                    "issue": "no_hierarchy",
                    "detail": f"Not linked to any {link_type}",
                    "severity": "warning",
                }
            )

        # 4. No driver/assignee
        if driver_field and not f.get(driver_field):
            proj_issues.append(
                {
                    "issue": "no_driver",
                    "detail": "No driver assigned",
                    "severity": "warning",
                }
            )

        # 5-7. Task status analysis
        if proj_tasks:
            incomplete = [s for s in task_statuses if s not in done_statuses]
            completed = [s for s in task_statuses if s in done_statuses]

            # 5. All tasks done but project open
            if not incomplete and completed:
                # Include DoD and task titles for review
                task_names = [
                    t["fields"].get(cfg["task_field"], "?") for t in proj_tasks
                ]
                dod_text = (dod[:120] + "...") if len(dod) > 120 else dod
                proj_issues.append(
                    {
                        "issue": "all_tasks_done",
                        "detail": (
                            f"All {len(completed)} tasks done, project still "
                            f"open ({status})"
                        ),
                        "dod": dod_text or "(no DoD)",
                        "completed_tasks": task_names,
                        "severity": "warning",
                    }
                )

            # 6. All incomplete tasks are blocked
            elif incomplete and all(s == "Blocked" for s in incomplete):
                proj_issues.append(
                    {
                        "issue": "all_blocked",
                        "detail": (f"All {len(incomplete)} active tasks are blocked"),
                        "severity": "error",
                    }
                )

            # 7. No actionable next step
            actionable = [s for s in incomplete if s != "Blocked"]
            if incomplete and not actionable:
                proj_issues.append(
                    {
                        "issue": "no_actionable_tasks",
                        "detail": "No actionable tasks (all blocked or done)",
                        "severity": "error",
                    }
                )

        for pi in proj_issues:
            pi["project"] = name
            pi["project_id"] = proj_id
            pi["base"] = base_key
            pi["status"] = status
            issues.append(pi)

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Audit project quality across Airtable bases"
    )
    parser.add_argument(
        "--base", choices=["personal", "aitb", "bb", "all"], default="all"
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument(
        "--driver",
        default="aaron",
        help="Filter to projects driven by this person (default: aaron). "
        "Use 'all' for no filter.",
    )
    args = parser.parse_args()

    # Resolve driver name to record IDs per base
    driver_ids = {}
    if args.driver and args.driver.lower() != "all":
        from _config import PEOPLE

        lower = args.driver.lower()
        if lower in PEOPLE:
            driver_ids = PEOPLE[lower]
        elif args.driver.startswith("rec"):
            driver_ids = {b: args.driver for b in ["personal", "aitb", "bb"]}

    bases = ["personal", "aitb", "bb"] if args.base == "all" else [args.base]
    all_issues = []

    for base_key in bases:
        driver_id = driver_ids.get(base_key)
        all_issues.extend(audit_base(base_key, driver_filter=driver_id))

    if args.json:
        print(json.dumps(all_issues, indent=2))
        return

    # Group by issue type, ordered by triage priority
    ISSUE_ORDER = [
        (
            "no_hierarchy",
            "NO MOUNTAIN/GOAL LINKAGE",
            "Every project must be linked to a Mountain (30d) or Goal (1yr). "
            "Ask: is this project committed for THIS month? If yes, link it "
            "to the appropriate active mountain. If not, link it to the "
            "'Backlog' mountain/goal. Projects in Backlog get reviewed "
            "during monthly planning and promoted when committed.",
        ),
        (
            "no_definition_of_done",
            "MISSING DEFINITION OF DONE",
            "Write a concrete, verifiable Definition of Done for each "
            "project. It should answer: what does 'finished' look like? "
            "Use measurable outcomes, not vague aspirations.",
        ),
        (
            "no_tasks",
            "NO TASKS (excluding Backlog)",
            "Create 1-3 concrete next actions for each project. "
            "Every active project needs at least one task to move it "
            "forward. If the project has no clear next step, it may "
            "need to be archived or redefined. "
            "Backlog projects are excluded from this check.",
        ),
        (
            "no_driver",
            "NO DRIVER ASSIGNED",
            "Assign a driver (owner) to each project. The driver is "
            "accountable for progress, not necessarily doing all the work.",
        ),
        (
            "all_blocked",
            "ALL TASKS BLOCKED",
            "Investigate what is blocking each task. Unblock at least one "
            "task, escalate the blocker, or redefine the approach. A fully "
            "blocked project is a stalled project.",
        ),
        (
            "no_actionable_tasks",
            "NO ACTIONABLE TASKS",
            "All remaining tasks are blocked or done. Create a new "
            "actionable task or unblock an existing one so the project "
            "can move forward.",
        ),
        (
            "all_tasks_done",
            "ALL TASKS DONE BUT PROJECT OPEN",
            "Review the Definition of Done against completed tasks below. "
            "If the DoD is clearly met, mark the project Complete. "
            "If not, create the remaining tasks needed to finish.",
        ),
    ]

    total_errors = 0
    total_warnings = 0

    for issue_key, title, guidance in ISSUE_ORDER:
        matching = [i for i in all_issues if i["issue"] == issue_key]
        if not matching:
            continue

        severity = matching[0]["severity"]
        label = "ERROR" if severity == "error" else "WARNING"
        if severity == "error":
            total_errors += len(matching)
        else:
            total_warnings += len(matching)

        print(f"\n{'=' * 60}")
        print(f"{label}: {title} ({len(matching)})")
        print(f"{'=' * 60}")
        print(f"  {guidance}")
        print()
        for i in matching:
            base = i.get("base", "").upper()
            print(f"  [{base}] {i['project']} ({i['status']})")

            # For all_tasks_done, show DoD and completed tasks
            if issue_key == "all_tasks_done":
                print(f"    DoD: {i.get('dod', '?')}")
                tasks = i.get("completed_tasks", [])
                for t in tasks[:8]:
                    print(f"      - {t}")
                if len(tasks) > 8:
                    print(f"      ... and {len(tasks) - 8} more")
                print()

    if not all_issues:
        print("\nAll projects pass quality checks.")
    else:
        print(
            f"\nTotal: {total_errors} errors, {total_warnings} warnings "
            f"across {len(bases)} base(s)"
        )


if __name__ == "__main__":
    main()
