#!/usr/bin/env python3
"""
Gather product roadmap context from BB Airtable base.

Queries the BB Product Roadmap table for features matching a search query.
Used during PR-FAQ drafting to pull roadmap context.

Usage:
    python3 gather_roadmap_context.py --query "AI Teammates" [--max 10] [--config path/to/config.yaml]

Output:
    JSON array of roadmap items with Feature, Status, Priority,
    Definition of Done, Notes, Product, and Dependencies.
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

ROADMAP_FIELDS = [
    "Feature",
    "Status",
    "Priority",
    "Definition of Done",
    "Notes",
    "Product",
    "Dependencies",
]


def build_filter(query: str) -> str:
    """Build an Airtable filterByFormula for roadmap search."""
    safe_query = query.replace("'", "\\'")
    return (
        f"OR(FIND(LOWER('{safe_query}'), LOWER({{Feature}})), "
        f"FIND(LOWER('{safe_query}'), LOWER({{Notes}})))"
    )


def search_roadmap(query: str, max_records: int, config: dict) -> list[dict]:
    """Query the BB Product Roadmap table and return matching items."""
    bb_cfg = airtable_config.get_base(config, "bb")
    roadmap_table_id = bb_cfg["roadmap_table_id"]
    base_url = f"https://api.airtable.com/v0/{bb_cfg['base_id']}/{roadmap_table_id}"

    params: dict[str, str] = {"maxRecords": str(max_records)}

    if query:
        params["filterByFormula"] = build_filter(query)

    for i, field in enumerate(ROADMAP_FIELDS):
        params[f"fields[{i}]"] = field

    url = base_url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=airtable_config.api_headers())

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Warning: Error querying roadmap: {e.read().decode()}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Error querying roadmap: {e}", file=sys.stderr)
        return []

    items = []
    for record in data.get("records", []):
        fields = record.get("fields", {})
        items.append(
            {
                "id": record["id"],
                "feature": fields.get("Feature", ""),
                "status": fields.get("Status", ""),
                "priority": fields.get("Priority", ""),
                "definition_of_done": fields.get("Definition of Done", ""),
                "notes": fields.get("Notes", ""),
                "product": fields.get("Product", ""),
                "dependencies": fields.get("Dependencies", ""),
                "airtable_url": airtable_config.airtable_record_url(
                    bb_cfg["base_id"], roadmap_table_id, record["id"]
                ),
            }
        )

    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search BB Product Roadmap in Airtable"
    )
    parser.add_argument(
        "--query", required=True, help="Text to search in Feature and Notes fields"
    )
    parser.add_argument(
        "--max", type=int, default=10, help="Maximum results (default: 10)"
    )
    parser.add_argument("--config", help="Path to YAML config file")

    args = parser.parse_args()
    config = airtable_config.load_config(args.config)
    items = search_roadmap(args.query, args.max, config)
    print(json.dumps(items, indent=2))


if __name__ == "__main__":
    main()
