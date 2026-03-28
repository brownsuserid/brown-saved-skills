#!/usr/bin/env python3
"""
Update fields on an Airtable organization record.

Usage:
    python3 update_org.py --base bb --id recXXX \
        [--name "Acme Corp"] \
        [--industry "Manufacturing"] \
        [--size "51 to 200"] \
        [--description "Widget maker"] \
        [--website "https://acme.com"] \
        [--config /path/to/config.yaml]

Only specified fields are updated (PATCH semantics).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"
    ),
)
from airtable_config import (  # noqa: E402
    api_headers,
    airtable_record_url,
    load_config,
)

# Module-level config — loaded lazily or via main()
_config: dict | None = None


def _ensure_config(config_path: str | None = None) -> dict:
    """Load config if not already loaded. Returns the full config."""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def update_org(base_key: str, record_id: str, updates: dict) -> dict:
    """PATCH an Airtable organization record with the given field updates."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]

    fields = {}

    if "name" in updates:
        fields[config["orgs_name_field"]] = updates["name"]

    if "industry" in updates:
        fields[config["orgs_industry_field"]] = updates["industry"]

    if "size" in updates:
        fields[config["orgs_size_field"]] = updates["size"]

    if "description" in updates:
        fields[config["orgs_description_field"]] = updates["description"]

    if "website" in updates:
        fields[config["orgs_website_field"]] = updates["website"]

    if not fields:
        print(
            "Error: No fields to update. Specify at least one field flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"https://api.airtable.com/v0/{config['base_id']}/{config['orgs_table']}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="PATCH"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"Error updating organization: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Update an Airtable organization record (PATCH semantics).",
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["bb", "aitb"],
        help="Which base the organization is in",
    )
    parser.add_argument("--id", required=True, help="The Airtable record ID (recXXX)")
    parser.add_argument("--name", help="Organization name")
    parser.add_argument("--industry", help="Industry")
    parser.add_argument("--size", help="Company size")
    parser.add_argument("--description", help="Description")
    parser.add_argument("--website", help="Website URL")
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )

    args = parser.parse_args()

    # Load config
    _ensure_config(args.config)

    updates = {}
    if args.name:
        updates["name"] = args.name
    if args.industry:
        updates["industry"] = args.industry
    if args.size:
        updates["size"] = args.size
    if args.description:
        updates["description"] = args.description
    if args.website:
        updates["website"] = args.website

    result = update_org(args.base, args.id, updates)

    cfg = _ensure_config()
    config = cfg["bases"][args.base]
    fields = result.get("fields", {})

    output = {
        "id": result["id"],
        "name": fields.get(config["orgs_name_field"], ""),
        "base": args.base,
        "airtable_url": airtable_record_url(
            config["base_id"], config["orgs_table"], result["id"]
        ),
        "updated_fields": list(updates.keys()),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
