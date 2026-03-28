#!/usr/bin/env python3
"""
Fetch all calendar events for the upcoming week (Mon-Sun) across all calendars.

Returns events with attendee information for quality review by Pablo.

Usage:
    python3 fetch_week_meetings.py [--start YYYY-MM-DD]

Output:
    JSON with meetings array, grouped by day.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta


# Google Calendar sources: (label, gog account, calendar ID)
GOOGLE_CALENDARS = [
    ("Personal", "aaroneden77@gmail.com", "primary"),
    ("BB", "aaron@brainbridge.app", "primary"),
    ("AITB", "aaron@aitrailblazers.org", "primary"),
]

# Apple Calendar sources to skip (read-only, no action needed)
# Work (Intuit) - managed externally
# Family - personal events
# TripIt - travel blocks


def get_week_range(start_date: str | None = None) -> tuple[str, str]:
    """Get Monday-Sunday range for the upcoming week."""
    if start_date:
        today = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        today = datetime.now()

    # Find next Monday (or today if Monday)
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() != 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)

    # If today is Sunday, use tomorrow (Monday) as start
    if today.weekday() == 6:
        monday = today + timedelta(days=1)
    # If today is already in a weekday, use this week's Monday
    elif today.weekday() < 5:
        monday = today - timedelta(days=today.weekday())

    sunday = monday + timedelta(days=6)

    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def fetch_google_events(start_date: str, end_date: str) -> list[dict]:
    """Fetch events from all Google calendars via gog CLI."""
    events = []

    for label, account, cal_id in GOOGLE_CALENDARS:
        try:
            result = subprocess.run(
                [
                    "gog",
                    "calendar",
                    "events",
                    "--account",
                    account,
                    cal_id,
                    "--from",
                    f"{start_date}T00:00:00-07:00",
                    "--to",
                    f"{end_date}T23:59:59-07:00",
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"Warning: gog failed for {label}: {e}", file=sys.stderr)
            continue

        if result.returncode != 0:
            print(
                f"Warning: gog failed for {label}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            continue

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON from gog for {label}", file=sys.stderr)
            continue

        for evt in data.get("events", []):
            # Skip all-day events (usually blocks, not meetings)
            start = evt.get("start", {})
            if "date" in start and "dateTime" not in start:
                continue

            # Skip declined events
            attendees = evt.get("attendees", [])
            my_response = None
            for att in attendees:
                if att.get("self"):
                    my_response = att.get("responseStatus")
                    break
            if my_response == "declined":
                continue

            # Extract attendee info
            external_attendees = []
            for att in attendees:
                if not att.get("self") and not att.get("resource"):
                    external_attendees.append(
                        {
                            "email": att.get("email", ""),
                            "name": att.get("displayName", ""),
                            "response": att.get("responseStatus", ""),
                            "organizer": att.get("organizer", False),
                        }
                    )

            end = evt.get("end", {})
            start_dt = start.get("dateTime", "")
            end_dt = end.get("dateTime", "")

            # Calculate duration
            duration_minutes = 0
            if start_dt and end_dt:
                try:
                    s = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                    e = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
                    duration_minutes = int((e - s).total_seconds() / 60)
                except ValueError:
                    pass

            events.append(
                {
                    "id": evt.get("id"),
                    "calendar": label,
                    "account": account,
                    "title": evt.get("summary", "(No title)"),
                    "description": evt.get("description", ""),
                    "start_iso": start_dt,
                    "end_iso": end_dt,
                    "date": start_dt[:10] if start_dt else "",
                    "time": _format_time(start_dt),
                    "end_time": _format_time(end_dt),
                    "duration_minutes": duration_minutes,
                    "location": evt.get("location", ""),
                    "meet_link": evt.get("hangoutLink", ""),
                    "html_link": evt.get("htmlLink", ""),
                    "attendees": external_attendees,
                    "attendee_count": len(external_attendees),
                    "organizer": evt.get("organizer", {}).get("email", ""),
                    "i_am_organizer": evt.get("organizer", {}).get("self", False),
                }
            )

    return events


def _format_time(iso_str: str) -> str:
    """Convert ISO datetime to 12-hour time string like '9:30 AM'."""
    if not iso_str:
        return ""
    try:
        clean = iso_str.split("-07:00")[0].split("+")[0].split("Z")[0]
        # Handle timezone offset in middle of string
        if "T" in clean:
            date_part, time_part = clean.split("T")
            # Remove any remaining offset
            time_part = time_part.split("-")[0].split("+")[0]
            clean = f"{date_part}T{time_part}"
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%-I:%M %p")
    except (ValueError, IndexError):
        return iso_str


def group_by_day(events: list[dict]) -> dict[str, list[dict]]:
    """Group events by date."""
    by_day: dict[str, list[dict]] = {}
    for evt in sorted(events, key=lambda e: e["start_iso"]):
        date = evt["date"]
        if date not in by_day:
            by_day[date] = []
        by_day[date].append(evt)
    return by_day


def main():
    parser = argparse.ArgumentParser(
        description="Fetch calendar events for the upcoming week"
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD). Defaults to upcoming Monday.",
    )
    args = parser.parse_args()

    start_date, end_date = get_week_range(args.start)
    events = fetch_google_events(start_date, end_date)
    by_day = group_by_day(events)

    # Add day names
    days_with_names = {}
    for date_str, day_events in by_day.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        days_with_names[date_str] = {
            "day": day_name,
            "date": date_str,
            "meetings": day_events,
            "count": len(day_events),
        }

    result = {
        "week_start": start_date,
        "week_end": end_date,
        "total_meetings": len(events),
        "days": days_with_names,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
