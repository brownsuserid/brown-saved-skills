#!/usr/bin/env python3
"""
Draft follow-up messages for event outreach.

For each contact needing follow-up, reads their recent conversation from
Beeper to provide context for personalized messaging. Skips contacts
who were already messaged recently.

Outputs conversation context + a suggested template for Pablo to customize.
NEVER sends messages — drafts only.

Usage:
    python3 draft_beeper_followups.py --config path/to/config.json --limit 5
    python3 draft_beeper_followups.py --config path/to/config.json --status Invited
    python3 draft_beeper_followups.py --config path/to/config.json --fetch-context

Output:
    JSON to stdout with conversation context per contact.
    Status messages to stderr.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BEEPER_READ = os.path.join(
    os.path.dirname(SCRIPT_DIR), "using-beeper", "beeper-read.sh"
)

# Generic fallback templates used when config.json has no "templates" section
DEFAULT_TEMPLATE_NUDGE = """Hi {name},

Quick follow-up on {event_name} on {event_date} at {event_location}. We'd love to have you there if you're interested.

RSVP here if you can make it: {rsvp_url}

Let me know either way!

Best,
Aaron"""

DEFAULT_TEMPLATE_INTERESTED = """Hi {name},

Great to hear you're interested in {event_name}! Just wanted to make sure you saw the RSVP link.

{event_date} at {event_location}.

RSVP here: {rsvp_url}

See you there!

