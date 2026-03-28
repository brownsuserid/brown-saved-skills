#!/usr/bin/env python3
"""
Search for deals across Brain Bridge and AITB Airtable bases.

Supports fuzzy matching, deduplication, open-only filtering,
and both human-readable and JSON output.

Usage:
    python search_deals.py "Acme"
    python search_deals.py "Acme" --open --json
    python search_deals.py "Acme" --base bb
    python search_deals.py "Acme" --config /path/to/config.yaml
"""

import argparse
import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

from airtable_config import api_headers, airtable_record_url, load_config  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Module-level config — loaded lazily or via main()
_config: dict | None = None
DEAL_CONFIG: dict = {}


def _build_deal_config(config: dict) -> dict:
    """Build DEAL_CONFIG from the loaded YAML config."""
    bases = config["bases"]
    return {
        "bb": {
            "base_id": bases["bb"]["base_id"],
            "deals_table_id": bases["bb"]["deals_table_id"],
            "source_label": "Brain Bridge Airtable",
            "name_field": bases["bb"]["deals_name_field"],
            "status_field": bases["bb"]["deals_status_field"],
            "type_field": bases["bb"].get("deals_type_field"),
            "org_field": bases["bb"]["deals_org_field"],
            "contact_field": bases["bb"]["deals_contact_field"],
            "deal_contacts_junction_table": bases["bb"].get(
                "deals_contact_junction_table"
            ),
            "contacts_table_id": bases["bb"]["contacts_table_id"],
            "contact_name_field": bases["bb"].get("contacts_name_field", "Full Name"),
            "amount_field": bases["bb"]["deals_amount_field"],
            "description_field": bases["bb"]["deals_description_field"],
            "closed_statuses": [
                "Closed Won",
                "Closed Lost",
                "Closed Lost to Competitor",
            ],
            "search_fields": [bases["bb"]["deals_name_field"]],
            "type_display": {
                "New Business": "New Customer",
                "Existing Business": "Existing Customer",
                "Partner": "Partner",
            },
        },
        "aitb": {
            "base_id": bases["aitb"]["base_id"],
            "deals_table_id": bases["aitb"]["deals_table_id"],
            "source_label": "AITB Airtable",
            "name_field": bases["aitb"]["deals_name_field"],
            "status_field": bases["aitb"]["deals_status_field"],
            "type_field": None,
            "org_field": bases["aitb"]["deals_org_field"],
            "contact_field": bases["aitb"]["deals_contact_field"],
            "amount_field": bases["aitb"]["deals_amount_field"],
            "description_field": bases["aitb"]["deals_description_field"],
            "closed_statuses": ["Closed - Won", "Closed - Lost"],
            "search_fields": [
                bases["aitb"]["deals_name_field"],
                bases["aitb"]["deals_org_field"],
            ],
            "default_type": "Sponsor",
        },
    }


def _ensure_config(config_path: str | None = None) -> dict:
    """Load config if not already loaded. Returns the full config."""
    global _config, DEAL_CONFIG
    if _config is None:
        _config = load_config(config_path)
        DEAL_CONFIG.update(_build_deal_config(_config))
    return _config


# ---------------------------------------------------------------------------
# Fuzzy matching (shared logic with search_orgs)
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, alphanumeric only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fuzzy_score(query: str, target: str) -> int:
    """Calculate a fuzzy match score (0-100) between query and target."""
    norm_query = normalize_name(query)
    norm_target = normalize_name(target)

    if not norm_query or not norm_target:
        return 0

    if norm_query == norm_target:
        return 100

    if norm_query in norm_target:
        return 90

    if norm_target in norm_query:
        return 80

    words = query.split()
    if not words:
        return 0

    match_count = sum(
        1
        for w in words
        if len(normalize_name(w)) >= 3 and normalize_name(w) in norm_target
    )
    return match_count * 70 // len(words)


# ---------------------------------------------------------------------------
# Airtable fetching
# ---------------------------------------------------------------------------


def lookup_field(base_id: str, table_id: str, record_id: str, field: str) -> Any:
    """Look up a single field value from an Airtable record."""
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("fields", {}).get(field)
    except Exception:
        return None


