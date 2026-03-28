#!/usr/bin/env python3
"""
Weekly stale deal follow-up task generator.

Reviews all deals in qualification stage or later from BB and AITB pipelines,
checks for recent interactions (emails, meetings/transcripts, touchpoints),
and creates follow-up tasks for deals with no touch in 7+ days.

Requirements:
- Include both BB and AITB pipelines
- Qualification stage or later
- For each stale deal (>7 days since last meaningful touchpoint), create exactly
  one task if no equivalent open follow-up task already exists
- Task assigned to Aaron
- Task title: "Follow up with <Contact/Org> re: <Deal>"
- Task description includes: why stale (last touchpoint date/type), suggested
  follow-up focus, recommended channel, key context from recent interactions

Usage:
    python3 generate_stale_deal_followups.py [--dry-run] [--output-json]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

from _config import BASES, PEOPLE, api_headers, airtable_record_url

# Aaron's record IDs per base
AARON_IDS = {
    "bb": PEOPLE["aaron"]["bb"],
    "aitb": PEOPLE["aaron"]["aitb"],
}

# BB pipeline stages (these are the Stage Name values from the Pipeline Stages table)
# Note: BB uses linked records, so we need to look up stage IDs
BB_STAGE_IDS_TO_NAMES = {
    "rec05mmqWkadN6TDn": "02-Contacted",
    "rec3HZUsB9prEaUGv": "03-Qualification",
    "rec3th5vMQEyzCkxx": "04-Interest Expressed",
    "recC61RlY5ZXUGylE": "05-Empathy Interview",
    "recDEbErJd4m8PVyS": "06-Aligning Scope",
    "recGXQK8cnJhJZmKU": "07-Proposal Meeting Booked",
    "recPA9aoE2dZQuFQY": "08-Reviewing Proposal",
    "recPQkGzdqk3XpQoC": "09-Negotiation/Review",
    "recZH5Dikh3E6LhLr": "10-Signed Proposal - Won",
    "recbaQXMSudZjYDz0": "11-Closed Lost",
    "recd7yx8okT58BBhb": "12-Closed Lost to Competitor",
    "recf0FIMRj6QF9Rwb": "01-Identified",
    "recp517hrxj6kxJg4": "00-Backlog",
    "recuQkWl3niAkKBLB": "S0-Identified",
}

# Qualification stage or later (stage name prefixes in BB)
BB_QUALIFICATION_PREFIXES = [
    "03-Qualification",
    "04-Interest Expressed",
    "05-Empathy Interview",
    "06-Aligning Scope",
    "07-Proposal Meeting Booked",
    "08-Reviewing Proposal",
    "09-Negotiation/Review",
]

# AITB stages (single select)
AITB_QUALIFICATION_STAGES = [
    "Interest Expressed",
    "Empathy Interview",
    "Scope Identified",
    "Budget Identified",
]

# Stale threshold in days
STALE_DAYS = 7

# Gmail accounts to search for emails
GMAIL_ACCOUNTS = [
    "aaroneden77@gmail.com",
    "aaron@brainbridge.app",
    "aaron@aitrailblazers.org",
]

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def fetch_records(
    base_id: str,
    table_id: str,
    formula: str | None = None,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch records from Airtable with pagination."""
    import urllib.parse
    import urllib.request

    records = []
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

        # Add fields as separate params
        if fields:
            field_params = "&".join(
                f"fields%5B%5D={urllib.parse.quote(f)}" for f in fields
            )
            full_url = (
                f"{full_url}&{field_params}" if query else f"{full_url}?{field_params}"
            )

        req = urllib.request.Request(full_url, headers=api_headers())

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    return records


def fetch_record(base_id: str, table_id: str, record_id: str) -> dict[str, Any]:
    """Fetch a single Airtable record by ID."""
    import urllib.request

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    req = urllib.request.Request(url, headers=api_headers())

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def lookup_record(base_id: str, table_id: str, record_id: str, field_name: str) -> Any:
    """Lookup a single field value from a record by field name."""
    try:
        record = fetch_record(base_id, table_id, record_id)
        return record.get("fields", {}).get(field_name)
    except Exception:
        return None


