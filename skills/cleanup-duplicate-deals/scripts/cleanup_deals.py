"""
Cleanup duplicate deals in an Airtable deals table.

Problem: When new Notes are created for deals, a new shell deal record
is sometimes created instead of linking the Note to the existing deal.
These shell records have only a Name and a single Note link, with no
Organization, Contact, Status, Assignee, or Type.

Additionally, some shell records are created with a "Name: " prefix
(e.g., "Name: Partnership with Complaxion" instead of "Partnership with Complaxion").

This script:
1. Fetches all deals from the deals table
2. Groups them by normalized name (stripping "name: " prefix)
3. Identifies the primary record (most populated fields, then oldest)
4. For each shell duplicate:
   a. Moves its Note links to the primary record
   b. Deletes the shell record
5. Supports --dry-run (default) and --execute modes

Config-driven: reads base IDs and table IDs from YAML config.

Usage:
    python cleanup_deals.py                                # dry-run all
    python cleanup_deals.py --execute                      # execute all
    python cleanup_deals.py --deal "3keylogic"             # dry-run single deal
    python cleanup_deals.py --deal "3keylogic" --execute   # execute single deal
    python cleanup_deals.py --config /path/to.yaml         # custom config
"""

import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import api_headers, load_config

# Fields that indicate a "rich" (real) record vs a "shell" (duplicate)
RICH_FIELDS = ["Organization", "Deal Contacts", "Status", "Assignee", "Type"]


def fetch_all_deals(base_id: str, deals_table_id: str, headers: dict) -> list[dict]:
    """Fetch all records from the deals table with pagination."""
    all_records = []
    offset = None
    while True:
        url = f"https://api.airtable.com/v0/{base_id}/{deals_table_id}?pageSize=100"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        all_records.extend(data["records"])
        offset = data.get("offset")
        if not offset:
            break
    return all_records


def normalize_name(name: str) -> str:
    """Normalize deal name for grouping: lowercase, strip 'name: ' prefix."""
    n = name.strip().lower()
    if n.startswith("name: "):
        n = n[6:]
    return n


def richness_score(record: dict) -> int:
    """Count how many rich fields a record has populated."""
    fields = record["fields"]
    return sum(1 for f in RICH_FIELDS if fields.get(f))


def pick_primary(records: list[dict]) -> dict:
    """Pick the primary record: highest richness, then most notes, then oldest."""
    return max(
        records,
        key=lambda r: (
            richness_score(r),
            len(r["fields"].get("Notes", [])),
            -len(r["createdTime"]),  # tie-break: doesn't matter much
        ),
    )


def update_record_notes(
    record_id: str,
    note_ids: list[str],
    base_id: str,
    deals_table_id: str,
    headers: dict,
) -> None:
    """Update a deal record's Notes field to include the given note IDs."""
    url = f"https://api.airtable.com/v0/{base_id}/{deals_table_id}/{record_id}"
    payload = json.dumps({"fields": {"Notes": note_ids}}).encode()
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        resp.read()


def delete_records(
    record_ids: list[str], base_id: str, deals_table_id: str, headers: dict
) -> None:
    """Delete records in batches of 10 (Airtable limit)."""
    for i in range(0, len(record_ids), 10):
        batch = record_ids[i : i + 10]
        params = "&".join(f"records[]={rid}" for rid in batch)
        url = f"https://api.airtable.com/v0/{base_id}/{deals_table_id}?{params}"
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req) as resp:
            resp.read()
        if i + 10 < len(record_ids):
            time.sleep(0.25)  # rate limit courtesy