Best,
Aaron"""

AARON_SENDER_ID = "@aaroneden77:beeper.com"


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def call_beeper(tool: str, params: dict) -> str | None:
    """Call beeper-read.sh and return the text output, or None on failure."""
    try:
        result = subprocess.run(
            [BEEPER_READ, tool, json.dumps(params)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def run_gog(args: list[str]) -> str | None:
    """Run a gog CLI command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["gog"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def read_spreadsheet(config: dict) -> list[dict]:
    """Read current spreadsheet rows via gog CLI --json."""
    ss = config["spreadsheet"]
    tab = ss["developersTab"]
    columns = ss.get("columns", "A:F")
    raw = run_gog(
        [
            "sheets",
            "get",
            ss["id"],
            f"{tab}!{columns}",
            "--account",
            ss["account"],
            "--json",
        ]
    )
    if raw is None:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    values = data.get("values", [])
    if len(values) < 2:
        return []

    headers = values[0]
    rows = []
    for row_values in values[1:]:
        row = {}
        for i, header in enumerate(headers):
            row[header] = row_values[i] if i < len(row_values) else ""
        rows.append(row)

    return rows


def get_conversation_context(chat_id: str) -> dict:
    """Fetch recent messages for a chat and parse into structured context.

    list_messages returns JSON: {"items": [{"senderID": "...", "isSender": bool,
    "timestamp": "...", "text": "...", ...}, ...]}

    Returns dict with:
        recent_aaron_message: True if Aaron sent a message today
        their_messages: list of contact's message texts
        aaron_messages: list of Aaron's message texts
    """
    raw = call_beeper("list_messages", {"chatID": chat_id})
    if raw is None:
        return {
            "recent_aaron_message": False,
            "their_messages": [],
            "aaron_messages": [],
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "recent_aaron_message": False,
            "their_messages": [],
            "aaron_messages": [],
        }

    items = data.get("items", [])
    their_messages: list[str] = []
    aaron_messages: list[str] = []
    recent_aaron_message = False
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for item in items:
        text = item.get("text", "").strip()
        if not text:
            continue

        is_aaron = (
            item.get("isSender", False) or item.get("senderID", "") == AARON_SENDER_ID
        )

        if is_aaron:
            aaron_messages.append(text)
            ts = item.get("timestamp", "")
            if ts.startswith(today_str):
                recent_aaron_message = True
        else:
            their_messages.append(text)

    return {
        "recent_aaron_message": recent_aaron_message,
        "their_messages": their_messages,
        "aaron_messages": aaron_messages,
    }


def get_contacts_needing_followup(config: dict) -> list[dict]:
    """Build list of contacts needing follow-up from spreadsheet."""
    followup_rules = config.get("followup_rules", {})
    priority_statuses = followup_rules.get(
        "priority_order", ["Interested", "No Response", "Invited"]
    )

    sheet_rows = read_spreadsheet(config)

    contacts = []
    known_contacts_map = {
        c["name"].lower(): c for c in config.get("known_contacts", [])
    }

    for row in sheet_rows:
        name = row.get("Name", "")
        status = row.get("Status", "")
        # Notes column stores chat_id for LinkedIn contacts
        notes = row.get("Notes", "")
        channel = row.get("Channel", "LinkedIn")

        if not name:
            continue

        needs_followup = (
            any(ps.lower() in status.lower() for ps in priority_statuses)
            if status
            else False
        )
        if not needs_followup:
            continue

        # Resolve chat_id: check Notes column first, then known_contacts
        chat_id = ""
        if notes and notes.startswith("!"):
            chat_id = notes
        else:
            known = known_contacts_map.get(name.lower())
            if known:
                chat_id = known["chat_id"]

        contacts.append(
            {
                "name": name,
                "status": status,
                "chat_id": chat_id,
                "channel": channel,
            }
        )

    # Sort by priority
    def priority_key(c: dict) -> int:
        for i, ps in enumerate(priority_statuses):
            if ps.lower() in c["status"].lower():
                return i
        return len(priority_statuses)

    contacts.sort(key=priority_key)
    return contacts


def render_template(status: str, name: str, config: dict) -> str:
    """Render a suggested template with contact name and event details.

    Uses templates from config.json if available, otherwise falls back to
    generic defaults.
    """
    first_name = name.split()[0] if name else name
    event = config.get("event", {})
    rsvp_url = event.get("rsvpUrl", "")
    event_name = event.get("name", "the event")
    event_date = event.get("date", "")
    event_location = event.get("location", "")

    templates = config.get("templates", {})
    if "interested" in status.lower():
        template = templates.get("interested", DEFAULT_TEMPLATE_INTERESTED)
    else:
        template = templates.get("nudge", DEFAULT_TEMPLATE_NUDGE)

    return template.format(
        name=first_name,
        rsvp_url=rsvp_url,
        event_name=event_name,
        event_date=event_date,
        event_location=event_location,
    )


def build_beeper_command(chat_id: str, message: str) -> str:
    """Generate a python3 one-liner that calls beeper-read.sh focus_app.

    Uses python3 subprocess to avoid shell quoting issues with apostrophes
    and newlines in the draft text.
    """
    params = json.dumps({"chatID": chat_id, "draftText": message})
    escaped_params = params.replace("\\", "\\\\").replace("'", "\\'")
    return (
        f'python3 -c "import subprocess,json; '
        f"subprocess.run(['{BEEPER_READ}','focus_app',"
        f"'{escaped_params}'])\""
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draft follow-up messages for event outreach"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to event config.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of drafts to generate (0 = all)",
    )
    parser.add_argument(
        "--status",
        help="Only draft for contacts with this status (e.g. 'Interested')",
    )
    parser.add_argument(
        "--skip-recent",
        action="store_true",
        default=True,
        help="Skip contacts Aaron already messaged today (default: true)",
    )
    parser.add_argument(
        "--no-skip-recent",
        action="store_false",
        dest="skip_recent",
        help="Include contacts even if messaged today",
    )
    parser.add_argument(
        "--fetch-context",
        action="store_true",
        default=False,
        help="Call list_messages per contact for conversation context (slow, triggers Beeper draft indicators). Off by default.",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Get contacts needing follow-up
    print("Identifying contacts needing follow-up...", file=sys.stderr)
    contacts = get_contacts_needing_followup(config)

    if args.status:
        contacts = [c for c in contacts if args.status.lower() in c["status"].lower()]

    print(f"  Found {len(contacts)} contacts needing follow-up", file=sys.stderr)

    drafts = []
    skipped = []

    for contact in contacts:
        if args.limit and len(drafts) >= args.limit:
            break

        name = contact["name"]
        status = contact["status"]
        chat_id = contact["chat_id"]

        if not chat_id:
            skipped.append({"name": name, "reason": "no_chat_id"})
            continue

        # Only call list_messages if --fetch-context is set.
        # By default, skip the Beeper scan to avoid triggering draft
        # indicators in Beeper Desktop from dozens of API calls.
        if args.fetch_context:
            print(f"  Reading conversation: {name}...", file=sys.stderr)
            context = get_conversation_context(chat_id)

            if args.skip_recent and context["recent_aaron_message"]:
                print(f"  Skipping {name}: already messaged today", file=sys.stderr)
                skipped.append({"name": name, "reason": "messaged_today"})
                continue
        else:
            context = {
                "recent_aaron_message": False,
                "their_messages": [],
                "aaron_messages": [],
            }

        # Generate suggested template (Pablo should customize based on context)
        suggested_message = render_template(status, name, config)

        draft = {
            "name": name,
            "status": status,
            "chat_id": chat_id,
            "channel": contact["channel"],
            "template_type": "interested"
            if "interested" in status.lower()
            else "nudge",
            "suggested_message": suggested_message,
            "conversation_context": {
                "their_messages": context["their_messages"],
                "aaron_messages": context["aaron_messages"],
                "already_messaged_today": context["recent_aaron_message"],
            },
            "beeper_command": build_beeper_command(chat_id, suggested_message),
        }
        drafts.append(draft)
        if args.fetch_context:
            print(
                f"  Drafted: {name} ({status})"
                f" — {len(context['their_messages'])} replies,"
                f" {len(context['aaron_messages'])} sent",
                file=sys.stderr,
            )
        else:
            print(f"  Drafted: {name} ({status})", file=sys.stderr)

    result = {
        "drafts": drafts,
        "skipped": skipped,
        "summary": {
            "drafts_count": len(drafts),
            "skipped_count": len(skipped),
        },
    }

    print(json.dumps(result, indent=2))

    print(
        f"\nDrafts complete: {len(drafts)} ready, {len(skipped)} skipped",
        file=sys.stderr,
    )
    if drafts:
        print(
            "Each draft includes conversation_context for personalization.",
            file=sys.stderr,
        )
        print(
            "Review and customize before sending — messages are NEVER sent automatically.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
