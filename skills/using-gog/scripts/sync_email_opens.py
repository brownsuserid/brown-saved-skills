#!/usr/bin/env python3
"""Sync email opens from gog tracking workers to Airtable Contact Activity Logs.

Queries all three gog tracking workers (personal, bb, aitb) for opens in the
last 24 hours, resolves each recipient email to a contact in BB or AITB, and
creates a Contact Activity Log entry in the matching base for each unique open.

Idempotent: tracks synced tracking_id+recipient+date combos in a local state file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.expanduser("~/.openclaw/skills/_shared"))
import _config as cfg  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCOUNTS: list[str] = [
    "aaroneden77@gmail.com",
    "aaron@brainbridge.app",
    "aaron@aitrailblazers.org",
]

# Per-base config for contact resolution and activity logging.
# Each base has its own contacts table, email field name, activity logs table,
# and field IDs for the activity log records.
BASES_CONFIG: list[dict[str, str]] = [
    {
        "label": "bb",
        "base_id": cfg.BASES["bb"]["base_id"],
        "contacts_table": cfg.TABLES["bb"]["contacts"],
        "email_field": cfg.BASES["bb"]["contacts_email_field"],
        "activity_logs_table": cfg.TABLES["bb"]["contact_activity_logs"],
        "fld_contact": "fld1m4LKuy1IKvq02",
        "fld_activity_type": "fld5v5j0M9WLxkfj3",
        "fld_details": "fldloeLifv73vG4SF",
    },
    {
        "label": "aitb",
        "base_id": cfg.BASES["aitb"]["base_id"],
        "contacts_table": cfg.TABLES["aitb"]["contacts"],
        "email_field": cfg.BASES["aitb"]["contacts_email_field"],
        "activity_logs_table": cfg.TABLES["aitb"]["contact_activity_logs"],
        "fld_contact": "fld1HrjlIX3KfQgPK",
        "fld_activity_type": "fldgP0nAm0AsewEI2",
        "fld_details": "fldu4SI2h31ekBDmG",
    },
]

STATE_FILE: Path = Path(__file__).parent / ".tracking_state.json"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def load_state() -> set[str]:
    """Load set of already-synced dedup keys from state file."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return set(data.get("synced_keys", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def save_state(keys: set[str]) -> None:
    """Persist synced dedup keys. Keeps only keys from the last 7 days."""
    # Keep keys that include a date within the last 7 days (simple pruning)
    recent: list[str] = []
    for k in keys:
        # Key format: tracking_id|recipient|YYYY-MM-DD
        parts = k.rsplit("|", 1)
        if len(parts) == 2:
            key_date = parts[1]
            # Keep if within 7 days (rough check: keep anything from this month or last)
            if key_date >= _seven_days_ago():
                recent.append(k)
        else:
            recent.append(k)
    STATE_FILE.write_text(json.dumps({"synced_keys": sorted(recent)}, indent=2) + "\n")


