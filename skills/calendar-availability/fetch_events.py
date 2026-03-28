#!/usr/bin/env python3
"""
Fetch calendar events from Google calendars (gog) and Apple calendars (EventKit)
for a date range. Shared data layer for all calendar scripts.

Usage:
    python3 fetch_events.py --start 2026-02-09 --end 2026-02-13

Output:
    JSON with events array across all calendars.
"""

import argparse
import json
import subprocess  # nosec B404 - used to call gog CLI with static args
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import os

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def resolve_config_path(cli_config: str | None = None) -> Path:
    """Resolve config file path: --config flag > env var > default."""
    if cli_config:
        return Path(cli_config)
    env_config = os.environ.get("OPENCLAW_CALENDAR_CONFIG")
    if env_config:
        return Path(env_config)
    return DEFAULT_CONFIG_PATH


# Title keywords that mark a meeting as in-person
IN_PERSON_KEYWORDS = [
    "in-person",
    "in person",
    "(irl)",
    "[irl]",
    "@office",
    "offsite",
    "on-site",
    "onsite",
]

# Video-call URL patterns — a location containing these is NOT in-person
VIDEO_URL_PATTERNS = [
    "zoom.us",
    "meet.google",
    "teams.microsoft",
    "webex",
    "whereby",
    "around.co",
    "loom.com",
]


