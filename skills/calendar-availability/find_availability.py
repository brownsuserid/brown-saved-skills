#!/usr/bin/env python3
"""
Find available time slots across multiple calendars.

Queries Google and Apple calendars, then finds gaps that can accommodate
the requested meeting duration within the specified time-of-day constraints.

Usage:
    python3 find_availability.py --duration 60 --time-of-day afternoon --start 2026-02-09 --end 2026-02-13

Output:
    JSON with available slots, or human-readable format with --human flag.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_events import get_all_events, get_timezone, load_config

# Time of day definitions (24-hour format)
TIME_FILTERS = {
    "morning": (8, 12),  # 8 AM - 12 PM
    "afternoon": (12, 17),  # 12 PM - 5 PM
    "evening": (17, 20),  # 5 PM - 8 PM
    "business": (9, 17),  # 9 AM - 5 PM
    "any": (8, 20),  # 8 AM - 8 PM
}


def parse_iso_datetime(iso_str: str, tz: ZoneInfo) -> datetime:
    """Parse ISO datetime string to a timezone-aware datetime in the target tz."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def format_time_12h(dt: datetime) -> str:
    """Format datetime to 12-hour time string like '1:00 PM'."""
    return dt.strftime("%-I:%M %p")


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments."""
    if args.duration <= 0:
        print("Error: --duration must be positive", file=sys.stderr)
        sys.exit(1)

    if args.min_gap < 0:
        print("Error: --min-gap cannot be negative", file=sys.stderr)
        sys.exit(1)

    if args.max_slots <= 0:
        print("Error: --max-slots must be positive", file=sys.stderr)
        sys.exit(1)

    try:
        datetime.strptime(args.start, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid start date format: {args.start}", file=sys.stderr)
        sys.exit(1)

    if args.end:
        try:
            datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid end date format: {args.end}", file=sys.stderr)
            sys.exit(1)

        if args.end < args.start:
            print("Error: End date must not be before start date", file=sys.stderr)
            sys.exit(1)


def get_busy_periods(
    events: list[dict], date: str, tz: ZoneInfo
) -> list[tuple[datetime, datetime]]:
    """Extract busy periods for a specific date, excluding declined events."""
    busy = []
    target_date = datetime.strptime(date, "%Y-%m-%d").date()

    for evt in events:
        # Skip declined events — they don't block availability
        if evt.get("declined", False):
            continue

        start_dt = parse_iso_datetime(evt["start_iso"], tz)
        end_dt = parse_iso_datetime(evt["end_iso"], tz)

        # Check if event overlaps with this date
        if start_dt.date() > target_date or end_dt.date() < target_date:
            continue

        # Clip event to this date's boundaries
        day_start = datetime(
            target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=tz
        )
        day_end = datetime(
            target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=tz
        )

        actual_start = max(start_dt, day_start)
        actual_end = min(end_dt, day_end)

        if actual_start < actual_end:
            busy.append((actual_start, actual_end))

    # Sort by start time
    busy.sort(key=lambda x: x[0])

    # Merge overlapping periods
    merged: list[tuple[datetime, datetime]] = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return merged


def find_slots_for_day(
    date: str,
    busy_periods: list[tuple[datetime, datetime]],
    duration_minutes: int,
    time_filter: tuple[int, int],
    min_gap_minutes: int,
    tz: ZoneInfo,
    compact: bool = False,
) -> list[dict]:
    """Find all available slots for a single day.

    If compact is True, returns one slot per free window (the earliest fit)
    instead of every 15-minute increment.
    """
    slots = []

    year, month, day = (int(p) for p in date.split("-"))

    window_start_hour, window_end_hour = time_filter
    window_start = datetime(year, month, day, window_start_hour, 0, tzinfo=tz)
    window_end = datetime(year, month, day, window_end_hour, 0, tzinfo=tz)

    # Build list of free periods within the window
    free_periods: list[tuple[datetime, datetime]] = []
    current_start = window_start

    for busy_start, busy_end in busy_periods:
        # Skip busy periods entirely outside our window
        if busy_end <= window_start or busy_start >= window_end:
            continue

        # Clip busy period to window
        busy_start = max(busy_start, window_start)
        busy_end = min(busy_end, window_end)

        # Free time before this busy period (with buffer)
        if current_start < busy_start:
            free_end = busy_start - timedelta(minutes=min_gap_minutes)
            if current_start < free_end:
                free_periods.append((current_start, free_end))

        # Move current start past this busy period plus buffer
        current_start = busy_end + timedelta(minutes=min_gap_minutes)

    # Free time after all busy periods
    if current_start < window_end:
        free_periods.append((current_start, window_end))

    # Find all slots that fit within each free period
    duration = timedelta(minutes=duration_minutes)
    day_name = datetime(year, month, day).strftime("%A")

    for free_start, free_end in free_periods:
        # Round start up to nearest 15 minutes
        slot_start = free_start
        minute = slot_start.minute
        if minute % 15 != 0:
            rounded_minute = ((minute // 15) + 1) * 15
            if rounded_minute == 60:
                slot_start = slot_start.replace(minute=0) + timedelta(hours=1)
            else:
                slot_start = slot_start.replace(minute=rounded_minute)

        # Generate slots at 15-minute increments (or just the first if compact)
        while slot_start + duration <= free_end:
            slot_end = slot_start + duration
            slots.append(
                {
                    "date": date,
                    "day": day_name,
                    "start": format_time_12h(slot_start),
                    "end": format_time_12h(slot_end),
                    "start_iso": slot_start.isoformat(),
                    "end_iso": slot_end.isoformat(),
                }
            )
            if compact:
                break
            slot_start += timedelta(minutes=15)

    return slots


def format_human_output(result: dict) -> str:
    """Format results as human-readable text."""
    query = result["query"]
    slots = result["slots"]

    duration_str = f"{query['duration_minutes']}-minute"
    if query["duration_minutes"] >= 60:
        hours = query["duration_minutes"] / 60
        if hours == int(hours):
            duration_str = f"{int(hours)}-hour"
        else:
            duration_str = f"{hours:.1f}-hour"

    time_of_day = query["time_of_day"]
    if time_of_day == "business":
        time_of_day = "business hours"
    elif time_of_day == "any":
        time_of_day = ""

    # Format date range
    start_dt = datetime.strptime(query["start_date"], "%Y-%m-%d")
    end_dt = datetime.strptime(query["end_date"], "%Y-%m-%d")

    if start_dt == end_dt:
        date_range = start_dt.strftime("%b %-d")
    else:
        date_range = f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%b %-d')}"

    lines = []

    # Always include timezone in output — Arizona doesn't observe DST
    tz_label = "Arizona time (MST)"

    if time_of_day:
        lines.append(
            f"Available {duration_str} {time_of_day} slots ({date_range}), {tz_label}:"
        )
    else:
        lines.append(f"Available {duration_str} slots ({date_range}), {tz_label}:")

    lines.append("")

    if not slots:
        lines.append("  No available slots found.")
    else:
        for slot in slots:
            slot_dt = datetime.strptime(slot["date"], "%Y-%m-%d")
            formatted_date = slot_dt.strftime("%A, %b %-d")
            lines.append(f"  {formatted_date}: {slot['start']} - {slot['end']}")

    lines.append("")
    lines.append(
        f"{len(slots)} slot(s) found across {len(result['calendars_checked'])} calendars."
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Find available time slots across calendars"
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: OPENCLAW_CALENDAR_CONFIG env var or config.yaml)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Required meeting duration in minutes (default: 60)",
    )
    parser.add_argument(
        "--start",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD, default: 7 days from start)",
    )
    parser.add_argument(
        "--time-of-day",
        choices=["morning", "afternoon", "evening", "business", "any"],
        default="business",
        help="Time of day filter (default: business)",
    )
    parser.add_argument(
        "--min-gap",
        type=int,
        default=15,
        help="Minimum buffer before/after in minutes (default: 15)",
    )
    parser.add_argument(
        "--max-slots",
        type=int,
        default=10,
        help="Maximum slots to return (default: 10)",
    )
    parser.add_argument(
        "--include-weekends",
        action="store_true",
        help="Include weekends in results (default: skip weekends for all filters except 'any')",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Return one slot per free window instead of every 15-min increment",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Output human-readable text instead of JSON",
    )
    parser.add_argument(
        "--ignore-calendars",
        nargs="+",
        metavar="NAME",
        help="Calendar labels/names to ignore (e.g., Work BB Personal). Matches against Google label or Apple calendar name, case-insensitive.",
    )

    args = parser.parse_args()
    validate_args(args)

    # Calculate end date if not provided
    start_date = args.start
    if args.end:
        end_date = args.end
    else:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=7)
        end_date = end_dt.strftime("%Y-%m-%d")

    config = load_config(args.config)
    tz = get_timezone(config)

    # Fetch events
    event_data = get_all_events(start_date, end_date, config)
    events = event_data.get("events", [])
    calendars_checked = event_data.get("calendars_checked", [])

    # Filter out ignored calendars
    if args.ignore_calendars:
        ignore_set = {name.lower() for name in args.ignore_calendars}

        def _should_keep(evt: dict) -> bool:
            # Check calendar name (Apple) or source label (Google)
            cal_name = (evt.get("calendar") or "").lower()
            source = (evt.get("source") or "").lower()
            # source is like "google:BB" or "apple:Intuit"
            source_label = source.split(":", 1)[1] if ":" in source else source
            return cal_name not in ignore_set and source_label not in ignore_set

        events = [e for e in events if _should_keep(e)]

    # Get time filter
    time_filter = TIME_FILTERS[args.time_of_day]

    # Find slots for each day in range
    all_slots: list[dict] = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        # Skip weekends unless explicitly included or using "any" filter
        skip_weekends = args.time_of_day != "any" and not args.include_weekends
        if skip_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        busy = get_busy_periods(events, date_str, tz)
        day_slots = find_slots_for_day(
            date_str,
            busy,
            args.duration,
            time_filter,
            args.min_gap,
            tz,
            compact=args.compact,
        )
        all_slots.extend(day_slots)

        if len(all_slots) >= args.max_slots:
            all_slots = all_slots[: args.max_slots]
            break

        current += timedelta(days=1)

    result = {
        "query": {
            "start_date": start_date,
            "end_date": end_date,
            "duration_minutes": args.duration,
            "time_of_day": args.time_of_day,
            "min_gap_minutes": args.min_gap,
            "timezone": str(tz),
        },
        "slots": all_slots,
        "total_slots": len(all_slots),
        "calendars_checked": calendars_checked,
    }

    if args.human:
        print(format_human_output(result))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