def resolve_contact_name(base_id: str, config: dict) -> str:
    """Resolve contact name from Deal Contacts junction or direct link."""
    dc_ids = config.get("_dc_ids", [])
    if not dc_ids:
        return ""

    junction_table = config.get("deal_contacts_junction_table")
    contacts_table = config.get("contacts_table_id")
    contact_name_field = config.get("contact_name_field", "Full Name")

    if junction_table:
        # BB: junction table -> Contact record
        contact_ids = lookup_field(base_id, junction_table, dc_ids[0], "Contact")
        if contact_ids and isinstance(contact_ids, list) and contact_ids:
            name = lookup_field(
                base_id, contacts_table, contact_ids[0], contact_name_field
            )
            return name or ""
    else:
        # AITB or direct link: IDs point to contacts directly
        if contacts_table:
            name = lookup_field(base_id, contacts_table, dc_ids[0], contact_name_field)
            return name or ""

    return ""


def fetch_deals(
    base_id: str, table_id: str, query: str, config: dict, open_only: bool = False
) -> list[dict[str, Any]]:
    """Fetch deals matching query from an Airtable base."""
    import urllib.parse
    import urllib.request

    norm_query = re.sub(r"[^a-z0-9 ]", "", query.lower())

    # Build search conditions across configured search fields
    search_conditions = [
        f"FIND('{norm_query}', LOWER({{{field}}})) > 0"
        for field in config["search_fields"]
    ]
    search_formula = (
        search_conditions[0]
        if len(search_conditions) == 1
        else f"OR({', '.join(search_conditions)})"
    )

    # Add open-only filter if requested
    if open_only:
        closed_conditions = ", ".join(
            f'{{{config["status_field"]}}}!="{s}"' for s in config["closed_statuses"]
        )
        formula = f"AND({search_formula}, {closed_conditions})"
    else:
        formula = search_formula

    url = (
        f"https://api.airtable.com/v0/{base_id}/{table_id}"
        f"?filterByFormula={urllib.parse.quote(formula)}&maxRecords=10"
    )

    req = urllib.request.Request(url, headers=api_headers())
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())

    return data.get("records", [])


def parse_deal_record(
    record: dict, config: dict, base_id: str, table_id: str
) -> dict[str, Any]:
    """Parse an Airtable deal record into a normalized dict."""
    fields = record.get("fields", {})

    # Handle type — BB has a Type field with display mapping, AITB defaults to "Sponsor"
    if config.get("type_field"):
        raw_type = fields.get(config["type_field"], "")
        deal_type = config.get("type_display", {}).get(raw_type, raw_type)
    else:
        deal_type = config.get("default_type", "")

    # Handle linked fields that may be arrays (lookup values) or record IDs
    org_value = fields.get(config["org_field"], "")
    if isinstance(org_value, list):
        org_value = ", ".join(str(v) for v in org_value) if org_value else ""

    # Resolve contact name: junction table for BB, display value for AITB
    raw_contact = fields.get(config["contact_field"], "")
    if config.get("deal_contacts_junction_table"):
        dc_ids = (
            raw_contact
            if isinstance(raw_contact, list)
            else ([raw_contact] if raw_contact else [])
        )
        resolve_cfg = {**config, "_dc_ids": dc_ids}
        contact_value = resolve_contact_name(base_id, resolve_cfg)
    elif isinstance(raw_contact, list):
        contact_value = ", ".join(str(v) for v in raw_contact) if raw_contact else ""
    else:
        contact_value = str(raw_contact) if raw_contact else ""

    return {
        "name": fields.get(config["name_field"], "Unknown"),
        "status": fields.get(config["status_field"], ""),
        "type": deal_type,
        "organization": org_value,
        "primary_contact": contact_value,
        "amount": fields.get(config["amount_field"]),
        "description": fields.get(config["description_field"], ""),
        "link": airtable_record_url(base_id, table_id, record["id"]),
    }


# ---------------------------------------------------------------------------
# Search orchestration
# ---------------------------------------------------------------------------


