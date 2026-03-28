"""
Contact lookup by email and activity logging for BB and AITB Airtable bases.

Used by draft_email.py to auto-log email activity when drafting/sending
from BB or AITB accounts.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

# Add shared config to path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "_shared"),
)

from _config import BASES, TABLES, api_headers

# ---------------------------------------------------------------------------
# Email field mappings per base
# ---------------------------------------------------------------------------

EMAIL_FIELDS = {
    "bb": ["Email (Work)", "Email (Personal)"],
    "aitb": ["Email"],
}

# Activity type per base (must match existing Airtable select options)
ACTIVITY_TYPE = {
    "bb": "Email Sent",
    "aitb": "Message Sent",
}


# ---------------------------------------------------------------------------
# Contact lookup
# ---------------------------------------------------------------------------


def lookup_contact_by_email(email: str, base: str) -> str | None:
    """Search the Contacts table for a record matching the given email.

    Checks all email fields for the base (BB has Work + Personal, AITB has one).
    Returns the Airtable record ID of the first match, or None.
    """
    if base not in EMAIL_FIELDS:
        return None

    base_id = BASES[base]["base_id"]
    table_id = TABLES[base]["contacts"]
    fields = EMAIL_FIELDS[base]

    # Build OR formula across all email fields
    conditions = [f"{{{f}}}='{email}'" for f in fields]
    if len(conditions) == 1:
        formula = conditions[0]
    else:
        formula = f"OR({', '.join(conditions)})"

    url = (
        f"https://api.airtable.com/v0/{base_id}/{table_id}"
        f"?filterByFormula={urllib.parse.quote(formula)}&maxRecords=1"
    )

    try:
        req = urllib.request.Request(url, headers=api_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        records = data.get("records", [])
        if records:
            return records[0]["id"]
    except Exception as e:
        print(
            f"Warning: Contact lookup failed for {email} in {base}: {e}",
            file=sys.stderr,
        )

    return None


# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------


def log_email_activity(
    base: str,
    contact_id: str,
    subject: str,
    to: str,
    account_email: str,
    deal_id: str | None = None,
    thread_id: str | None = None,
    message_id: str | None = None,
) -> dict | None:
    """Create a Contact Activity Log record in the appropriate base.

    Returns the created record dict, or None on failure.
    Non-fatal: prints warnings to stderr but never raises.
    """
    if base not in ACTIVITY_TYPE:
        return None

    base_id = BASES[base]["base_id"]
    table_id = TABLES[base]["contact_activity_logs"]
    activity_type = ACTIVITY_TYPE[base]

    details = f"Subject: {subject}\nTo: {to}\nAccount: {account_email}"

    fields: dict = {
        "Contact": [contact_id],
        "Activity Type": activity_type,
        "Details": details,
    }

    # AITB has a Name field
    if base == "aitb":
        fields["Name"] = f"Email: {subject}"

    # BB has Thread ID, Message ID, and Deals fields
    if base == "bb":
        if thread_id:
            fields["Thread ID"] = thread_id
        if message_id:
            fields["Message ID"] = message_id
        if deal_id:
            fields["Deals"] = [deal_id]

    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    payload = json.dumps({"fields": fields}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers=api_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        return result
    except Exception as e:
        print(
            f"Warning: Failed to log activity in {base}: {e}",
            file=sys.stderr,
        )
        return None
