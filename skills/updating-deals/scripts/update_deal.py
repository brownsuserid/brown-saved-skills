#!/usr/bin/env python3
"""
Update fields on an Airtable deal record.

Usage:
    python3 update_deal.py --base bb --id recXXX \
        [--name "Acme Consulting"] \
        [--status "Negotiation"] \
        [--type "New Business"] \
        [--organization recOrgXXX] \
        [--contact recContactXXX] \
        [--amount 50000] \
        [--description "Q2 engagement"] \
        [--assignee pablo] \
        [--campaign recCampaignXXX] \
        [--config /path/to/config.yaml]

Only specified fields are updated (PATCH semantics).
--contact on BB creates/updates a junction record. On AITB it sets the field directly.
--campaign is BB only.
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
    resolve_assignee,
)

# Module-level config — loaded lazily or via main()
_config: dict | None = None


def _ensure_config(config_path: str | None = None) -> dict:
    """Load config if not already loaded. Returns the full config."""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def _create_junction_record(base_key: str, deal_id: str, contact_id: str) -> dict:
    """Create a junction record linking a deal to a contact (BB only)."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]
    junction_table = config["deals_contact_junction_table"]
    url = f"https://api.airtable.com/v0/{config['base_id']}/{junction_table}"
    payload = json.dumps(
        {
            "fields": {
                "Deal": [deal_id],
                "Contact": [contact_id],
            }
        }
    ).encode()

    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error creating junction record: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def update_deal(base_key: str, record_id: str, updates: dict) -> dict:
    """PATCH an Airtable deal record with the given field updates."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]

    fields = {}

    if "name" in updates:
        fields[config["deals_name_field"]] = updates["name"]

    if "status" in updates:
        fields[config["deals_status_field"]] = updates["status"]

    if "type" in updates:
        type_field = config.get("deals_type_field")
        if not type_field:
            print(
                f"Error: Base '{base_key}' does not have a deals_type_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[type_field] = updates["type"]

    if "organization" in updates:
        fields[config["deals_org_field"]] = [updates["organization"]]

    if "amount" in updates:
        fields[config["deals_amount_field"]] = updates["amount"]

    if "description" in updates:
        fields[config["deals_description_field"]] = updates["description"]

    if "assignee" in updates:
        assignee_field = config.get("deals_assignee_field")
        if not assignee_field:
            print(
                f"Error: Base '{base_key}' does not have a deals_assignee_field configured.",
                file=sys.stderr,
            )
            sys.exit(1)
        assignee_id = resolve_assignee(cfg, updates["assignee"], base_key)
        fields[assignee_field] = [assignee_id]

    if "campaign" in updates:
        campaign_field = config.get("deals_campaign_field")
        if not campaign_field:
            print(
                f"Error: --campaign is not supported for base '{base_key}'.",
                file=sys.stderr,
            )
            sys.exit(1)
        fields[campaign_field] = [updates["campaign"]]

    # Contact handled separately for BB (junction table) vs AITB (direct link)
    contact_id = updates.get("contact")

    if not fields and not contact_id:
        print(
            "Error: No fields to update. Specify at least one field flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = None

    # PATCH the deal record if there are fields to update
    if fields:
        url = f"https://api.airtable.com/v0/{config['base_id']}/{config['deals_table_id']}/{record_id}"
        payload = json.dumps({"fields": fields}).encode()

        req = urllib.request.Request(
            url, data=payload, headers=api_headers(), method="PATCH"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"Error updating deal: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Handle contact linking
    if contact_id:
        junction_table = config.get("deals_contact_junction_table")
        if junction_table:
            # BB: create junction record
            _create_junction_record(base_key, record_id, contact_id)
        else:
            # AITB: set contact field directly on the deal
            contact_fields = {config["deals_contact_field"]: [contact_id]}
            url = f"https://api.airtable.com/v0/{config['base_id']}/{config['deals_table_id']}/{record_id}"
            payload = json.dumps({"fields": contact_fields}).encode()
            req = urllib.request.Request(
                url, data=payload, headers=api_headers(), method="PATCH"
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    result = json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                print(f"Error linking contact: {e.read().decode()}", file=sys.stderr)
                sys.exit(1)

    # If only contact was set (no other fields), fetch the record for output
    if result is None:
        url = f"https://api.airtable.com/v0/{config['base_id']}/{config['deals_table_id']}/{record_id}"
        req = urllib.request.Request(url, headers=api_headers())
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            print(f"Error fetching deal: {e}", file=sys.stderr)
            sys.exit(1)

    return result


def check_data_quality(result: dict, base_key: str) -> None:
    """Print warnings for missing data quality fields."""
    cfg = _ensure_config()
    config = cfg["bases"][base_key]
    fields = result.get("fields", {})

    org_value = fields.get(config["deals_org_field"])
    if not org_value:
        print(
            "Warning: Deal has no Organization linked. Use --organization recXXX to fix.",
            file=sys.stderr,
        )

    contact_value = fields.get(config["deals_contact_field"])
    if not contact_value:
        print(
            "Warning: Deal has no Contact linked. Use --contact recXXX to fix.",
            file=sys.stderr,
        )

    if base_key == "bb":
        campaign_value = fields.get(config.get("deals_campaign_field", ""), "")
        if not campaign_value:
            print(
                "Warning: Deal has no Campaign linked. Use --campaign recXXX to fix.",
                file=sys.stderr,
            )


def main():
    parser = argparse.ArgumentParser(
        description="Update an Airtable deal record (PATCH semantics).",
    )
    parser.add_argument(
        "--base",
        required=True,
        choices=["bb", "aitb"],
        help="Which base the deal is in",
    )
    parser.add_argument("--id", required=True, help="The Airtable record ID (recXXX)")
    parser.add_argument("--name", help="Deal name")
    parser.add_argument("--status", help="Deal status (passed as literal)")
    parser.add_argument("--type", help="Deal type (BB only)")
    parser.add_argument("--organization", help="Organization record ID (recXXX)")
    parser.add_argument("--contact", help="Contact record ID (recXXX)")
    parser.add_argument("--amount", type=float, help="Deal amount")
    parser.add_argument("--description", help="Deal description")
    parser.add_argument("--assignee", help="Assignee: pablo, aaron, or record ID")
    parser.add_argument("--campaign", help="Campaign record ID (BB only)")
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )

    args = parser.parse_args()

    # Load config
    _ensure_config(args.config)

    # Validate BB-only flags
    if args.campaign and args.base == "aitb":
        print("Error: --campaign is not supported for base 'aitb'.", file=sys.stderr)
        sys.exit(1)

    updates = {}
    if args.name:
        updates["name"] = args.name
    if args.status:
        updates["status"] = args.status
    if args.type:
        updates["type"] = args.type
    if args.organization:
        updates["organization"] = args.organization
    if args.contact:
        updates["contact"] = args.contact
    if args.amount is not None:
        updates["amount"] = args.amount
    if args.description:
        updates["description"] = args.description
    if args.assignee:
        updates["assignee"] = args.assignee
    if args.campaign:
        updates["campaign"] = args.campaign

    result = update_deal(args.base, args.id, updates)

    check_data_quality(result, args.base)

    cfg = _ensure_config()
    config = cfg["bases"][args.base]
    fields = result.get("fields", {})

    output = {
        "id": result["id"],
        "name": fields.get(config["deals_name_field"], ""),
        "status": fields.get(config["deals_status_field"], ""),
        "base": args.base,
        "airtable_url": airtable_record_url(
            config["base_id"], config["deals_table_id"], result["id"]
        ),
        "updated_fields": list(updates.keys()),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