def search_all_bases(
    query: str, open_only: bool = False, base_filter: str | None = None
) -> list[dict[str, Any]]:
    """Search deals across configured bases."""
    _ensure_config()
    results = []

    for base_key, config in DEAL_CONFIG.items():
        if base_filter and base_key != base_filter:
            continue

        try:
            records = fetch_deals(
                config["base_id"],
                config["deals_table_id"],
                query,
                config,
                open_only=open_only,
            )
            for record in records:
                parsed = parse_deal_record(
                    record, config, config["base_id"], config["deals_table_id"]
                )
                parsed["source"] = config["source_label"]
                results.append(parsed)
        except Exception as e:
            print(f"[{base_key}] Error searching deals: {e}", file=sys.stderr)

    return results


def filter_and_dedup(
    results: list[dict], query: str, min_score: int = 50
) -> list[dict]:
    """Filter results by fuzzy match score and deduplicate within same source."""
    seen: set[str] = set()
    filtered = []

    for result in results:
        name = result.get("name", "")
        source = result.get("source", "")
        if not name:
            continue

        score = fuzzy_score(query, name)
        if score < min_score:
            continue

        unique_key = f"{source}:{normalize_name(name)}"
        if unique_key in seen:
            continue

        seen.add(unique_key)
        filtered.append(result)

    return filtered


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_json(query: str, results: list[dict]) -> str:
    """Format results as JSON."""
    sources = {r["source"] for r in results}
    return json.dumps(
        {
            "query": query,
            "total_sources": len(sources),
            "results": results,
        },
        indent=2,
    )


def format_human(
    query: str, results: list[dict], base_filter: str | None = None
) -> str:
    """Format results as human-readable text."""
    _ensure_config()
    if not results:
        sources = [
            c["source_label"]
            for k, c in DEAL_CONFIG.items()
            if not base_filter or k == base_filter
        ]
        lines = [f"No deals found for: {query}", ""]
        lines.append("Sources searched:")
        for src in sources:
            lines.append(f"  - {src}")
        return "\n".join(lines)

    best_name = results[0]["name"]
    lines = [
        f"DEAL: {best_name}",
        "",
        f"Found {len(results)} result(s):",
        "",
    ]

    for i, result in enumerate(results, 1):
        lines.append(f"**Result {i}: {result['source']}**")
        if result.get("name"):
            lines.append(f"- Deal: {result['name']}")
        if result.get("status"):
            lines.append(f"- Status: {result['status']}")
        if result.get("type"):
            lines.append(f"- Type: {result['type']}")
        if result.get("organization"):
            lines.append(f"- Organization: {result['organization']}")
        if result.get("primary_contact"):
            lines.append(f"- Contact: {result['primary_contact']}")
        if result.get("amount") is not None:
            lines.append(f"- Amount: ${result['amount']}")
        if result.get("description"):
            lines.append(f"- Description: {result['description']}")
        if result.get("link"):
            lines.append(f"- Link: {result['link']}")
        lines.append("")

    # Show missing sources
    found_sources = {r["source"] for r in results}
    all_sources = [
        c["source_label"]
        for k, c in DEAL_CONFIG.items()
        if not base_filter or k == base_filter
    ]
    missing = [s for s in all_sources if s not in found_sources]

    lines.append("---")
    lines.append("")
    if missing:
        lines.append("Not found in:")
        for m in missing:
            lines.append(f"  - {m}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Search for deals across Airtable bases."
    )
    parser.add_argument("query", help="Deal name or company to search for")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON format")
    parser.add_argument(
        "--open", "-o", action="store_true", help="Show only open deals"
    )
    parser.add_argument("--base", "-b", choices=["bb", "aitb"], help="Filter by base")
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )
    args = parser.parse_args()

    # Load config
    _ensure_config(args.config)

    print("Searching deal tables...", file=sys.stderr)
    raw_results = search_all_bases(
        args.query, open_only=args.open, base_filter=args.base
    )
    results = filter_and_dedup(raw_results, args.query)

    if args.json:
        print(format_json(args.query, results))
    else:
        print(format_human(args.query, results, base_filter=args.base))


if __name__ == "__main__":
    main()
