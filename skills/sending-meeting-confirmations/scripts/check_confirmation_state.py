#!/usr/bin/env python3
"""
Check and manage confirmation state to prevent duplicate confirmations.

Usage:
    python3 check_confirmation_state.py --check <event_id>
    python3 check_confirmation_state.py --mark <event_id> [--attendee-email <email>]
    python3 check_confirmation_state.py --list
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

STATE_FILE = Path.home() / ".openclaw" / "memory" / "meeting-confirmations.json"
TIMEZONE = "America/Phoenix"


def load_state() -> dict:
    """Load the confirmation state file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"confirmed": [], "last_run": None}


def save_state(state: dict) -> None:
    """Save the confirmation state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_already_confirmed(event_id: str, attendee_email: str | None = None) -> bool:
    """Check if a meeting (and optionally attendee) has already been confirmed."""
    state = load_state()
    
    for entry in state.get("confirmed", []):
        if entry.get("event_id") == event_id:
            if attendee_email is None:
                return True
            if attendee_email.lower() in [e.lower() for e in entry.get("attendees", [])]:
                return True
    return False


def mark_confirmed(event_id: str, meeting_title: str, attendee_emails: list[str]) -> None:
    """Mark a meeting as confirmed."""
    state = load_state()
    
    # Check if we already have an entry for this event
    existing = None
    for entry in state.get("confirmed", []):
        if entry.get("event_id") == event_id:
            existing = entry
            break
    
    now = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    
    if existing:
        # Add new attendees to existing entry
        existing_emails = set(existing.get("attendees", []))
        existing_emails.update([e.lower() for e in attendee_emails])
        existing["attendees"] = list(existing_emails)
        existing["confirmed_at"] = now
    else:
        # Create new entry
        state.setdefault("confirmed", []).append({
            "event_id": event_id,
            "meeting_title": meeting_title,
            "attendees": [e.lower() for e in attendee_emails],
            "confirmed_at": now,
        })
    
    state["last_run"] = now
    save_state(state)


def cleanup_old_entries(days: int = 30) -> int:
    """Remove entries older than specified days. Returns count removed."""
    state = load_state()
    now = datetime.now(ZoneInfo(TIMEZONE))
    cutoff = now - timedelta(days=days)
    
    original_count = len(state.get("confirmed", []))
    state["confirmed"] = [
        e for e in state.get("confirmed", [])
        if datetime.fromisoformat(e.get("confirmed_at", "2000-01-01")) > cutoff
    ]
    removed = original_count - len(state["confirmed"])
    
    if removed > 0:
        save_state(state)
    
    return removed


def list_confirmed() -> list[dict]:
    """List all confirmed meetings."""
    state = load_state()
    return state.get("confirmed", [])


def main():
    parser = argparse.ArgumentParser(
        description="Manage meeting confirmation state"
    )
    parser.add_argument(
        "--check",
        metavar="EVENT_ID",
        help="Check if an event has been confirmed",
    )
    parser.add_argument(
        "--attendee-email",
        help="Specific attendee email to check (optional)",
    )
    parser.add_argument(
        "--mark",
        metavar="EVENT_ID",
        help="Mark an event as confirmed",
    )
    parser.add_argument(
        "--meeting-title",
        help="Meeting title (required with --mark)",
    )
    parser.add_argument(
        "--attendees",
        nargs="+",
        help="Attendee emails to mark as confirmed (required with --mark)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all confirmed meetings",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove entries older than 30 days",
    )
    args = parser.parse_args()

    if args.check:
        if is_already_confirmed(args.check, args.attendee_email):
            print("confirmed")
            return 0
        else:
            print("not_confirmed")
            return 1

    if args.mark:
        if not args.attendees:
            print("Error: --attendees required with --mark", file=sys.stderr)
            return 1
        mark_confirmed(args.mark, args.meeting_title or "Unknown", args.attendees)
        print(f"Marked {args.mark} as confirmed for {len(args.attendees)} attendee(s)")
        return 0

    if args.list:
        confirmed = list_confirmed()
        if not confirmed:
            print("No confirmed meetings in state file.")
            return 0
        print(json.dumps(confirmed, indent=2))
        return 0

    if args.cleanup:
        from datetime import timedelta
        removed = cleanup_old_entries()
        print(f"Removed {removed} old confirmation entries")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    main()
