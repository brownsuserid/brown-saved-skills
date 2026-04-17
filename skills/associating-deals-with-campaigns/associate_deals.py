#!/usr/bin/env python3
"""
Prepare enriched deal and campaign data for LLM-based campaign association.

Fetches the operator's orphaned BB deals, enriches each with contact
activity logs and deal context, fetches all campaigns, and outputs
structured JSON for LLM agents to reason about matches.

This script does NOT match deals to campaigns. It prepares the data.
The calling LLM processes batches of deals against the campaign list
and recommends associations.

Usage:
    # Prepare data for Aaron's deals
    python3 associate_deals.py --assignee aaron

    # Single deal
    python3 associate_deals.py --deal recXXX

    # Execute associations from a recommendations file
    python3 associate_deals.py --execute recommendations.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "airtable-config"))

from _config import (  # noqa: E402
    BASES,
    PEOPLE,
    TABLES,
    api_headers,
    airtable_record_url,
)

BB_BASE_ID = BASES["bb"]["base_id"]
DEALS_TABLE = TABLES["bb"]["deals"]
CAMPAIGNS_TABLE = TABLES["bb"]["campaigns"]
CONTACTS_TABLE = TABLES["bb"]["contacts"]
ORGS_TABLE = TABLES["bb"]["organizations"]
DEAL_CONTACTS_TABLE = TABLES["bb"]["deal_contacts"]
ACTIVITY_LOGS_TABLE = TABLES["bb"]["contact_activity_logs"]

CAMPAIGNS_FIELD_NAME = "Campaigns"
CAMPAIGNS_FIELD_ID = "fldFyWKc7rUdtk4sI"

BATCH_SIZE = 5


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def _fetch_all(
    table_id: str, formula: str = "", fields: list[str] | None = None
) -> list[dict]:
    """Fetch all records from an Airtable table, handling pagination."""
    records: list[dict] = []
    offset = None
    while True:
        params: dict[str, str] = {"pageSize": "100"}
        if formula:
            params["filterByFormula"] = formula
        if fields:
            for i, f in enumerate(fields):
                params[f"fields[{i}]"] = f
        if offset:
            params["offset"] = offset
        qs = urllib.parse.urlencode(params)
        url = f"https://api.airtable.com/v0/{BB_BASE_ID}/{table_id}?{qs}"
        req = urllib.request.Request(url, headers=api_headers())
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def _fetch_record(table_id: str, record_id: str) -> dict | None:
    """Fetch a single record by ID."""
    url = f"https://api.airtable.com/v0/{BB_BASE_ID}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return None


def _patch_record(table_id: str, record_id: str, fields: dict) -> dict:
    """PATCH a single record."""
    url = f"https://api.airtable.com/v0/{BB_BASE_ID}/{table_id}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=api_headers(), method="PATCH"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def fetch_orphaned_deals(
    single_deal_id: str | None = None,
    assignee_record_id: str | None = None,
) -> list[dict]:
    """Fetch open BB deals that have no campaign linked."""
    if single_deal_id:
        rec = _fetch_record(DEALS_TABLE, single_deal_id)
        if not rec:
            print(
                f"Error: Deal {single_deal_id} not found.",
                file=sys.stderr,
            )
            sys.exit(1)
        return [rec]

    formula = (
        "AND("
        'NOT(OR({Status}="Closed Won",{Status}="Closed Lost",'
        '{Status}="Closed Lost to Competitor")),'
        f"LEN(ARRAYJOIN({{{CAMPAIGNS_FIELD_NAME}}}))=0"
        ")"
    )
    records = _fetch_all(DEALS_TABLE, formula=formula)

    if assignee_record_id:
        filtered = []
        for r in records:
            assignees = r.get("fields", {}).get("Assignee", [])
            if isinstance(assignees, list):
                if assignee_record_id in assignees:
                    filtered.append(r)
            elif assignees == assignee_record_id:
                filtered.append(r)
        return filtered

    return records


def fetch_campaigns() -> list[dict]:
    """Fetch all campaigns."""
    return _fetch_all(
        CAMPAIGNS_TABLE,
        fields=[
            "Name",
            "Source",
            "Description",
            "Status",
            "Target Audience",
            "Campaign Plan",
            "Campaign Code",
            "Message Guardrails",
            "Deals",
            "Assignee",
            "Started",
            "Ended",
        ],
    )


def resolve_linked_names(
    record_ids: list[str], table_id: str, name_field: str
) -> list[str]:
    """Resolve a list of linked record IDs to their name values."""
    names = []
    for rid in record_ids:
        rec = _fetch_record(table_id, rid)
        if rec:
            name = rec.get("fields", {}).get(name_field, "")
            if name:
                names.append(name)
    return names


def fetch_activity_logs(contact_id: str) -> list[dict]:
    """Fetch activity logs: 3 earliest + 3 most recent.

    The earliest outreaches reveal the campaign source (first touch).
    The most recent show current state. Fetches up to 20 log IDs,
    resolves the bookends, returns in chronological order.
    """
    rec = _fetch_record(CONTACTS_TABLE, contact_id)
    if not rec:
        return []
    log_ids = rec.get("fields", {}).get("Contact Activity Logs", [])
    if not log_ids:
        return []

    # Only fetch bookends: first 3 + last 3 IDs (max 6 API calls)
    ids_to_fetch = []
    if len(log_ids) <= 6:
        ids_to_fetch = log_ids
    else:
        ids_to_fetch = log_ids[:3] + log_ids[-3:]

    # Deduplicate in case of overlap
    seen_ids: set[str] = set()
    unique_ids = []
    for lid in ids_to_fetch:
        if lid not in seen_ids:
            seen_ids.add(lid)
            unique_ids.append(lid)

    logs = []
    for log_id in unique_ids:
        log = _fetch_record(ACTIVITY_LOGS_TABLE, log_id)
        if log:
            lf = log.get("fields", {})
            logs.append(
                {
                    "activity_type": lf.get("Activity Type", ""),
                    "details": lf.get("Details", ""),
                    "created": lf.get("Created", ""),
                }
            )

    logs.sort(key=lambda x: x.get("created", ""))
    return logs


def enrich_deal(deal: dict) -> dict[str, Any]:
    """Extract and resolve key fields from a deal record."""
    fields = deal.get("fields", {})
    deal_id = deal["id"]

    # Resolve org name
    org_ids = fields.get("Organization", [])
    org_names = []
    if org_ids:
        org_names = resolve_linked_names(
            org_ids if isinstance(org_ids, list) else [org_ids],
            ORGS_TABLE,
            "Name",
        )

    # Resolve primary contact + activity logs (1 contact to limit API calls)
    dc_ids = fields.get("Deal Contacts", [])
    contact_names: list[str] = []
    activity_logs: list[dict] = []
    primary_contact_id = None
    if dc_ids:
        junc = _fetch_record(DEAL_CONTACTS_TABLE, dc_ids[0])
        if junc:
            contact_ids = junc.get("fields", {}).get("Contact", [])
            if contact_ids:
                primary_contact_id = (
                    contact_ids[0] if isinstance(contact_ids, list) else contact_ids
                )
                contact_names.extend(
                    resolve_linked_names(
                        [primary_contact_id], CONTACTS_TABLE, "Full Name"
                    )
                )

    if primary_contact_id:
        activity_logs = fetch_activity_logs(primary_contact_id)

    # Created by
    created_by = fields.get("Created By", {})
    created_by_name = created_by.get("name", "") if isinstance(created_by, dict) else ""

    return {
        "id": deal_id,
        "name": fields.get("Name", ""),
        "type": fields.get("Type", ""),
        "description": (fields.get("Description", "") or "")[:500],
        "pain_points": (fields.get("Pain Points", "") or "")[:300],
        "tags": fields.get("Tags 2", "") or "",
        "engagement": fields.get("Engagement", "") or "",
        "outreach_plan": ((fields.get("Outreach Plan", "") or "")[:300]),
        "org_names": org_names,
        "contact_names": contact_names,
        "created_by": created_by_name,
        "created": fields.get("Created", "")[:10],
        "activity_logs": [
            {
                "type": log["activity_type"],
                "details": (log.get("details", "") or "")[:500],
                "date": log.get("created", "")[:10],
            }
            for log in activity_logs
        ],
        "url": airtable_record_url(BB_BASE_ID, DEALS_TABLE, deal_id),
    }


def parse_campaign(campaign: dict) -> dict[str, Any]:
    """Parse a campaign record with full context for LLM reasoning."""
    fields = campaign.get("fields", {})
    assignee = fields.get("Assignee", {})
    return {
        "id": campaign["id"],
        "name": fields.get("Name", ""),
        "source": fields.get("Source", ""),
        "status": fields.get("Status", ""),
        "campaign_code": fields.get("Campaign Code", "") or "",
        "description": (fields.get("Description", "") or "")[:500],
        "target_audience": ((fields.get("Target Audience", "") or "")[:500]),
        "campaign_plan": ((fields.get("Campaign Plan", "") or "")[:800]),
        "message_guardrails": ((fields.get("Message Guardrails", "") or "")[:300]),
        "deal_count": len(fields.get("Deals", [])),
        "assignee": (assignee.get("name", "") if isinstance(assignee, dict) else ""),
        "started": fields.get("Started", "") or "",
        "ended": fields.get("Ended", "") or "",
    }


# ---------------------------------------------------------------------------
# Execution (apply recommendations)
# ---------------------------------------------------------------------------


def execute_recommendations(recs_file: str) -> None:
    """Apply campaign associations from a recommendations JSON file.

    Expected format:
    [
        {"deal_id": "recXXX", "campaign_id": "recYYY"},
        ...
    ]
    """
    with open(recs_file) as f:
        recs = json.load(f)

    success = 0
    errors = 0
    for rec in recs:
        deal_id = rec["deal_id"]
        campaign_id = rec["campaign_id"]
        try:
            _patch_record(
                DEALS_TABLE,
                deal_id,
                {CAMPAIGNS_FIELD_ID: [campaign_id]},
            )
            print(
                f"  OK: {rec.get('deal_name', deal_id)} -> "
                f"{rec.get('campaign_name', campaign_id)}"
            )
            success += 1
        except Exception as e:
            print(
                f"  ERROR: {rec.get('deal_name', deal_id)}: {e}",
                file=sys.stderr,
            )
            errors += 1

    print(f"\nDone: {success} linked, {errors} errors.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare enriched deal + campaign data for LLM-based campaign association."
        ),
    )
    parser.add_argument(
        "--assignee",
        default="aaron",
        help="Operator name. Scopes to their deals. Default: aaron",
    )
    parser.add_argument(
        "--deal",
        help="Process a single deal by record ID (recXXX)",
    )
    parser.add_argument(
        "--execute",
        metavar="FILE",
        help="Apply associations from a recommendations JSON file",
    )
    args = parser.parse_args()

    # Execute mode
    if args.execute:
        execute_recommendations(args.execute)
        return

    operator = args.assignee.lower()
    assignee_bb_id = PEOPLE.get(operator, {}).get("bb")

    # Step 1: Fetch deals
    print(f"Fetching orphaned deals for {operator}...", file=sys.stderr)
    raw_deals = fetch_orphaned_deals(
        single_deal_id=args.deal,
        assignee_record_id=assignee_bb_id if not args.deal else None,
    )
    print(f"  Found {len(raw_deals)} deal(s).", file=sys.stderr)

    # Step 2: Fetch campaigns
    print("Fetching campaigns...", file=sys.stderr)
    raw_campaigns = fetch_campaigns()
    campaigns = [parse_campaign(c) for c in raw_campaigns]
    print(f"  Found {len(campaigns)} campaign(s).", file=sys.stderr)

    # Step 3: Enrich deals
    print(
        "Enriching deals (contacts, orgs, activity logs)...",
        file=sys.stderr,
    )
    deals = []
    for i, raw in enumerate(raw_deals):
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(raw_deals)}...", file=sys.stderr)
        deals.append(enrich_deal(raw))
    print(f"  Enriched {len(deals)} deal(s).", file=sys.stderr)

    # Step 4: Output batched JSON
    batches = []
    for i in range(0, len(deals), BATCH_SIZE):
        batches.append(deals[i : i + BATCH_SIZE])

    output = {
        "operator": operator,
        "total_deals": len(deals),
        "total_campaigns": len(campaigns),
        "batch_size": BATCH_SIZE,
        "total_batches": len(batches),
        "campaigns": campaigns,
        "batches": batches,
    }

    print(json.dumps(output, indent=2))
    print(
        f"\nOutput: {len(batches)} batches of up to {BATCH_SIZE} deals "
        f"+ {len(campaigns)} campaigns.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
