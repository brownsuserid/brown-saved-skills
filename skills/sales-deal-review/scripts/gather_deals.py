#!/usr/bin/env python3
"""
Gather deals from Airtable bases for review.

Queries all configured bases for open deals, checks if each has incomplete tasks
assigned to Aaron, and generates a consolidated report.

Config-driven: iterates over all bases in the YAML config that have deal-related
fields (deals_table_id, deals_name_field, etc.).

Usage:
    python3 gather_deals.py
    python3 gather_deals.py --config /path/to/config.yaml
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import api_headers, load_config


# ---------------------------------------------------------------------------
# Per-base deal configuration (derived from YAML config at runtime)
# ---------------------------------------------------------------------------

# Hardcoded per-base overrides that aren't in the YAML config.
# These capture deal-specific field mappings and display logic.
DEAL_OVERRIDES = {
    "bb": {
        "deal_name_field": "Name",
        "deal_status_field": "Status",
        "deal_org_field": "Organization",
        "deal_contact_field": "Deal Contacts",
        "deal_contacts_junction_table": "tblxdCIQQ7Uu0g1qS",
        "deal_tasks_field": "Tasks",
        "deal_assignee_field": "Assignee",
        "deal_type_field": "Type",
        "org_name_field": "Name",
        "contact_name_field": "Full Name",
        "lookup_names": True,
        "status_field_name": "Status",
        "closed_statuses": [
            "Closed Won",
            "Closed Lost",
            "Closed Lost to Competitor",
        ],
        "task_name_field": "Task",
        "task_assignee_field": "Assignee",
        "task_status_field": "Status",
        "task_deals_field": "Deals",
        "type_display": {
            "New Business": "New Customer",
            "Existing Business": "Existing Customer",
            "Partner": "Partner",
        },
    },
    "aitb": {
        "deal_name_field": "Project Title",
        "deal_status_field": "Stage",
        "deal_org_field": "Organization Name",
        "deal_contact_field": "Contact",
        "deal_tasks_field": "Tasks",
        "deal_assignee_field": None,
        "deal_type_field": None,
        "org_name_field": "Name",
        "contact_name_field": "Name",
        "lookup_names": True,
        "deal_contact_name_lookup": "Contact Full Name",
        "status_field_name": "Stage",
        "closed_statuses": ["Closed - Won", "Closed - Lost"],
        "task_name_field": "Task",
        "task_assignee_field": "Assignee",
        "task_status_field": "Status",
        "task_deals_field": "Sponsor Deals",
        "type_display": None,
        "default_type": "Sponsor",
    },
}


def build_deal_config(config: dict, base_key: str) -> dict | None:
    """Build deal configuration for a base by merging YAML config with overrides."""
    base_cfg = config["bases"].get(base_key)
    if not base_cfg:
        return None

    # Skip bases without deal-related fields
    if not base_cfg.get("deals_table_id"):
        return None

    overrides = DEAL_OVERRIDES.get(base_key)
    if not overrides:
        return None

    people = config.get("people", {})
    aaron_id = people.get("aaron", {}).get(base_key)

    return {
        "base_id": base_cfg["base_id"],
        "deals_table_id": base_cfg["deals_table_id"],
        "tasks_table_id": base_cfg["tasks_table_id"],
        "orgs_table_id": base_cfg.get("orgs_table"),
        "contacts_table_id": base_cfg.get("contacts_table_id"),
        "aaron_id": aaron_id,
        **overrides,
    }


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def _api_url(base_id: str, table_id: str) -> str:
    return f"https://api.airtable.com/v0/{base_id}/{table_id}"


def _airtable_record_url(base_id: str, table_id: str, record_id: str) -> str:
    return f"https://airtable.com/{base_id}/{table_id}/{record_id}"


def fetch_records(
    base_id: str,
    table_id: str,
    headers: dict,
    formula: str | None = None,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch records from Airtable with pagination."""
    import urllib.parse
    import urllib.request

    records = []
    offset = None

    while True:
        url = _api_url(base_id, table_id)
        params = {}
        if formula:
            params["filterByFormula"] = formula
        if offset:
            params["offset"] = offset

        # Build URL with params
        if fields:
            field_params = "&".join(
                f"fields%5B%5D={urllib.parse.quote(f)}" for f in fields
            )
            base_params = urllib.parse.urlencode(
                {k: v for k, v in params.items() if k != "fields[]"}
            )
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


