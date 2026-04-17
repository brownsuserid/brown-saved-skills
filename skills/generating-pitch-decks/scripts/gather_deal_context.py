#!/usr/bin/env python3
"""
Gather full context for a deal to support pitch deck and proposal generation.

Fetches deal record, primary contact, organization, Airtable notes, and
searches Google Drive for meeting transcript metadata. Outputs JSON for use
by generate_proposal.py or the generating-pitch-decks workflow.

Config-driven: reads base IDs, table IDs, and field names from YAML config.

Usage:
    python3 gather_deal_context.py --deal "Radiant Nuclear"
    python3 gather_deal_context.py --deal-id recPujEjs4Ntc6rok
    python3 gather_deal_context.py --deal "Cetera" --base bb
    python3 gather_deal_context.py --deal "Acme" --config /path/to.yaml
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"))

from airtable_config import api_headers, airtable_record_url, load_config

GOG_ACCOUNTS = {
    "bb": "aaron@brainbridge.app",
    "aitb": "aaron@aitrailblazers.org",
}


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def fetch_record(
    base_id: str, table_id: str, record_id: str, headers: dict
) -> dict[str, Any]:
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def fetch_records(
    base_id: str, table_id: str, headers: dict, formula: str | None = None
) -> list[dict[str, Any]]:
    import urllib.parse
    import urllib.request

    records: list[dict[str, Any]] = []
    offset = None

    while True:
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        params: dict[str, str] = {}
        if formula:
            params["filterByFormula"] = formula
        if offset:
            params["offset"] = offset

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


def search_deals_by_name(
    name: str, base_id: str, deals_table: str, headers: dict
) -> list[dict[str, Any]]:
    """Search Deals table for deals matching name (case-insensitive contains)."""
    formula = f"SEARCH(LOWER('{name}'), LOWER({{Name}}))"
    return fetch_records(base_id, deals_table, headers, formula=formula)


# ---------------------------------------------------------------------------
# Drive transcript search (via gog CLI)
# ---------------------------------------------------------------------------


def search_drive_transcripts(
    query: str, account: str, max_results: int = 10
) -> list[dict[str, Any]]:
    """Search Google Drive for transcript files via gog CLI."""
    try:
        result = subprocess.run(
            [
                "gog",
                "drive",
                "search",
                query,
                "--account",
                account,
                "--max",
                str(max_results),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(
                f"Warning: gog drive search failed: {result.stderr[:200]}",
                file=sys.stderr,
            )
            return []
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"Warning: could not search Drive: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def gather_context(
    config: dict,
    deal_id: str | None,
    deal_name: str | None,
    base_key: str = "bb",
) -> dict[str, Any]:
    """Assemble full deal context for pitch deck/proposal generation."""
    headers = api_headers()
    base_cfg = config["bases"][base_key]
    tables = base_cfg.get("tables", {})

    base_id = base_cfg["base_id"]
    deals_table = base_cfg.get("deals_table_id", tables.get("deals", ""))
    orgs_table = base_cfg.get("orgs_table", tables.get("organizations", ""))
    contacts_table = base_cfg.get("contacts_table_id", tables.get("contacts", ""))
    deal_contacts_table = tables.get("deal_contacts", "tblxdCIQQ7Uu0g1qS")

    # Resolve deal record
    if deal_id:
        print(f"Fetching deal {deal_id}...", file=sys.stderr)
        deal = fetch_record(base_id, deals_table, deal_id, headers)
        deals = [deal]
    elif deal_name:
        print(f"Searching for deal matching '{deal_name}'...", file=sys.stderr)
        deals = search_deals_by_name(deal_name, base_id, deals_table, headers)
        if not deals:
            print(f"No deals found matching '{deal_name}'.", file=sys.stderr)
            sys.exit(1)
        if len(deals) > 1:
            names = [d.get("fields", {}).get("Name", d["id"]) for d in deals]
            print(
                f"Multiple deals found: {names}. Using first match.",
                file=sys.stderr,
            )
        deal = deals[0]
        deal_id = deal["id"]
    else:
        print("Error: provide --deal or --deal-id", file=sys.stderr)
        sys.exit(1)

    df = deal.get("fields", {})

    result: dict[str, Any] = {
        "deal": {
            "id": deal_id,
            "name": df.get("Name", ""),
            "status": df.get("Status", ""),
            "type": df.get("Type", ""),
            "description": df.get("Description", ""),
            "pain_points": df.get("Pain Points", ""),
            "stakeholder_map": df.get("Stakeholder Map", ""),
            "airtable_url": airtable_record_url(base_id, deals_table, deal_id),
        },
        "contact": None,
        "organization": None,
        "airtable_notes": [],
        "drive_transcripts": [],
    }

    # Organization
    org_ids = df.get("Organization", [])
    if org_ids and orgs_table:
        print(f"Fetching org {org_ids[0]}...", file=sys.stderr)
        try:
            org = fetch_record(base_id, orgs_table, org_ids[0], headers)
            of = org.get("fields", {})
            result["organization"] = {
                "id": org_ids[0],
                "name": of.get("Name", ""),
                "website": of.get("Website", ""),
                "industry": of.get("Industry", ""),
            }
        except Exception as exc:
            print(f"Warning: could not fetch org: {exc}", file=sys.stderr)

    # Contact via Deal Contacts junction table
    dc_ids = df.get("Deal Contacts", [])
    if dc_ids and deal_contacts_table:
        print("Resolving contact via Deal Contacts junction...", file=sys.stderr)
        try:
            junction = fetch_record(base_id, deal_contacts_table, dc_ids[0], headers)
            linked_contact_ids = junction.get("fields", {}).get("Contact", [])
            if linked_contact_ids and contacts_table:
                contact = fetch_record(
                    base_id, contacts_table, linked_contact_ids[0], headers
                )
                cf = contact.get("fields", {})
                result["contact"] = {
                    "id": linked_contact_ids[0],
                    "name": cf.get("Full Name", cf.get("Name", "")),
                    "email": cf.get("Email (Work)", cf.get("Email (Personal)", "")),
                    "title": cf.get("Title", ""),
                    "linkedin": cf.get("LinkedIn", ""),
                }
        except Exception as exc:
            print(f"Warning: could not fetch contact: {exc}", file=sys.stderr)

    # Airtable deal notes (most recent 5)
    note_ids = df.get("Notes", [])
    notes_table = tables.get("notes", "Notes")
    if note_ids:
        print(f"Fetching {min(len(note_ids), 5)} deal notes...", file=sys.stderr)
        for note_id in note_ids[:5]:
            try:
                note = fetch_record(base_id, notes_table, note_id, headers)
                nf = note.get("fields", {})
                result["airtable_notes"].append(
                    {
                        "id": note_id,
                        "title": nf.get("Title", ""),
                        "created": nf.get("Created", ""),
                    }
                )
            except Exception:
                pass

    # Google Drive transcript search
    org_name = (result["organization"] or {}).get("name", "")
    contact_name = (result["contact"] or {}).get("name", "")
    deal_name_str = df.get("Name", "")

    search_query = " OR ".join(filter(None, [org_name, contact_name, deal_name_str]))
    if search_query:
        print(f"Searching Drive for transcripts: '{search_query}'...", file=sys.stderr)
        account = GOG_ACCOUNTS.get(base_key, GOG_ACCOUNTS["bb"])
        transcripts = search_drive_transcripts(search_query, account)
        result["drive_transcripts"] = transcripts

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gather full deal context for pitch deck/proposal generation."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--deal", help="Deal name (fuzzy search in Deals)")
    source.add_argument("--deal-id", help="Airtable deal record ID")
    parser.add_argument(
        "--base",
        default="bb",
        help="Airtable base key (default: bb)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (default: ../airtable-config/configs/all.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    try:
        context = gather_context(
            config,
            deal_id=args.deal_id,
            deal_name=args.deal,
            base_key=args.base,
        )
        print(json.dumps(context, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