def load_config(config_path: str | Path | None = None) -> dict:
    """Load calendar configuration from a YAML config file.

    Resolution order: explicit path > OPENCLAW_CALENDAR_CONFIG env var > default config.yaml.
    """
    path = resolve_config_path(str(config_path) if config_path else None)
    if not path.exists():
        print(f"Error: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def get_timezone(config: dict) -> ZoneInfo:
    """Get the configured timezone."""
    return ZoneInfo(config.get("timezone", "America/Phoenix"))


def is_in_person(evt: dict) -> bool:
    """Return True if the event appears to be in-person.

    Checks title keywords first, then inspects the location field:
    a non-empty location that is not a video-call URL is treated as physical.
    """
    title = evt.get("title", "").lower()
    if any(kw in title for kw in IN_PERSON_KEYWORDS):
        return True
    location = (evt.get("location") or "").lower()
    if location and not any(p in location for p in VIDEO_URL_PATTERNS):
        return True
    return False


def _extract_google_response_status(evt: dict) -> str:
    """Extract current user's response status from Google Calendar event attendees."""
    for attendee in evt.get("attendees", []):
        if attendee.get("self"):
            return attendee.get("responseStatus", "unknown")
    return "accepted"  # organizer with no attendee list


def fetch_google_events(
    start_date: str, end_date: str, config: dict, succeeded: list[str] | None = None
) -> list[dict]:
    """Fetch events from all Google calendars via gog CLI for a date range.

    If succeeded is provided, appends the account name of each calendar
    that returned data successfully.
    """
    events = []
    tz = get_timezone(config)
    tz_offset = datetime.now(tz).strftime("%z")
    tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}"

    for cal in config.get("google_calendars", []):
        label = cal["label"]
        account = cal["account"]
        cal_id = cal.get("calendar_id", "primary")

        try:
            result = subprocess.run(  # nosec B603 B607 - static gog CLI call
                [
                    "gog",
                    "calendar",
                    "events",
                    "--account",
                    account,
                    cal_id,
                    "--from",
                    f"{start_date}T00:00:00{tz_offset_formatted}",
                    "--to",
                    f"{end_date}T23:59:59{tz_offset_formatted}",
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

        if succeeded is not None:
            succeeded.append(account)

        for evt in data.get("events", []):
            summary = evt.get("summary", "")
            start = evt.get("start", {})
            end = evt.get("end", {})
            start_dt = start.get("dateTime", "")
            end_dt = end.get("dateTime", "")

            # Skip all-day events (no dateTime, only date)
            if not start_dt or not end_dt:
                continue

            # Determine if user has declined this event
            declined = False
            tentative = False
            response_status = _extract_google_response_status(evt)
            if response_status == "declined":
                declined = True
            elif response_status == "tentative":
                tentative = True

            event_dict = {
                "title": summary,
                "source": f"google:{label}",
                "calendar": account,
                "link": evt.get("htmlLink"),
                "location": evt.get("location") or None,
                "start_iso": start_dt,
                "end_iso": end_dt,
                "declined": declined,
                "tentative": tentative,
                "response_status": response_status,
                "in_person": False,
            }
            event_dict["in_person"] = is_in_person(event_dict)
            events.append(event_dict)

    return events


def _extract_apple_response_status(
    evt: object,
    participant_map: dict[int, str],
    event_status_map: dict[int, str],
) -> str:
    """Extract response status from an EventKit event.

    Checks attendee-level status first (current user), then falls back
    to event-level status. Exchange/Outlook events often have no attendee
    data, so event status is the best we can get.
    """
    attendees = evt.attendees()  # type: ignore[union-attr]
    if attendees:
        for a in attendees:
            if a.isCurrentUser():
                return participant_map.get(a.participantStatus(), "unknown")

    event_status = evt.status()  # type: ignore[union-attr]
    return event_status_map.get(event_status, "unknown")


def fetch_apple_events(
    start_date: str, end_date: str, config: dict, succeeded: list[str] | None = None
) -> list[dict]:
    """Fetch events from macOS Calendar via EventKit for a date range.

    If succeeded is provided, appends the name of each Apple calendar
    that was successfully queried.
    """
    try:
        import EventKit
        from Foundation import NSCalendar, NSDateComponents
    except ImportError:
        print(
            "Warning: pyobjc-framework-EventKit not installed, skipping Apple calendars",
            file=sys.stderr,
        )
        return []

    apple_calendars = config.get("apple_calendars", [])
    cal_to_source = {c["name"]: c["source"] for c in apple_calendars}
    target_names = {c["name"] for c in apple_calendars}

    tz = get_timezone(config)

    store = EventKit.EKEventStore.alloc().init()

    # Request calendar access (macOS 14+ uses requestFullAccessToEvents)
    import threading

    access_granted = threading.Event()
    access_result = [False]

    def completion(granted, error):
        access_result[0] = granted
        access_granted.set()

    if hasattr(store, "requestFullAccessToEventsWithCompletion_"):
        store.requestFullAccessToEventsWithCompletion_(completion)
    else:
        store.requestAccessToEntityType_completion_(0, completion)
    access_granted.wait(timeout=10)

    if not access_result[0]:
        print(
            "Warning: Calendar access not granted, skipping Apple calendars",
            file=sys.stderr,
        )
        return []

    all_cals = store.calendarsForEntityType_(0)  # EKEntityTypeEvent
    target_cals = [c for c in all_cals if c.title() in target_names]

    if not target_cals:
        print("Warning: No matching Apple calendars found", file=sys.stderr)
        return []

    if succeeded is not None:
        for c in target_cals:
            succeeded.append(str(c.title()))

    ns_cal = NSCalendar.currentCalendar()

    # Parse start date
    s_year, s_month, s_day = (int(p) for p in start_date.split("-"))
    start_comps = NSDateComponents.alloc().init()
    start_comps.setYear_(s_year)
    start_comps.setMonth_(s_month)
    start_comps.setDay_(s_day)
    start_comps.setHour_(0)
    start_comps.setMinute_(0)
    start_comps.setSecond_(0)
    ns_start = ns_cal.dateFromComponents_(start_comps)

    # Parse end date
    e_year, e_month, e_day = (int(p) for p in end_date.split("-"))
    end_comps = NSDateComponents.alloc().init()
    end_comps.setYear_(e_year)
    end_comps.setMonth_(e_month)
    end_comps.setDay_(e_day)
    end_comps.setHour_(23)
    end_comps.setMinute_(59)
    end_comps.setSecond_(59)
    ns_end = ns_cal.dateFromComponents_(end_comps)

    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(
        ns_start, ns_end, target_cals
    )
    ek_events = store.eventsMatchingPredicate_(predicate)

    # EKEventStatus: 0=none, 1=confirmed, 2=tentative, 3=cancelled
    # EKParticipantStatus: 0=unknown, 1=pending, 2=accepted, 3=declined, 4=tentative
    ek_participant_map = {
        0: "unknown",
        1: "needsAction",
        2: "accepted",
        3: "declined",
        4: "tentative",
        5: "delegated",
    }
    ek_event_status_map = {0: "unknown", 1: "accepted", 2: "tentative", 3: "cancelled"}

    events = []
    for evt in ek_events:
        # Skip all-day events
        if evt.isAllDay():
            continue

        cal_name = str(evt.calendar().title())
        source = cal_to_source.get(cal_name, cal_name)
        start_ts = evt.startDate().timeIntervalSince1970()
        end_ts = evt.endDate().timeIntervalSince1970()

        # Use timezone-aware datetimes
        start_dt = datetime.fromtimestamp(start_ts, tz=tz)
        end_dt = datetime.fromtimestamp(end_ts, tz=tz)

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        response_status = _extract_apple_response_status(
            evt, ek_participant_map, ek_event_status_map
        )

        raw_location = evt.location()
        location_str = str(raw_location) if raw_location else None

        event_dict = {
            "title": str(evt.title()),
            "source": f"apple:{source}",
            "calendar": cal_name,
            "link": None,
            "location": location_str,
            "start_iso": start_iso,
            "end_iso": end_iso,
            "declined": response_status == "declined",
            "tentative": response_status == "tentative",
            "response_status": response_status,
            "in_person": False,
        }
        event_dict["in_person"] = is_in_person(event_dict)
        events.append(event_dict)

    return events


def deduplicate_events(events: list[dict]) -> list[dict]:
    """Remove duplicates based on title and start time.

    When the same event appears in both Google and Apple calendars,
    prefer the Google version (richer metadata).
    """
    seen: dict[tuple[str, str], dict] = {}

    for evt in events:
        # Normalize the start time for comparison (strip to minute precision)
        start_normalized = evt["start_iso"][:16]
        key = (evt["title"], start_normalized)
        existing = seen.get(key)

        if existing is None:
            seen[key] = evt
        elif existing["source"].startswith("apple:") and evt["source"].startswith(
            "google:"
        ):
            # Prefer Google version (has declined/tentative metadata)
            seen[key] = evt

    return list(seen.values())


def get_all_events(start_date: str, end_date: str, config: dict | None = None) -> dict:
    """Fetch, deduplicate, and return all calendar events.

    This is the main entry point for programmatic use.
    """
    if config is None:
        config = load_config()

    succeeded: list[str] = []
    google_events = fetch_google_events(start_date, end_date, config, succeeded)
    apple_events = fetch_apple_events(start_date, end_date, config, succeeded)

    all_events = google_events + apple_events
    all_events = deduplicate_events(all_events)
    all_events.sort(key=lambda e: e["start_iso"])

    return {
        "events": all_events,
        "start_date": start_date,
        "end_date": end_date,
        "calendars_checked": succeeded,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch calendar events for a date range"
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: OPENCLAW_CALENDAR_CONFIG env var or config.yaml)",
    )
    parser.add_argument(
        "--start",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--end",
        default=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD, default: 7 days from now)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    result = get_all_events(args.start, args.end, config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