def lookup_record(
    base_id: str, table_id: str, record_id: str, field_name: str, headers: dict
) -> str | None:
    """Lookup a single field value from a record by field name."""
    import urllib.request

    url = f"{_api_url(base_id, table_id)}/{record_id}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("fields", {}).get(field_name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def gather_deals_for_base(base_key: str, deal_cfg: dict, headers: dict) -> list[dict]:
    """Gather open deals from a single base."""
    base_id = deal_cfg["base_id"]
    deals_table = deal_cfg["deals_table_id"]

    # Build filter: exclude closed deals only (assignee filtered in Python
    # because ARRAYJOIN on linked records joins display names, not record IDs)
    closed_conditions = ", ".join(
        f'{{{deal_cfg["status_field_name"]}}}!="{s}"'
        for s in deal_cfg["closed_statuses"]
    )
    formula = f"AND({closed_conditions})"

    print(f"[{base_key}] Fetching deals...", file=sys.stderr)
    deals_raw = fetch_records(base_id, deals_table, headers, formula=formula)

    # Filter by assignee in Python (where we have raw record IDs)
    assignee_field = deal_cfg["deal_assignee_field"]
    if assignee_field:
        aaron_id_for_filter = deal_cfg["aaron_id"]
        deals_raw = [
            d
            for d in deals_raw
            if aaron_id_for_filter in d.get("fields", {}).get(assignee_field, [])
        ]

    print(f"[{base_key}] Found {len(deals_raw)} deals", file=sys.stderr)

    # Collect all task IDs linked from deals, then batch-fetch them
    tasks_table = deal_cfg["tasks_table_id"]
    tasks_field = deal_cfg["deal_tasks_field"]

    all_task_ids: set[str] = set()
    for deal in deals_raw:
        task_ids = deal.get("fields", {}).get(tasks_field, [])
        all_task_ids.update(task_ids)

    # Batch-fetch task records using OR(RECORD_ID()=...) formula
    task_cache: dict[str, dict] = {}
    task_id_list = list(all_task_ids)
    # Airtable formula length limit -- batch in groups of 50
    for i in range(0, len(task_id_list), 50):
        batch = task_id_list[i : i + 50]
        conditions = ", ".join(f'RECORD_ID()="{tid}"' for tid in batch)
        formula = f"OR({conditions})"
        task_records = fetch_records(base_id, tasks_table, headers, formula=formula)
        for t in task_records:
            task_cache[t["id"]] = t

    # Build task index by deal using the deal's linked Tasks field
    tasks_by_deal: dict[str, list[dict]] = {}
    done_statuses = {"Completed", "Archived", "Cancelled"}

    for deal in deals_raw:
        deal_id = deal["id"]
        linked_task_ids = deal.get("fields", {}).get(tasks_field, [])
        for tid in linked_task_ids:
            task = task_cache.get(tid)
            if not task:
                continue
            tf = task.get("fields", {})
            task_status = tf.get("Status", "")
            if task_status in done_statuses:
                continue
            # Include tasks assigned to anyone -- what matters is the deal has a next action
            task_name = tf.get("Task", "Untitled")
            tasks_by_deal.setdefault(deal_id, []).append(
                {
                    "id": tid,
                    "name": task_name,
                    "status": task_status,
                }
            )

    # Process deals
    deals = []
    for deal in deals_raw:
        deal_id = deal["id"]
        fields = deal.get("fields", {})

        # Get deal name
        name = fields.get(deal_cfg["deal_name_field"], "Untitled Deal")

        # Get status/stage
        status = fields.get(deal_cfg["deal_status_field"], "Unknown")

        # Get deal type
        if deal_cfg.get("deal_type_field"):
            raw_type = fields.get(deal_cfg["deal_type_field"], "Unknown")
            display_type = deal_cfg["type_display"].get(raw_type, raw_type)
        else:
            display_type = deal_cfg.get("default_type", "Unknown")

        # Get org and contact names
        if deal_cfg["lookup_names"]:
            # Separate API lookups
            org_ids = fields.get(deal_cfg["deal_org_field"], [])
            org_name = None
            if org_ids:
                org_name = lookup_record(
                    base_id,
                    deal_cfg["orgs_table_id"],
                    org_ids[0],
                    deal_cfg["org_name_field"],
                    headers,
                )

            # Contact: resolve via junction table if configured, else direct
            dc_ids = fields.get(deal_cfg["deal_contact_field"], [])
            contact_name = None
            if dc_ids:
                junction_table = deal_cfg.get("deal_contacts_junction_table")
                if junction_table:
                    # Deal Contacts junction -> Contact record
                    junction_contact = lookup_record(
                        base_id,
                        junction_table,
                        dc_ids[0],
                        "Contact",
                        headers,
                    )
                    if (
                        junction_contact
                        and isinstance(junction_contact, list)
                        and junction_contact
                    ):
                        contact_name = lookup_record(
                            base_id,
                            deal_cfg["contacts_table_id"],
                            junction_contact[0],
                            deal_cfg["contact_name_field"],
                            headers,
                        )
                else:
                    # Direct link to contacts table
                    contact_name = lookup_record(
                        base_id,
                        deal_cfg["contacts_table_id"],
                        dc_ids[0],
                        deal_cfg["contact_name_field"],
                        headers,
                    )
        else:
            # Lookup fields on the deal record itself
            org_lookup = fields.get(deal_cfg.get("deal_org_name_lookup", ""), [])
            org_name = org_lookup[0] if org_lookup else None

            contact_lookup = fields.get(
                deal_cfg.get("deal_contact_name_lookup", ""), []
            )
            contact_name = contact_lookup[0] if contact_lookup else None

        # Check for active tasks
        active_tasks = tasks_by_deal.get(deal_id, [])

        deals.append(
            {
                "id": deal_id,
                "name": name,
                "status": status,
                "type": display_type,
                "base": base_key,
                "organization_name": org_name or "No Organization",
                "primary_contact_name": contact_name or "No Contact",
                "task_ids": [t["id"] for t in active_tasks],
                "task_names": [t["name"] for t in active_tasks],
                "has_active_tasks": len(active_tasks) > 0,
                "airtable_url": _airtable_record_url(base_id, deals_table, deal_id),
            }
        )

    return deals