def _seven_days_ago() -> str:
    from datetime import timedelta

    return (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")


def dedup_key(tracking_id: str, recipient: str, opened_at: str) -> str:
    """Build a dedup key from tracking_id + recipient + date."""
    date_part = (
        opened_at[:10] if opened_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    return f"{tracking_id}|{recipient}|{date_part}"


# ---------------------------------------------------------------------------
# gog CLI interaction
# ---------------------------------------------------------------------------


def query_opens(account: str) -> list[dict[str, Any]]:
    """Query opens from a gog tracking worker for the last 24 hours."""
    try:
        result = subprocess.run(
            [
                "gog",
                "gmail",
                "track",
                "opens",
                "--since",
                "24h",
                "--account",
                account,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(
                f"  Warning: gog query failed for {account}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return []
        data = json.loads(result.stdout)
        return data.get("opens", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  Warning: error querying {account}: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------

# Cache: email -> (contact_record_id, base_config) or (None, None)
_contact_cache: dict[str, tuple[str | None, dict[str, str] | None]] = {}


def find_contact_by_email(email: str) -> tuple[str | None, dict[str, str] | None]:
    """Search BB then AITB contacts by email. Returns (record_id, base_config) or (None, None)."""
    if email in _contact_cache:
        return _contact_cache[email]

    for base_cfg in BASES_CONFIG:
        url = cfg.api_url(base_cfg["base_id"], base_cfg["contacts_table"])
        email_field = base_cfg["email_field"]
        params = {
            "filterByFormula": f'{{{email_field}}} = "{email}"',
            "maxRecords": "1",
            "fields[]": email_field,
        }
        resp = requests.get(url, headers=cfg.api_headers(), params=params, timeout=15)
        if resp.status_code != 200:
            print(
                f"  Warning: Airtable search failed in {base_cfg['label']} for {email}: {resp.status_code}",
                file=sys.stderr,
            )
            continue

        records = resp.json().get("records", [])
        if records:
            result = (records[0]["id"], base_cfg)
            _contact_cache[email] = result
            return result

    _contact_cache[email] = (None, None)
    return (None, None)


def create_activity_log(
    contact_id: str, details: str, base_cfg: dict[str, str]
) -> str | None:
    """Create a Contact Activity Log record in the given base. Returns record ID or None."""
    url = cfg.api_url(base_cfg["base_id"], base_cfg["activity_logs_table"])
    payload = {
        "records": [
            {
                "fields": {
                    base_cfg["fld_contact"]: [contact_id],
                    base_cfg["fld_activity_type"]: "Message Opened",
                    base_cfg["fld_details"]: details,
                }
            }
        ]
    }
    resp = requests.post(url, headers=cfg.api_headers(), json=payload, timeout=15)
    if resp.status_code != 200:
        print(
            f"  Warning: failed to create activity log in {base_cfg['label']}: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        return None

    records = resp.json().get("records", [])
    return records[0]["id"] if records else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def format_details(open_event: dict[str, Any], account: str) -> str:
    """Build a human-readable details string from an open event."""
    parts = [
        f"Account: {account}",
        f"Tracking ID: {open_event.get('tracking_id', 'unknown')}",
        f"Opened: {open_event.get('opened_at', 'unknown')}",
    ]
    if open_event.get("country"):
        location = open_event["country"]
        if open_event.get("city"):
            location = f"{open_event['city']}, {location}"
        parts.append(f"Location: {location}")
    if open_event.get("user_agent"):
        ua = open_event["user_agent"]
        if len(ua) > 120:
            ua = ua[:120] + "..."
        parts.append(f"User-Agent: {ua}")
    return "\n".join(parts)


def main() -> None:
    synced_keys = load_state()
    stats = {
        "queried": 0,
        "new_opens": 0,
        "no_contact": 0,
        "logged": 0,
        "skipped_dup": 0,
    }

    for account in ACCOUNTS:
        print(f"Querying opens for {account}...")
        opens = query_opens(account)
        stats["queried"] += len(opens)
        print(f"  Found {len(opens)} open(s)")

        for event in opens:
            tracking_id: str = event.get("tracking_id", "")
            recipient: str = event.get("recipient", "")
            opened_at: str = event.get("opened_at", "")

            if not tracking_id or not recipient:
                continue

            key = dedup_key(tracking_id, recipient, opened_at)
            if key in synced_keys:
                stats["skipped_dup"] += 1
                continue

            stats["new_opens"] += 1

            contact_id, base_cfg = find_contact_by_email(recipient)
            if not contact_id or not base_cfg:
                print(f"  No contact found for {recipient}, skipping")
                stats["no_contact"] += 1
                synced_keys.add(key)
                continue

            details = format_details(event, account)
            record_id = create_activity_log(contact_id, details, base_cfg)
            if record_id:
                print(
                    f"  Logged open: {recipient} [{base_cfg['label']}] "
                    f"(tracking: {tracking_id[:12]}...)"
                )
                stats["logged"] += 1
                synced_keys.add(key)
            else:
                print(f"  Failed to log open for {recipient}")

    save_state(synced_keys)

    print("\n--- Summary ---")
    print(f"Total opens queried: {stats['queried']}")
    print(f"New (not previously synced): {stats['new_opens']}")
    print(f"Skipped (already synced): {stats['skipped_dup']}")
    print(f"No matching contact: {stats['no_contact']}")
    print(f"Activity logs created: {stats['logged']}")


if __name__ == "__main__":
    main()
