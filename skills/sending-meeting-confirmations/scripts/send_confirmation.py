#!/usr/bin/env python3
"""
Send meeting confirmation emails to external attendees.

Usage:
    python3 send_confirmation.py [--dry-run] [--json]

Environment:
    Sets --dry-run by default unless OPENCLAW_CONFIRMATION_SEND=1 is set.
"""

import argparse
import json
import os
import subprocess  # nosec B404 - used to call gog CLI with static args
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent directory to path for importing other scripts
sys.path.insert(0, str(Path(__file__).parent))

from gather_external_meetings import gather_external_meetings
from check_confirmation_state import is_already_confirmed, mark_confirmed

TIMEZONE = "America/Phoenix"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "confirmation-message.md"


def load_template() -> str:
    """Load the confirmation message template."""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text()
    # Default template if file doesn't exist
    return """Hi {{name}},

Quick note to confirm our meeting today at {{time}}.

{{location_line}}

Looking forward to connecting then.

Best,
Aaron
"""


def render_template(template: str, meeting: dict, attendee: dict) -> str:
    """Render the template with meeting and attendee data."""
    name = attendee.get("name", "").split()[0] if attendee.get("name") else "there"
    if not name:
        name = "there"
    
    location = meeting.get("location", "")
    if location.startswith("Video call:"):
        location_line = f"We'll connect via video: {location[12:]}"
    else:
        location_line = f"Location: {location}"
    
    return template.replace("{{name}}", name) \
                   .replace("{{time}}", meeting.get("start_formatted", "")) \
                   .replace("{{date}}", meeting.get("date_formatted", "")) \
                   .replace("{{meeting_title}}", meeting.get("title", "")) \
                   .replace("{{location_line}}", location_line) \
                   .replace("{{location}}", location)


def send_confirmation_email(
    to_email: str,
    subject: str,
    body: str,
    account: str,
    dry_run: bool = True,
) -> dict:
    """Send or simulate sending a confirmation email."""
    result = {
        "to": to_email,
        "subject": subject,
        "sent": False,
        "dry_run": dry_run,
        "error": None,
    }
    
    if dry_run:
        result["status"] = "draft"
        return result
    
    try:
        # Use gog to send the email
        proc = subprocess.run(  # nosec B603 B607 - static gog CLI call
            [
                "gog",
                "gmail",
                "send",
                "--to",
                to_email,
                "--subject",
                subject,
                "--body",
                body,
                "--account",
                account,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if proc.returncode == 0:
            result["sent"] = True
            result["status"] = "sent"
        else:
            result["error"] = proc.stderr.strip()
            result["status"] = "failed"
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"
    
    return result


def run_confirmations(dry_run: bool = True, output_json: bool = False) -> list[dict]:
    """Run the confirmation process for all external meetings."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    date_str = now.strftime("%Y-%m-%d")
    
    # Gather meetings
    meetings = gather_external_meetings(date_str)
    
    if not meetings:
        return []
    
    template = load_template()
    results = []
    
    for meeting in meetings:
        event_id = meeting.get("event_id", "")
        
        for attendee in meeting.get("external_attendees", []):
            email = attendee.get("email", "").lower()
            
            # Skip if already confirmed
            if is_already_confirmed(event_id, email):
                results.append({
                    "meeting": meeting.get("title"),
                    "attendee": email,
                    "status": "skipped",
                    "reason": "already_confirmed",
                })
                continue
            
            # Render personalized message
            body = render_template(template, meeting, attendee)
            subject = f"Confirming: {meeting.get('title')} today at {meeting.get('start_formatted')}"
            
            # Determine which account to send from (same as meeting calendar)
            account = meeting.get("account", "aaroneden77@gmail.com")
            
            # Send or draft
            send_result = send_confirmation_email(
                to_email=email,
                subject=subject,
                body=body,
                account=account,
                dry_run=dry_run,
            )
            
            send_result["meeting"] = meeting.get("title")
            send_result["attendee"] = email
            send_result["meeting_time"] = meeting.get("start_formatted")
            
            # Mark as confirmed if sent successfully
            if send_result.get("sent") or dry_run:
                mark_confirmed(event_id, meeting.get("title"), [email])
            
            results.append(send_result)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Send meeting confirmation emails"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without sending (default unless OPENCLAW_CONFIRMATION_SEND=1)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send emails (override env var)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()
    
    # Determine if we should actually send
    env_send = os.environ.get("OPENCLAW_CONFIRMATION_SEND", "") == "1"
    dry_run = not (args.send or env_send)
    
    if args.dry_run:
        dry_run = True
    
    results = run_confirmations(dry_run=dry_run, output_json=args.json)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No external meetings requiring confirmation.")
            return
        
        action = "DRY RUN - Would send" if dry_run else "Sent"
        print(f"\n{action} {len(results)} confirmation(s):\n")
        
        for r in results:
            status_icon = "✓" if r.get("status") in ("sent", "draft") else "○"
            if r.get("status") == "skipped":
                print(f"  {status_icon} {r['meeting']} → {r['attendee']} (already confirmed)")
            else:
                print(f"  {status_icon} {r['meeting']} → {r['attendee']}")
                if r.get("error"):
                    print(f"     Error: {r['error']}")
        
        if dry_run:
            print("\nTo actually send, use --send or set OPENCLAW_CONFIRMATION_SEND=1")


if __name__ == "__main__":
    main()