def gather_all_deals(config: dict) -> dict[str, Any]:
    """Gather deals from all configured bases."""
    headers = api_headers()
    all_deals = []

    for base_key in config["bases"]:
        deal_cfg = build_deal_config(config, base_key)
        if not deal_cfg:
            continue
        try:
            base_deals = gather_deals_for_base(base_key, deal_cfg, headers)
            all_deals.extend(base_deals)
        except Exception as e:
            print(f"[{base_key}] Error gathering deals: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)

    # Compute summary -- group by base key dynamically
    summary: dict[str, Any] = {
        "total_deals": len(all_deals),
        "deals_with_tasks": sum(1 for d in all_deals if d["has_active_tasks"]),
        "deals_without_tasks": sum(1 for d in all_deals if not d["has_active_tasks"]),
    }

    # Per-base summaries
    base_keys_seen = {d["base"] for d in all_deals}
    for bk in sorted(base_keys_seen):
        base_deals = [d for d in all_deals if d["base"] == bk]
        base_summary: dict[str, Any] = {
            "total": len(base_deals),
            "without_tasks": sum(1 for d in base_deals if not d["has_active_tasks"]),
        }
        # Add by_type breakdown if any deals have non-default types
        types = {d["type"] for d in base_deals}
        if len(types) > 1 or (
            len(types) == 1 and list(types)[0] not in ("Unknown", "Sponsor")
        ):
            by_type: dict[str, dict] = {}
            for deal in base_deals:
                t = deal["type"]
                by_type.setdefault(t, {"total": 0, "without_tasks": 0})
                by_type[t]["total"] += 1
                if not deal["has_active_tasks"]:
                    by_type[t]["without_tasks"] += 1
            base_summary["by_type"] = by_type
        summary[bk] = base_summary

    return {"deals": all_deals, "summary": summary}


def main():
    parser = argparse.ArgumentParser(
        description="Gather deals from Airtable bases for review"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    try:
        result = gather_all_deals(config)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
