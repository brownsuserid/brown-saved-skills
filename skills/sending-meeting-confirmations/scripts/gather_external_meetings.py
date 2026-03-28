#!/usr/bin/env python3
"""
Gather today's external meetings from Google Calendars.
External = attendees who are not @intuit.com and not Aaron's emails.

Usage:
    python3 gather_external_meetings.py [--date 2026-02-10]

Output:
    JSON array of meetings with external attendees.
"""

import argparse
import json
import subprocess  # nosec B404 - used to call gog CLI with static args
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Aaron's email addresses (these are NOT external)
AARON_EMAILS = {
    "aaroneden77@gmail.com",
    "aaron@brainbridge.app",
    "aaron@aitrailblazers.org",
    "aaron_eden@intuit.com",
    "aaron.eden@intuit.com",
}

# Intuit domains (these are NOT external)
INTUIT_DOMAINS = {"intuit.com", "intuit.net"}

# Calendars to check
CALENDARS = [
    {"label": "BB", "account": "aaron@brainbridge.app"},
    {"label": "AITB", "account": "aaron@aitrailblazers.org"},
    {"label": "Personal", "account": "aaroneden77@gmail.com"},
]

TIMEZONE = "America/Phoenix"


def is_external_email(email: str) -> bool:
    """Return True if email is external (not Aaron's and not Intuit)."""
    email_lower = email.lower().strip()
    if email_lower in AARON_EMAILS:
        return False
    domain = email_lower.split("@")[-1] if "@" in email_lower else ""
    if domain in INTUIT_DOMAINS:
        return False
    return True


def fetch_events_for_calendar(account: str, date_str: str) -> list[dict]:
    """Fetch events from a Google Calendar for a specific date."""
    tz = ZoneInfo(TIMEZONE)
    tz_offset = datetime.now(tz).strftime("%z")
    tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}"

    start_iso = f"{date_str}T00:00:00{tz_offset_formatted}"
    end_iso = f"{date_str}T23:59:59{tz_offset_formatted}"

    try:
        result = subprocess.run(  # nosec B603 B607 - static gog CLI call
            [
                "gog",
                "calendar",
                "events",
                "--account",
                account,
                "primary",
                "--from",
                start_iso,
                "--to",
                end_iso,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Warning: gog failed for {account}: {e}", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(
            f"Warning: gog failed for {account}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON from gog for {account}", file=sys.stderr)
        return []

    return data.get("events", [])


def extract_attendees(evt: dict) -> list[dict]:
    """Extract attendee information from event."""
    attendees = []
    for attendee in evt.get("attendees", []):
        email = attendee.get("email", "").lower().strip()
        if not email:
            continue
        # Skip Aaron himself
        if email in AARON_EMAILS:
            continue
        attendees.append({
            "email": email,
            "name": attendee.get("displayName", ""),
            "response_status": attendee.get("responseStatus", "unknown"),
            "is_external": is_external_email(email),
        })
    return attendees


def get_meeting_location(evt: dict) -> str:
    """Extract and clean meeting location."""
    location = evt.get("location", "")
    if location:
        # Check if it's a video link
        video_patterns = ["zoom.us", "meet.google", "teams.microsoft"]
        if any(p in location.lower() for p in video_patterns):
            return f"Video call: {location}"
        return location
    
    # Check for conference data
    if evt.get("conferenceData"):
        entry_points = evt["conferenceData"].get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                return f"Video call: {ep.get('uri', 'Link in calendar')}"
    
    return "Location: See calendar invite"


def gather_external_meetings(date_str: str | None = None) -> list[dict]:
    """Gather all external meetings for the given date."""
    if date_str is None:
        date_str = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")

    all_meetings = []
    now = datetime.now(ZoneInfo(TIMEZONE))

    for cal in CALENDARS:
        account = cal["account"]
        label = cal["label"]
        events = fetch_events_for_calendar(account, date_str)

        for evt in events:
            # Skip BBI (Brain Bridge Internal) meetings
            title = evt.get("summary", "").lower()
            if "bbi" in title:
                continue

            # Skip all-day events
            start = evt.get("start", {})
            if start.get("date") and not start.get("dateTime"):
                continue

            # Skip declined events
            attendees = extract_attendees(evt)
            self_attendee = None
            for att in evt.get("attendees", []):
                if att.get("self"):
                    self_attendee = att
                    break
            if self_attendee and self_attendee.get("responseStatus") == "declined":
                continue

            # Get external attendees
            external_attendees = [a for a in attendees if a["is_external"]]
            if not external_attendees:
                continue

            # Parse start time
            start_dt_str = start.get("dateTime", "")
            if not start_dt_str:
                continue

            try:
                # Handle ISO format with timezone
                start_dt = datetime.fromisoformat(start_dt_str.replace("Z", "+00:00"))
                # Convert to Arizona time
                start_dt = start_dt.astimezone(ZoneInfo(TIMEZONE))
            except ValueError:
                continue

            # Skip meetings that have already started or are more than 24 hours away
            time_until = start_dt - now
            if time_until.total_seconds() < 0:
                continue  # Already started
            if time_until.total_seconds() > 24 * 3600:
                continue  # More than 24 hours away

            meeting = {
                "event_id": evt.get("id", ""),
                "calendar": label,
                "account": account,
                "title": evt.get("summary", "Untitled Meeting"),
                "start_iso": start_dt_str,
                "start_formatted": start_dt.strftime("%I:%M %p").lstrip("0"),
                "date_formatted": start_dt.strftime("%A, %B %d"),
                "location": get_meeting_location(evt),
                "external_attendees": external_attendees,
                "attendee_count": len(external_attendees),
                "html_link": evt.get("htmlLink", ""),
            }
            all_meetings.append(meeting)

    # Sort by start time
    all_meetings.sort(key=lambda m: m["start_iso"])
    return all_meetings


def main():
    parser = argparse.ArgumentParser(
        description="Gather today's external meetings"
    )
    parser.add_argument(
        "--date",
        help="Date to check (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Only include meetings within this many hours (default: 24)",
    )
    args = parser.parse_args()

    meetings = gather_external_meetings(args.date)

    if args.json:
        print(json.dumps(meetings, indent=2))
    else:
        if not meetings:
            print("No external meetings found for confirmation.")
            return

        print(f"Found {len(meetings)} external meeting(s) to confirm:")
        for m in meetings:
            print(f"\n  📅 {m['title']}")
            print(f"     Time: {m['date_formatted']} at {m['start_formatted']}")
            print(f"     Location: {m['location']}")
            print(f"     Attendees: {', '.join(a['email'] for a in m['external_attendees'])}")


if __name__ == "__main__":
    main()
