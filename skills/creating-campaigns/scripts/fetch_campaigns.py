#!/usr/bin/env python3
"""
Fetch BB campaign records from Airtable with flexible filtering.

Supports filtering by assignee, status, name substring, and source.
Returns all fields relevant to campaign planning and messaging by default.

Usage:
    # All campaigns
    python fetch_campaigns.py

    # Campaigns assigned to Aaron
    python fetch_campaigns.py --assignee aaron

    # In-progress campaigns for any assignee
    python fetch_campaigns.py --status "In Progress"

    # Drafts assigned to Josh, JSON output
    python fetch_campaigns.py --assignee josh --status Drafting --json

    # Name substring match
    python fetch_campaigns.py --name "Q2"

    # Combine filters
    python fetch_campaigns.py --assignee aaron --status Drafting --name "Healthcare"
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"),
)

from airtable_config import api_headers, airtable_record_url, load_config  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FIELDS = [
    "Name",
    "Status",
    "Source",
    "Assignee",
    "Campaign Plan",
    "Message Guardrails",
    "Campaign Code",
    "Started",
    "Ended",
]

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

_config: dict | None = None


def _ensure_config(config_path: str | None = None) -> dict:
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def _bb(config: dict) -> dict:
    return config["bases"]["bb"]


def _people(config: dict) -> dict:
    return config.get("people", {})


def resolve_assignee(name: str, config: dict) -> str | None:
    """Resolve a name key or raw email/name to a normalized lowercase token for client-side matching.

    The Campaigns table uses a Collaborator field for Assignee (user objects with id/email/name),
    not a linked record, so server-side filtering by record ID does not work. We fetch all records
    and filter client-side by matching against the collaborator's name or email.

    Returns None if name is 'all' or empty (no filter).
    """
    if not name or name.lower() == "all":
        return None
    # Return the raw string lowercased — matched against collaborator name/email downstream
    return name.lower()


# ---------------------------------------------------------------------------
# Airtable fetch
# ---------------------------------------------------------------------------


def _fetch_all_pages(
    base_id: str,
    table_id: str,
    formula: str,
    fields: list[str],
) -> list[dict]:
    """Fetch all pages of records from an Airtable table."""
    records: list[dict] = []
    offset: str | None = None

    while True:
        params: dict[str, str] = {"pageSize": "100"}
        if formula:
            params["filterByFormula"] = formula
        for i, f in enumerate(fields):
            params[f"fields[{i}]"] = f
        if offset:
            params["offset"] = offset

        qs = urllib.parse.urlencode(params)
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}?{qs}"
        req = urllib.request.Request(url, headers=api_headers())
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break

    return records


def build_formula(
    status: str | None,
    name_query: str | None,
    source: str | None,
) -> str:
    """Build an Airtable filterByFormula expression from the given server-side filters.

    Note: Assignee filtering is done client-side because the Campaigns table uses
    a Collaborator field (user object), not a linked record field.
    """
    conditions: list[str] = []

    if status and status.lower() != "all":
        safe = status.replace("'", "\\'")
        conditions.append(f"{{Status}}='{safe}'")

    if name_query:
        safe = name_query.replace("'", "\\'")
        conditions.append(f"FIND(LOWER('{safe}'), LOWER({{Name}})) > 0")

    if source:
        safe = source.replace("'", "\\'")
        conditions.append(f"{{Source}}='{safe}'")

    if not conditions:
        return ""
    if len(conditions) == 1:
        return conditions[0]
    return f"AND({', '.join(conditions)})"


def _assignee_matches(record: dict, token: str) -> bool:
    """Check if a record's Assignee collaborator field matches the given token.

    Matches against the collaborator's lowercased name and email.
    """
    assignee = record.get("fields", {}).get("Assignee")
    if not assignee:
        return False
    if isinstance(assignee, dict):
        # Single collaborator object
        name = (assignee.get("name") or "").lower()
        email = (assignee.get("email") or "").lower()
        return token in name or token in email
    if isinstance(assignee, list):
        # Multi-collaborator (future-proofing)
        for a in assignee:
            name = (a.get("name") or "").lower()
            email = (a.get("email") or "").lower()
            if token in name or token in email:
                return True
    return False


def fetch_campaigns(
    assignee: str | None = None,
    status: str | None = None,
    name_query: str | None = None,
    source: str | None = None,
    fields: list[str] | None = None,
    config_path: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch BB campaign records with optional filters.

    Args:
        assignee: Name key ('aaron', 'josh', ...), record ID ('rec...'), or None for all.
        status: Exact status value ('Drafting', 'In Progress', ...), or None/'all' for all.
        name_query: Case-insensitive substring to match against campaign Name.
        source: Exact Source field value.
        fields: Fields to retrieve. Defaults to DEFAULT_FIELDS.
        config_path: Path to YAML config file.

    Returns:
        List of raw Airtable record dicts (id + fields).
    """
    config = _ensure_config(config_path)
    bb = _bb(config)

    base_id = bb["base_id"]
    table_id = bb["tables"]["campaigns"]
    fetch_fields = fields or DEFAULT_FIELDS

    assignee_token = resolve_assignee(assignee, config) if assignee else None
    formula = build_formula(status, name_query, source)

    records = _fetch_all_pages(base_id, table_id, formula, fetch_fields)
    if assignee_token:
        records = [r for r in records if _assignee_matches(r, assignee_token)]
    return records


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_json(records: list[dict], config: dict) -> str:
    bb = _bb(config)
    base_id = bb["base_id"]
    table_id = bb["tables"]["campaigns"]

    output = []
    for r in records:
        fields = r.get("fields", {})
        output.append({
            "id": r["id"],
            "link": airtable_record_url(base_id, table_id, r["id"]),
            **fields,
        })
    return json.dumps(output, indent=2)


