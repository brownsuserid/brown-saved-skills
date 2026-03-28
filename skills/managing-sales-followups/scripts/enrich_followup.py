#!/usr/bin/env python3
"""
Enrich a follow-up task with deal, contact, org, interactions, and comms context.

Pulls the full record chain for a task -- deal, contact (via Deal Contacts junction),
organization, contact activity logs, recent emails, meeting transcripts, and Beeper
messages -- and outputs JSON for interactive review and drafting.

Config-driven: reads base IDs, table IDs, and field names from YAML config.

Usage:
    python3 enrich_followup.py --task-id recXXXXX
    python3 enrich_followup.py --task-id recXXXXX --include-notes
    python3 enrich_followup.py --task-id recXXXXX --config /path/to.yaml
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import api_headers, airtable_record_url, load_config

SKILLS_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

GMAIL_ACCOUNTS = [
    "aaroneden77@gmail.com",
    "aaron@brainbridge.app",
    "aaron@aitrailblazers.org",
]


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def fetch_record(
    base_id: str, table_id: str, record_id: str, headers: dict
) -> dict[str, Any]:
    """Fetch a single Airtable record by ID."""
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def fetch_records(
    base_id: str, table_id: str, headers: dict, formula: str | None = None
) -> list[dict[str, Any]]:
    """Fetch all records with optional filter."""
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


# ---------------------------------------------------------------------------
# External tool helpers
# ---------------------------------------------------------------------------


def search_emails(contact_name: str, days: int = 30) -> list[dict[str, Any]]:
    """Search all 3 Gmail accounts for recent emails mentioning contact."""
    results: list[dict[str, Any]] = []

    for account in GMAIL_ACCOUNTS:
        try:
            cmd = [
                "gog",
                "gmail",
                "messages",
                "search",
                f"{contact_name} newer_than:{days}d",
                "--account",
                account,
                "--max",
                "10",
                "--json",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                messages = json.loads(proc.stdout)
                if isinstance(messages, list):
                    for msg in messages:
                        msg["account"] = account
                    results.extend(messages)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
            print(
                f"Warning: email search failed for {account}: {exc}",
                file=sys.stderr,
            )

    return results


def search_meeting_transcripts(contact_name: str) -> list[dict[str, Any]]:
    """Search meeting transcripts for contact name."""
    script = str(
        Path(SKILLS_DIR)
        / "maintaining-relationships"
        / "scripts"
        / "searching-meeting-transcripts"
        / "search_transcripts.py"
    )

    try:
        proc = subprocess.run(
            [
                "python3",
                script,
                "--query",
                contact_name,
                "--account",
                "both",
                "--max",
                "5",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
        print(f"Warning: transcript search failed: {exc}", file=sys.stderr)

    return []


def search_beeper(contact_name: str) -> str:
    """Search Beeper for messages with contact."""
    script = str(
        Path(SKILLS_DIR)
        / "maintaining-relationships"
        / "scripts"
        / "using-beeper"
        / "beeper-find.sh"
    )

    try:
        proc = subprocess.run(
            [script, contact_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (subprocess.TimeoutExpired, Exception) as exc:
        print(f"Warning: beeper search failed: {exc}", file=sys.stderr)

    return ""


# ---------------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------------


def resolve_contact_via_junction(
    deal_id: str,
    base_id: str,
    deals_table: str,
    contacts_table: str,
    deal_contacts_table: str,
    headers: dict,
) -> dict[str, Any] | None:
    """Resolve contact through Deal Contacts junction table."""
    try:
        deal = fetch_record(base_id, deals_table, deal_id, headers)
        df = deal.get("fields", {})

        # Try direct "Primary Contact" first (some deals may have it)
        contact_ids = df.get("Primary Contact", [])
        if contact_ids:
            return fetch_record(base_id, contacts_table, contact_ids[0], headers)

        # Fall back to Deal Contacts junction table
        dc_ids = df.get("Deal Contacts", [])
        if not dc_ids:
            return None

        # Fetch the first junction record to get the Contact ID
        junction = fetch_record(base_id, deal_contacts_table, dc_ids[0], headers)
        jf = junction.get("fields", {})
        linked_contact_ids = jf.get("Contact", [])
        if not linked_contact_ids:
            return None

        return fetch_record(base_id, contacts_table, linked_contact_ids[0], headers)

    except Exception as exc:
        print(
            f"Warning: could not resolve contact via junction: {exc}", file=sys.stderr
        )
        return None


def fetch_activity_logs(
    contact_id: str,
    base_id: str,
    contacts_table: str,
    activity_logs_table: str,
    headers: dict,
    max_logs: int = 10,
) -> list[dict[str, Any]]:
    """Fetch Contact Activity Logs for a contact."""
    try:
        contact = fetch_record(base_id, contacts_table, contact_id, headers)
        cf = contact.get("fields", {})
        log_ids = cf.get("Contact Activity Logs", [])

        if not log_ids:
            return []

        logs: list[dict[str, Any]] = []
        for log_id in log_ids[:max_logs]:
            try:
                log = fetch_record(base_id, activity_logs_table, log_id, headers)
                lf = log.get("fields", {})
                logs.append(
                    {
                        "id": log_id,
                        "activity_type": lf.get("Activity Type", ""),
                        "details": lf.get("Details", ""),
                        "created": lf.get("Created", ""),
                    }
                )
            except Exception as exc:
                print(f"Warning: could not fetch log {log_id}: {exc}", file=sys.stderr)

        # Sort by created date descending
        logs.sort(key=lambda x: x.get("created", ""), reverse=True)
        return logs

    except Exception as exc:
        print(f"Warning: could not fetch activity logs: {exc}", file=sys.stderr)
        return []


def enrich_task(
    task_id: str, config: dict, base_key: str = "bb", include_notes: bool = False
) -> dict[str, Any]:
    """Build full context for a follow-up task."""
    headers = api_headers()
    base_cfg = config["bases"][base_key]
    tables = base_cfg.get("tables", {})

    base_id = base_cfg["base_id"]
    tasks_table = base_cfg["tasks_table_id"]
    deals_table = base_cfg.get("deals_table_id", tables.get("deals", ""))
    orgs_table = base_cfg.get("orgs_table", tables.get("organizations", ""))
    contacts_table = base_cfg.get("contacts_table_id", tables.get("contacts", ""))
    deal_contacts_table = tables.get("deal_contacts", "tblxdCIQQ7Uu0g1qS")
    activity_logs_table = tables.get("contact_activity_logs", "tblgf9zD001tj6mL5")

    print(f"Fetching task {task_id}...", file=sys.stderr)
    task = fetch_record(base_id, tasks_table, task_id, headers)
    tf = task.get("fields", {})

    result: dict[str, Any] = {
        "task": {
            "id": task_id,
            "name": tf.get("Task", ""),
            "status": tf.get("Status", ""),
            "definition_of_done": tf.get("Definition of Done", ""),
            "notes": tf.get("Notes", ""),
            "deadline": tf.get("Deadline"),
            "airtable_url": airtable_record_url(base_id, tasks_table, task_id),
        },
        "deal": None,
        "contact": None,
        "organization": None,
        "deal_notes": [],
        "activity_logs": [],
        "recent_emails": [],
        "meeting_transcripts": [],
        "beeper_messages": "",
    }

    deal_ids = tf.get("Deals", [])
    if not deal_ids:
        print("No linked deal found for this task.", file=sys.stderr)
        return result

    deal_id = deal_ids[0]
    print(f"Fetching deal {deal_id}...", file=sys.stderr)
    deal = fetch_record(base_id, deals_table, deal_id, headers)
    df = deal.get("fields", {})

    result["deal"] = {
        "id": deal_id,
        "name": df.get("Name", ""),
        "status": df.get("Status", ""),
        "type": df.get("Type", ""),
        "description": df.get("Description", ""),
        "pain_points": df.get("Pain Points", ""),
        "stakeholder_map": df.get("Stakeholder Map", ""),
        "airtable_url": airtable_record_url(base_id, deals_table, deal_id),
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

    # Contact: resolve via Deal Contacts junction table
    print(f"Resolving contact for deal {deal_id}...", file=sys.stderr)
    contact_record = resolve_contact_via_junction(
        deal_id, base_id, deals_table, contacts_table, deal_contacts_table, headers
    )
    contact_name = ""

    if contact_record:
        cf = contact_record.get("fields", {})
        contact_id = contact_record["id"]
        contact_name = cf.get("Full Name", cf.get("Name", ""))
        result["contact"] = {
            "id": contact_id,
            "name": contact_name,
            "email": cf.get("Email (Work)", cf.get("Email (Personal)", "")),
            "phone": cf.get("Phone (Mobile)", cf.get("Phone (Work)", "")),
            "title": cf.get("Title", ""),
            "linkedin": cf.get("LinkedIn", ""),
        }

        # Contact Activity Logs
        print(f"Fetching activity logs for {contact_name}...", file=sys.stderr)
        result["activity_logs"] = fetch_activity_logs(
            contact_id, base_id, contacts_table, activity_logs_table, headers
        )
    else:
        print("Warning: no contact found for this deal.", file=sys.stderr)

    # External sources (only if we have a contact name to search)
    if contact_name:
        print(
            f"Searching emails for '{contact_name}' (last 30 days)...", file=sys.stderr
        )
        result["recent_emails"] = search_emails(contact_name, days=30)

        print(f"Searching meeting transcripts for '{contact_name}'...", file=sys.stderr)
        result["meeting_transcripts"] = search_meeting_transcripts(contact_name)

        print(f"Searching Beeper for '{contact_name}'...", file=sys.stderr)
        result["beeper_messages"] = search_beeper(contact_name)

    # Deal notes (optional)
    if include_notes:
        note_ids = df.get("Notes", [])
        notes_table = tables.get("notes", "Notes")
        if note_ids:
            print(f"Fetching {min(len(note_ids), 3)} deal notes...", file=sys.stderr)
            for note_id in note_ids[:3]:
                try:
                    note = fetch_record(base_id, notes_table, note_id, headers)
                    nf = note.get("fields", {})
                    result["deal_notes"].append(
                        {
                            "id": note_id,
                            "title": nf.get("Title", ""),
                            "created": nf.get("Created", ""),
                        }
                    )
                except Exception as exc:
                    print(
                        f"Warning: could not fetch note {note_id}: {exc}",
                        file=sys.stderr,
                    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich a follow-up task with deal, contact, org, and comms context."
    )
    parser.add_argument("--task-id", required=True, help="Airtable task record ID")
    parser.add_argument(
        "--include-notes",
        action="store_true",
        help="Also fetch linked deal notes (slower)",
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

    try:
        result = enrich_task(
            args.task_id,
            config,
            base_key=args.base,
            include_notes=args.include_notes,
        )
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