def process_group(
    name: str,
    records: list[dict],
    execute: bool,
    base_id: str,
    deals_table_id: str,
    headers: dict,
) -> tuple[int, int] | None:
    """Process a single duplicate group. Returns (shells_count, notes_moved) or None if skipped."""
    primary = pick_primary(records)
    shells = [r for r in records if r["id"] != primary["id"]]
    primary_score = richness_score(primary)

    # Skip ambiguous cases where multiple records have high richness
    ambiguous = [s for s in shells if richness_score(s) >= 3]
    if ambiguous:
        print(
            f"  SKIPPING '{name}' - {len(ambiguous) + 1} records with rich data, needs manual review:"
        )
        for r in records:
            f = r["fields"]
            print(
                f"    {r['id']} score={richness_score(r)} notes={len(f.get('Notes', []))} "
                f'created={r["createdTime"][:10]} name="{f.get("Name", "")}"'
            )
        print()
        return None

    # Collect notes from shells to move to primary
    primary_notes = list(primary["fields"].get("Notes", []))
    notes_to_add = []
    for s in shells:
        shell_notes = s["fields"].get("Notes", [])
        for note_id in shell_notes:
            if note_id not in primary_notes and note_id not in notes_to_add:
                notes_to_add.append(note_id)

    shell_ids = [s["id"] for s in shells]

    # Display plan
    primary_name = primary["fields"].get("Name", "")
    print(
        f"  '{name}' (primary: {primary['id']}, \"{primary_name}\", score={primary_score})"
    )
    print(f"    Shells to delete: {len(shells)}")
    if notes_to_add:
        print(f"    Notes to move to primary: {len(notes_to_add)}")

    if execute:
        # Move notes
        if notes_to_add:
            merged_notes = primary_notes + notes_to_add
            update_record_notes(
                primary["id"], merged_notes, base_id, deals_table_id, headers
            )
            time.sleep(0.2)

        # Delete shells
        delete_records(shell_ids, base_id, deals_table_id, headers)
        print("    DONE")
        time.sleep(0.2)

    print()
    return (len(shells), len(notes_to_add))


def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicate deals")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform cleanup (default: dry-run)",
    )
    parser.add_argument(
        "--deal",
        type=str,
        default=None,
        help="Process only this deal name (case-insensitive substring match)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )
    parser.add_argument(
        "--base",
        default="bb",
        help="Base key to use (default: bb)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    headers = api_headers()
    base_cfg = config["bases"][args.base]
    base_id = base_cfg["base_id"]
    deals_table_id = base_cfg.get(
        "deals_table_id", base_cfg.get("tables", {}).get("deals", "")
    )

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    scope = f" for '{args.deal}'" if args.deal else ""
    print(f"=== {args.base.upper()} Deals Duplicate Cleanup ({mode}{scope}) ===\n")

    # 1. Fetch all deals
    print("Fetching all deals...")
    all_records = fetch_all_deals(base_id, deals_table_id, headers)
    print(f"Total records: {len(all_records)}\n")

    # 2. Group by normalized name
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in all_records:
        name = r["fields"].get("Name", "").strip()
        if name:
            by_name[normalize_name(name)].append(r)

    # 3. Find groups with duplicates
    duplicate_groups = {k: v for k, v in by_name.items() if len(v) > 1}

    # 4. Filter to single deal if requested
    if args.deal:
        deal_filter = args.deal.strip().lower()
        matched = {k: v for k, v in duplicate_groups.items() if deal_filter in k}
        if not matched:
            print(f"No duplicate group found matching '{args.deal}'")
            print(f"Available groups: {sorted(duplicate_groups.keys())}")
            sys.exit(1)
        duplicate_groups = matched

    print(f"Deal names with duplicates: {len(duplicate_groups)}\n")

    total_shells = 0
    total_notes_moved = 0

    for name in sorted(duplicate_groups.keys()):
        records = duplicate_groups[name]
        result = process_group(
            name, records, args.execute, base_id, deals_table_id, headers
        )
        if result:
            total_shells += result[0]
            total_notes_moved += result[1]

    # Summary
    print("=" * 60)
    print(f"Total duplicate groups: {len(duplicate_groups)}")
    print(f"Total shell records to delete: {total_shells}")
    print(f"Total notes to relocate: {total_notes_moved}")
    if not args.execute:
        print("\nThis was a DRY RUN. To execute, run with --execute")
        if args.deal:
            print(f'  python {__file__} --deal "{args.deal}" --execute')
        else:
            print(f"  python {__file__} --execute")


if __name__ == "__main__":
    main()