def format_human(records: list[dict], config: dict) -> str:
    bb = _bb(config)
    base_id = bb["base_id"]
    table_id = bb["tables"]["campaigns"]

    if not records:
        return "No campaigns found matching the given filters."

    lines = [f"Found {len(records)} campaign(s):\n"]
    for r in records:
        f = r.get("fields", {})
        lines.append(f"  {f.get('Name', '(unnamed)')}  [{f.get('Status', '')}]")
        lines.append(f"    Source: {f.get('Source', '')}")
        lines.append(f"    Link:   {airtable_record_url(base_id, table_id, r['id'])}")
        if f.get("Campaign Code"):
            lines.append(f"    Code:   {f['Campaign Code']}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch BB campaign records from Airtable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--assignee", "-a",
        help="Filter by assignee: name key (aaron, josh, pablo, ...), record ID, or 'all' (default: all)",
    )
    parser.add_argument(
        "--status", "-s",
        help="Filter by exact Status value (e.g. 'Drafting', 'In Progress'). Omit for all.",
    )
    parser.add_argument(
        "--name", "-n",
        help="Case-insensitive substring match on campaign Name.",
    )
    parser.add_argument(
        "--source",
        help="Filter by exact Source field value (e.g. 'BB Campaign').",
    )
    parser.add_argument(
        "--fields", "-f",
        nargs="+",
        metavar="FIELD",
        help=f"Fields to retrieve (default: {DEFAULT_FIELDS})",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output JSON instead of human-readable summary.",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file.",
    )
    args = parser.parse_args()

    config = _ensure_config(args.config)

    print("Fetching campaigns...", file=sys.stderr)
    records = fetch_campaigns(
        assignee=args.assignee,
        status=args.status,
        name_query=args.name,
        source=args.source,
        fields=args.fields,
        config_path=args.config,
    )
    print(f"  {len(records)} record(s) returned.", file=sys.stderr)

    if args.json:
        print(format_json(records, config))
    else:
        print(format_human(records, config))


if __name__ == "__main__":
    main()
