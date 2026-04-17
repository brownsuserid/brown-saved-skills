#!/usr/bin/env python3
"""
Fetch upcoming trips from TripIt iCal feed.

Fetches TripIt events 90 days ahead from the private iCal URL,
extracts destination info, and filters out already-processed trips.

Usage:
    python3 fetch_trips.py [--days 90] [--state path/to/processed-trips.json]

Environment:
    TRIPIT_ICAL_URL - Optional override for the iCal feed URL

Output:
    JSON with upcoming trips array.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Phoenix")
STATE_DIR = Path(__file__).parent.parent.parent / "data" / "speaking-opportunities"

# Aaron's TripIt iCal feed URL
DEFAULT_TRIPIT_ICAL_URL = "https://www.tripit.com/feed/ical/private/9DCC2558-C93F5DA6A1C9567E01692A842CE9EC70/tripit.ics"


def parse_ical_datetime(dt_str: str) -> datetime:
    """Parse an iCal datetime string to datetime object."""
    # Handle VALUE=DATE format (all-day events): 20251219
    if len(dt_str) == 8 and dt_str.isdigit():
        return datetime.strptime(dt_str, "%Y%m%d").replace(tzinfo=TIMEZONE)

    # Handle standard iCal datetime: 20251219T220000Z
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+0000"
        dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%S%z")
        return dt.astimezone(TIMEZONE)

    # Handle datetime with timezone: 20251219T220000
    try:
        return datetime.strptime(dt_str, "%Y%m%dT%H%M%S").replace(tzinfo=TIMEZONE)
    except ValueError:
        pass

    # Fallback: try to parse as date only
    return datetime.strptime(dt_str[:8], "%Y%m%d").replace(tzinfo=TIMEZONE)


def parse_ical(ical_data: str) -> list[dict]:
    """Parse iCal data and extract trip events."""
    trips = []
    current_event = {}
    in_event = False

    lines = ical_data.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Handle line folding (lines starting with space are continuations)
    unfolded_lines = []
    for line in lines:
        if line.startswith(" ") and unfolded_lines:
            unfolded_lines[-1] += line[1:]
        else:
            unfolded_lines.append(line)

    for line in unfolded_lines:
        line = line.strip()

        if line == "BEGIN:VEVENT":
            current_event = {}
            in_event = True
        elif line == "END:VEVENT":
            if in_event and current_event.get("uid"):
                # Only include main trip events (not individual bookings)
                # Main trips have "Summary: Location, Month Year" format
                summary = current_event.get("summary", "")
                if "," in summary and any(
                    month in summary
                    for month in [
                        "January",
                        "February",
                        "March",
                        "April",
                        "May",
                        "June",
                        "July",
                        "August",
                        "September",
                        "October",
                        "November",
                        "December",
                    ]
                ):
                    trips.append(
                        {
                            "trip_id": current_event["uid"],
                            "title": summary,
                            "location": current_event.get("location", ""),
                            "notes": current_event.get("description", ""),
                            "start_date": current_event.get("dtstart", ""),
                            "end_date": current_event.get("dtend", ""),
                            "start_iso": current_event.get("dtstart_iso", ""),
                            "end_iso": current_event.get("dtend_iso", ""),
                        }
                    )
            current_event = {}
            in_event = False
        elif in_event:
            if line.startswith("UID:"):
                current_event["uid"] = line[4:]
            elif line.startswith("SUMMARY:"):
                current_event["summary"] = line[8:]
            elif line.startswith("LOCATION:"):
                current_event["location"] = line[9:]
            elif line.startswith("DESCRIPTION:"):
                current_event["description"] = line[12:]
            elif line.startswith("DTSTART"):
                # Handle DTSTART;VALUE=DATE:20251219 or DTSTART:20251219T220000Z
                dt_val = line.split(":", 1)[1] if ":" in line else line
                current_event["dtstart"] = dt_val
                try:
                    dt = parse_ical_datetime(dt_val)
                    current_event["dtstart_iso"] = dt.isoformat()
                except Exception:
                    current_event["dtstart_iso"] = dt_val
            elif line.startswith("DTEND"):
                dt_val = line.split(":", 1)[1] if ":" in line else line
                current_event["dtend"] = dt_val
                try:
                    dt = parse_ical_datetime(dt_val)
                    current_event["dtend_iso"] = dt.isoformat()
                except Exception:
                    current_event["dtend_iso"] = dt_val

    return trips


def fetch_ical_feed(url: str) -> str:
    """Fetch iCal data from the provided URL."""
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"Error fetching iCal feed: HTTP {e.code}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching iCal feed: {e}", file=sys.stderr)
        sys.exit(1)


def load_processed(state_path: Path) -> set[str]:
    """Load set of already-processed trip IDs."""
    if not state_path.exists():
        return set()
    with open(state_path) as f:
        data = json.load(f)
    return {t["trip_id"] for t in data.get("processed", [])}


def main():
    parser = argparse.ArgumentParser(description="Fetch upcoming TripIt trips")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days ahead to look (default: 90)",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=STATE_DIR / "processed-trips.json",
        help="Path to processed trips state file",
    )
    parser.add_argument(
        "--include-processed",
        action="store_true",
        help="Include already-processed trips in output",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Override the TripIt iCal URL (defaults to TRIPIT_ICAL_URL env var or built-in URL)",
    )
    args = parser.parse_args()

    # Get URL from args, env var, or default
    url = args.url or os.environ.get("TRIPIT_ICAL_URL") or DEFAULT_TRIPIT_ICAL_URL

    today = datetime.now(TIMEZONE)
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"Fetching TripIt iCal feed from {url[:60]}...", file=sys.stderr)
    ical_data = fetch_ical_feed(url)
    print(f"Fetched {len(ical_data)} bytes of iCal data", file=sys.stderr)

    trips = parse_ical(ical_data)
    print(f"Found {len(trips)} trip events", file=sys.stderr)

    # Filter to only upcoming trips within date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=TIMEZONE)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=TIMEZONE)

    upcoming_trips = []
    for trip in trips:
        try:
            trip_start = datetime.fromisoformat(trip["start_iso"])
            if start_dt <= trip_start <= end_dt:
                upcoming_trips.append(trip)
        except Exception:
            # If we can't parse the date, include it anyway
            upcoming_trips.append(trip)

    trips = upcoming_trips
    print(f"Found {len(trips)} trips within date range", file=sys.stderr)

    if not args.include_processed:
        processed = load_processed(args.state)
        before = len(trips)
        trips = [t for t in trips if t["trip_id"] not in processed]
        if before != len(trips):
            print(
                f"Filtered out {before - len(trips)} already-processed trips",
                file=sys.stderr,
            )

    result = {
        "trips": trips,
        "start_date": start_date,
        "end_date": end_date,
        "total": len(trips),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import os

    main()