def get_bb_stage_name(deal_fields: dict) -> str | None:
    """Get the stage name for a BB deal (handles linked records)."""
    status_ids = deal_fields.get("Status", [])
    if not status_ids:
        return None
    stage_id = status_ids[0] if isinstance(status_ids, list) else status_ids
    return BB_STAGE_IDS_TO_NAMES.get(stage_id, "Unknown")


def search_emails_for_contact(
    contact_name: str, days: int = 30
) -> list[dict[str, Any]]:
    """Search all Gmail accounts for recent emails mentioning contact."""
    results = []

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
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    messages = json.loads(proc.stdout)
                    if isinstance(messages, list):
                        for msg in messages:
                            msg["account"] = account
                            # Parse date from internalDate (milliseconds since epoch)
                            internal_date = msg.get("internalDate")
                            if internal_date:
                                msg["date"] = datetime.fromtimestamp(
                                    int(internal_date) / 1000
                                ).isoformat()
                        results.extend(messages)
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, Exception):
            pass

    return results


def search_meeting_transcripts(contact_name: str) -> list[dict[str, Any]]:
    """Search meeting transcripts for contact name."""
    script = os.path.join(
        SKILLS_DIR,
        "maintaining-relationships",
        "scripts",
        "searching-meeting-transcripts",
        "search_transcripts.py",
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
            try:
                data = json.loads(proc.stdout)
                # Handle both list and dict responses
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "results" in data:
                    return data["results"]
                return []
            except json.JSONDecodeError:
                return []
    except (subprocess.TimeoutExpired, Exception):
        pass

    return []


def get_last_touchpoint_date(
    deal: dict, base_key: str
) -> tuple[datetime | None, str | None, str | None]:
    """
    Find the most recent touchpoint for a deal.
    Returns (date, type, source) or (None, None, None) if no touchpoints found.

    Checks in order of priority:
    1. Contact Activity Logs (most reliable - BB only)
    2. Gmail emails
    3. Meeting transcripts
    4. Deal notes
    """
    deal_id = deal["id"]
    deal_fields = deal.get("fields", {})
    config = BASES[base_key]

    latest_date = None
    latest_type = None
    latest_source = None

    # Get contact for this deal
    contact_id = None
    contact_name = None

    if base_key == "bb":
        # BB uses Deal Contacts junction table
        dc_ids = deal_fields.get("Deal Contacts", [])
        if dc_ids:
            try:
                junction = fetch_record(
                    config["base_id"], "tblxdCIQQ7Uu0g1qS", dc_ids[0]
                )
                contact_ids = junction.get("fields", {}).get("Contact", [])
                if contact_ids:
                    contact_id = contact_ids[0]
                    contact = fetch_record(
                        config["base_id"], config["contacts_table_id"], contact_id
                    )
                    contact_name = contact.get("fields", {}).get("Full Name", "")
            except Exception:
                pass
    else:
        # AITB uses direct Contact link
        contact_ids = deal_fields.get("Contact", [])
        if contact_ids:
            contact_id = contact_ids[0]
            try:
                contact = fetch_record(
                    config["base_id"], config["contacts_table_id"], contact_id
                )
                contact_name = contact.get("fields", {}).get("Name", "")
            except Exception:
                pass

    # 1. Check Contact Activity Logs (BB only)
    if contact_id and base_key == "bb":
        try:
            contact = fetch_record(
                config["base_id"], config["contacts_table_id"], contact_id
            )
            log_ids = contact.get("fields", {}).get("Contact Activity Logs", [])

            for log_id in log_ids:
                try:
                    log = fetch_record(config["base_id"], "tblgf9zD001tj6mL5", log_id)
                    log_fields = log.get("fields", {})
                    created = log_fields.get("Created")
                    if created:
                        log_date = datetime.fromisoformat(
                            created.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                        if latest_date is None or log_date > latest_date:
                            latest_date = log_date
                            latest_type = log_fields.get("Activity Type", "Activity")
                            latest_source = "Contact Activity Log"
                except Exception:
                    pass
        except Exception:
            pass

    # 2. Check Gmail for emails
    if contact_name:
        emails = search_emails_for_contact(contact_name, days=90)
        for email in emails:
            email_date = email.get("date")
            if email_date:
                try:
                    parsed_date = datetime.fromisoformat(
                        email_date.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    if latest_date is None or parsed_date > latest_date:
                        latest_date = parsed_date
                        latest_type = "Email"
                        latest_source = f"Gmail ({email.get('account', 'unknown')})"
                except Exception:
                    pass

    # 3. Check meeting transcripts
    if contact_name:
        try:
            transcripts = search_meeting_transcripts(contact_name)
            for transcript in transcripts:
                # Extract date from filename or title if possible
                title = (
                    transcript.get("title", "")
                    if isinstance(transcript, dict)
                    else str(transcript)
                )
                try:
                    # Try to parse date from beginning of title
                    if len(title) >= 10 and title[4] == "-" and title[7] == "-":
                        year, month, day = (
                            int(title[0:4]),
                            int(title[5:7]),
                            int(title[8:10]),
                        )
                        transcript_date = datetime(year, month, day)
                        if latest_date is None or transcript_date > latest_date:
                            latest_date = transcript_date
                            latest_type = "Meeting"
                            latest_source = f"Transcript: {title[:50]}"
                except Exception:
                    pass
        except Exception:
            pass

    # 4. Check Deal Notes
    note_ids = deal_fields.get("Notes", [])
    for note_id in note_ids:
        try:
            note = fetch_record(config["base_id"], "Notes", note_id)
            note_fields = note.get("fields", {})
            created = note_fields.get("Created")
            if created:
                note_date = datetime.fromisoformat(
                    created.replace("Z", "+00:00")
                ).replace(tzinfo=None)
                if latest_date is None or note_date > latest_date:
                    latest_date = note_date
                    latest_type = "Note"
                    latest_source = (
                        f"Deal Note: {note_fields.get('Title', 'Untitled')[:50]}"
                    )
        except Exception:
            pass

    return latest_date, latest_type, latest_source


def has_existing_followup_task(deal_id: str, base_key: str) -> bool:
    """Check if deal already has an open follow-up task."""
    config = BASES[base_key]

    # Search for tasks linked to this deal that are assigned to Aaron and open
    # The Deals field is a linked record field
    try:
        # Get all open tasks for Aaron in this base
        formula = f'AND(FIND("{AARON_IDS[base_key]}", ARRAYJOIN({{Assignee}}, ",")), Status!="Completed", Status!="Archived", Status!="Cancelled")'
        tasks = fetch_records(
            config["base_id"],
            config["tasks_table_id"],
            formula=formula,
            fields=["Task", "Deals"],
        )

        for task in tasks:
            task_fields = task.get("fields", {})
            task_name = task_fields.get("Task", "").lower()
            linked_deals = task_fields.get("Deals", [])

            # Check if this task is linked to our deal and has follow-up keywords
            if deal_id in linked_deals:
                if any(
                    kw in task_name for kw in ["follow up", "follow-up", "followup"]
                ):
                    return True

    except Exception:
        pass

    return False


def get_org_name(deal: dict, base_key: str) -> str | None:
    """Get organization name for a deal."""
    deal_fields = deal.get("fields", {})
    config = BASES[base_key]

    if base_key == "bb":
        org_ids = deal_fields.get("Organization", [])
        if org_ids:
            return lookup_record(
                config["base_id"], config["orgs_table"], org_ids[0], "Name"
            )
    else:
        # AITB has Organization Name as a lookup
        org_names = deal_fields.get("Organization Name", [])
        if org_names:
            return org_names[0]

    return None


def get_primary_contact_name(deal: dict, base_key: str) -> str | None:
    """Get primary contact name for a deal."""
    deal_fields = deal.get("fields", {})
    config = BASES[base_key]

    if base_key == "bb":
        # BB uses Deal Contacts junction table
        dc_ids = deal_fields.get("Deal Contacts", [])
        if dc_ids:
            try:
                junction = fetch_record(
                    config["base_id"], "tblxdCIQQ7Uu0g1qS", dc_ids[0]
                )
                contact_ids = junction.get("fields", {}).get("Contact", [])
                if contact_ids:
                    return lookup_record(
                        config["base_id"],
                        config["contacts_table_id"],
                        contact_ids[0],
                        "Full Name",
                    )
            except Exception:
                pass
    else:
        # AITB uses direct Contact link
        contact_ids = deal_fields.get("Contact", [])
        if contact_ids:
            return lookup_record(
                config["base_id"], config["contacts_table_id"], contact_ids[0], "Name"
            )

    return None


def get_deal_value(deal: dict, base_key: str) -> str | None:
    """Get deal value/amount."""
    deal_fields = deal.get("fields", {})

    if base_key == "bb":
        return deal_fields.get("Amount")
    else:
        return deal_fields.get("Deal Value")


def create_followup_task(
    deal: dict,
    base_key: str,
    days_stale: int,
    last_touch_type: str | None,
    last_touch_source: str | None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a follow-up task for a stale deal."""
    config = BASES[base_key]
    deal_id = deal["id"]
    deal_fields = deal.get("fields", {})

    # Get deal name
    if base_key == "bb":
        deal_name = deal_fields.get("Name", "Untitled Deal")
    else:
        deal_name = deal_fields.get("Project Title", "Untitled Deal")

    # Get org and contact names
    org_name = get_org_name(deal, base_key)
    contact_name = get_primary_contact_name(deal, base_key)

    # Build task title
    if contact_name:
        task_title = f"Follow up with {contact_name} re: {deal_name}"
    elif org_name:
        task_title = f"Follow up with {org_name} re: {deal_name}"
    else:
        task_title = f"Follow up re: {deal_name}"

    # Build task description
    description_lines = [
        "Done when follow-up has been sent and logged in Airtable.",
        "",
        "---",
        "WHY STALE:",
        f"- Last touchpoint: {last_touch_type or 'Unknown'} ({days_stale} days ago)",
        f"- Source: {last_touch_source or 'Unknown'}",
        "",
        "SUGGESTED FOLLOW-UP:",
    ]

    # Suggest follow-up focus based on deal stage
    if base_key == "bb":
        deal_stage = get_bb_stage_name(deal_fields)
    else:
        deal_stage = deal_fields.get("Stage")

    stage_lower = (deal_stage or "").lower()

    if any(
        x in stage_lower for x in ["contacted", "qualification", "interest", "backlog"]
    ):
        description_lines.append("- Re-engage to assess current interest level")
        description_lines.append("- Offer a brief intro call or resource")
    elif any(x in stage_lower for x in ["empathy", "interview"]):
        description_lines.append("- Follow up on empathy interview insights")
        description_lines.append("- Propose next steps or scope discussion")
    elif any(x in stage_lower for x in ["demo", "inspiration", "scope", "aligning"]):
        description_lines.append("- Follow up on demo/scope discussion")
        description_lines.append("- Address any questions or concerns")
    elif any(
        x in stage_lower
        for x in ["proposal", "price", "budget", "review", "negotiation", "reviewing"]
    ):
        description_lines.append("- Follow up on proposal/pricing discussion")
        description_lines.append("- Check for decision timeline or blockers")
    else:
        description_lines.append("- Re-engage to move deal forward")

    description_lines.extend(
        [
            "",
            "RECOMMENDED CHANNEL:",
            "- Email (primary)",
        ]
    )

    # Add key context
    description_lines.extend(
        [
            "",
            "KEY CONTEXT:",
            f"- Deal: {deal_name}",
            f"- Stage: {deal_stage}",
        ]
    )

    if org_name:
        description_lines.append(f"- Organization: {org_name}")
    if contact_name:
        description_lines.append(f"- Contact: {contact_name}")

    deal_value = get_deal_value(deal, base_key)
    if deal_value:
        description_lines.append(f"- Value: {deal_value}")

    description_lines.append(
        f"- Deal URL: {airtable_record_url(config['base_id'], config['deals_table_id'], deal_id)}"
    )

    description = "\n".join(description_lines)

    # Notes with additional context
    notes = f"Auto-generated by stale deal follow-up generator\nDeal ID: {deal_id}\nBase: {base_key.upper()}"

    if dry_run:
        return {
            "title": task_title,
            "description": description,
            "assignee": "aaron",
            "deal_id": deal_id,
            "base": base_key,
            "dry_run": True,
        }

    # Create the task using create_task.py
    create_task_script = os.path.join(
        SKILLS_DIR, "managing-projects", "scripts", "executing-tasks", "create_task.py"
    )

    cmd = [
        "python3",
        create_task_script,
        "--base",
        base_key,
        "--title",
        task_title,
        "--description",
        description,
        "--assignee",
        "aaron",
        "--deal",
        deal_id,
        "--notes",
        notes,
    ]

    # We need to find a project to link to - use inbox project as fallback
    inbox_project = config.get("inbox_project_id")
    if inbox_project:
        cmd.extend(["--project", inbox_project])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
            return {
                "success": True,
                "task_id": result.get("id"),
                "task_url": result.get("airtable_url"),
                "title": task_title,
            }
        else:
            return {
                "success": False,
                "error": proc.stderr,
                "title": task_title,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "title": task_title,
        }


def gather_deals_for_base(base_key: str) -> list[dict[str, Any]]:
    """Gather deals in qualification stage or later from a single base."""
    config = BASES[base_key]

    if base_key == "bb":
        # BB: Get all deals assigned to Aaron, then filter by stage
        # Stage is a linked record, so we fetch all and filter in Python
        formula = f'FIND("{AARON_IDS[base_key]}", ARRAYJOIN({{Assignee}}, ","))'
        fields = [
            "Name",
            "Status",
            "Organization",
            "Deal Contacts",
            "Tasks",
            "Notes",
            "Amount",
            "Description",
        ]
    else:
        # AITB: Filter by stage (single select)
        stage_conditions = [
            f'{{Stage}}="{stage}"' for stage in AITB_QUALIFICATION_STAGES
        ]
        formula = f"OR({', '.join(stage_conditions)})"
        fields = [
            "Project Title",
            "Stage",
            "Organization Name",
            "Contact",
            "Tasks",
            "Notes",
            "Deal Value",
            "Description",
        ]

    print(f"[{base_key}] Fetching deals...", file=sys.stderr)
    deals = fetch_records(
        config["base_id"], config["deals_table_id"], formula=formula, fields=fields
    )

    # For BB, filter by qualification stages
    if base_key == "bb":
        qualified_deals = []
        for deal in deals:
            stage_name = get_bb_stage_name(deal.get("fields", {}))
            if stage_name and any(
                stage_name.startswith(prefix) for prefix in BB_QUALIFICATION_PREFIXES
            ):
                qualified_deals.append(deal)
        deals = qualified_deals

    print(
        f"[{base_key}] Found {len(deals)} deals in qualification stage or later",
        file=sys.stderr,
    )

    return deals


def main():
    parser = argparse.ArgumentParser(
        description="Generate follow-up tasks for stale deals"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview tasks without creating them"
    )
    parser.add_argument(
        "--output-json", action="store_true", help="Output results as JSON"
    )
    args = parser.parse_args()

    now = datetime.now()
    stale_threshold = now - timedelta(days=STALE_DAYS)

    results = {
        "generated_at": now.isoformat(),
        "stale_threshold_days": STALE_DAYS,
        "summary": {
            "total_deals_reviewed": 0,
            "stale_deals_found": 0,
            "tasks_created": 0,
            "tasks_skipped": 0,
            "failures": 0,
        },
        "bb": {"deals_reviewed": 0, "stale": [], "tasks_created": [], "skipped": []},
        "aitb": {"deals_reviewed": 0, "stale": [], "tasks_created": [], "skipped": []},
        "errors": [],
    }

    for base_key in ["bb", "aitb"]:
        try:
            deals = gather_deals_for_base(base_key)
            results[base_key]["deals_reviewed"] = len(deals)
            results["summary"]["total_deals_reviewed"] += len(deals)

            for deal in deals:
                deal_id = deal["id"]
                deal_fields = deal.get("fields", {})
                deal_name = (
                    deal_fields.get("Name")
                    if base_key == "bb"
                    else deal_fields.get("Project Title")
                )

                # Check for recent touchpoints
                try:
                    last_touch_date, last_touch_type, last_touch_source = (
                        get_last_touchpoint_date(deal, base_key)
                    )
                except Exception as e:
                    print(
                        f"  Warning: Error getting touchpoints for {deal_name}: {e}",
                        file=sys.stderr,
                    )
                    last_touch_date, last_touch_type, last_touch_source = (
                        None,
                        None,
                        None,
                    )

                if last_touch_date is None:
                    # No touchpoints found - consider stale
                    days_stale = 999
                    is_stale = True
                else:
                    days_stale = (now - last_touch_date).days
                    is_stale = days_stale >= STALE_DAYS

                if not is_stale:
                    continue

                # Found a stale deal
                stale_info = {
                    "deal_id": deal_id,
                    "deal_name": deal_name,
                    "days_stale": days_stale,
                    "last_touch_date": last_touch_date.isoformat()
                    if last_touch_date
                    else None,
                    "last_touch_type": last_touch_type,
                    "last_touch_source": last_touch_source,
                }
                results[base_key]["stale"].append(stale_info)
                results["summary"]["stale_deals_found"] += 1

                # Check if already has follow-up task
                try:
                    has_followup = has_existing_followup_task(deal_id, base_key)
                except Exception as e:
                    print(
                        f"  Warning: Error checking existing tasks for {deal_name}: {e}",
                        file=sys.stderr,
                    )
                    has_followup = False

                if has_followup:
                    results[base_key]["skipped"].append(
                        {
                            "deal_id": deal_id,
                            "deal_name": deal_name,
                            "reason": "Already has open follow-up task",
                        }
                    )
                    results["summary"]["tasks_skipped"] += 1
                    continue

                # Create follow-up task
                try:
                    task_result = create_followup_task(
                        deal,
                        base_key,
                        days_stale,
                        last_touch_type,
                        last_touch_source,
                        dry_run=args.dry_run,
                    )
                except Exception as e:
                    task_result = {
                        "success": False,
                        "error": str(e),
                        "title": f"Follow up re: {deal_name}",
                    }

                if task_result.get("success") or args.dry_run:
                    results[base_key]["tasks_created"].append(
                        {
                            "deal_id": deal_id,
                            "deal_name": deal_name,
                            "task_title": task_result.get("title"),
                            "task_id": task_result.get("task_id"),
                            "task_url": task_result.get("task_url"),
                            "dry_run": args.dry_run,
                        }
                    )
                    if not args.dry_run:
                        results["summary"]["tasks_created"] += 1
                else:
                    results[base_key]["tasks_created"].append(
                        {
                            "deal_id": deal_id,
                            "deal_name": deal_name,
                            "task_title": task_result.get("title"),
                            "error": task_result.get("error"),
                            "success": False,
                        }
                    )
                    results["summary"]["failures"] += 1
                    results["errors"].append(
                        f"Failed to create task for {deal_name}: {task_result.get('error')}"
                    )

        except Exception as e:
            import traceback

            error_msg = f"Error processing {base_key}: {str(e)}"
            print(error_msg, file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            results["errors"].append(error_msg)

    # Output results
    if args.output_json:
        print(json.dumps(results, indent=2))
    else:
        # Print human-readable summary
        print("\n" + "=" * 60)
        print("STALE DEAL FOLLOW-UP TASK GENERATOR - RESULTS")
        print("=" * 60)
        print(f"\nGenerated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Stale threshold: {STALE_DAYS} days")
        print(f"Dry run: {args.dry_run}")

        print("\n--- SUMMARY ---")
        print(f"Total deals reviewed: {results['summary']['total_deals_reviewed']}")
        print(f"Stale deals found: {results['summary']['stale_deals_found']}")
        print(f"Tasks created: {results['summary']['tasks_created']}")
        print(
            f"Tasks skipped (already had follow-up): {results['summary']['tasks_skipped']}"
        )
        print(f"Failures: {results['summary']['failures']}")

        for base_key in ["bb", "aitb"]:
            base_label = "Brain Bridge" if base_key == "bb" else "AI Trailblazers"
            print(f"\n--- {base_label.upper()} ---")
            print(f"Deals reviewed: {results[base_key]['deals_reviewed']}")
            print(f"Stale deals: {len(results[base_key]['stale'])}")

        if results["errors"]:
            print("\n--- ERRORS ---")
            for error in results["errors"]:
                print(f"  ! {error}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
