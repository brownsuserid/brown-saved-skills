#!/usr/bin/env python3
"""
Query projects from an Airtable base.

Usage:
    python3 query_projects.py --base [personal|aitb|bb] [--all] [--config path/to/config.yaml]

Output:
    JSON array of projects with name, status, linked goals, and IDs.

Field mapping per base:
    Personal: name = "Project", description = "Definition of Done", goals = "1yr Goals"
    AITB:     name = "Project Name", description = "Definition of Done"
    BB:       name = "Name", description = "Project Overview"
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402


def fetch_projects(base_key, config, include_all=False):
    """Fetch projects from Airtable base. Filters to active by default."""
    proj_cfg = config["bases"].get(base_key, {}).get("projects")
    if not proj_cfg:
        print(f"Error: Unknown base '{base_key}'", file=sys.stderr)
        sys.exit(1)

    encoded_table = urllib.parse.quote(proj_cfg["table"])
    base_url = f"https://api.airtable.com/v0/{proj_cfg['base_id']}/{encoded_table}"

    params = {}

    if not include_all:
        conditions = [f"Status!='{s}'" for s in proj_cfg["done_statuses"]]
        if len(conditions) == 1:
            params["filterByFormula"] = conditions[0]
        else:
            params["filterByFormula"] = f"AND({','.join(conditions)})"

    params["sort[0][field]"] = proj_cfg["name_field"]
    params["sort[0][direction]"] = "asc"

    projects = []
    offset = None

    while True:
        page_params = dict(params)
        if offset:
            page_params["offset"] = offset

        url = base_url + "?" + urllib.parse.urlencode(page_params)
        req = urllib.request.Request(url, headers=airtable_config.api_headers())

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())

                for record in data.get("records", []):
                    fields = record.get("fields", {})
                    project = {
                        "id": record.get("id"),
                        "name": fields.get(proj_cfg["name_field"]),
                        "status": fields.get("Status"),
                        "description": fields.get(proj_cfg["description_field"], ""),
                    }
                    if proj_cfg["goals_field"]:
                        project["linked_goals"] = fields.get(
                            proj_cfg["goals_field"], []
                        )
                    if proj_cfg["notes_field"]:
                        project["notes"] = fields.get(proj_cfg["notes_field"], "")
                    if proj_cfg.get("for_this_week_field"):
                        project["for_this_week"] = bool(
                            fields.get(proj_cfg["for_this_week_field"], False)
                        )

                    projects.append(project)

                offset = data.get("offset")
                if not offset:
                    break

        except urllib.error.HTTPError as e:
            print(f"Error fetching projects: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    return projects


def main():
    parser = argparse.ArgumentParser(description="Query projects from Airtable")
    parser.add_argument(
        "--base",
        required=True,
        choices=["personal", "aitb", "bb"],
        help="Which base to query",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include completed/archived projects (default: active only)",
    )
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    projects = fetch_projects(args.base, config, include_all=args.all)
    print(json.dumps(projects, indent=2))


if __name__ == "__main__":
    main()
