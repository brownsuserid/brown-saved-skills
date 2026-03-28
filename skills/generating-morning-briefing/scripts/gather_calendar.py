#!/usr/bin/env python3
"""
Gather calendar events and compute briefing stats for a single day.

Uses fetch_events.py as the shared data layer for Google and Apple calendar
queries. Adds briefing-specific analysis: conflict detection, buffer warnings,
in-person travel time, free windows, and BB/AITB overcommit checks.

Usage:
    python3 gather_calendar.py [--date 2026-02-06]

Output:
    JSON with events array and stats (conflicts, no_buffer, meeting_hours,
    free_windows, bb_aitb_warning).
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import shared calendar data layer
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[3]
        / "finding-calendar-availability"
        / "scripts"
    ),
)
from fetch_events import get_all_events  # noqa: E402

# Travel buffer added before and after in-person meetings (minutes)
TRAVEL_BUFFER_MINUTES = 30

# Business hours for BB/AITB overcommit check and free window calculation
BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17

# Google calendar source labels that count toward the BB/AITB overcommit check
OVERCOMMIT_SOURCES = {"google:BB", "google:AITB"}

# Apple calendar source label that marks an Intuit workday
INTUIT_WORK_SOURCES = {"apple:Intuit", "apple:Work"}


def _format_time(iso_str: str) -> str:
    """Convert ISO datetime to 12-hour time string like '9:30 AM'."""
    if not iso_str:
        return ""
    try:
        # Handle both offset and non-offset formats
        clean = iso_str.split("-07:00")[0].split("+")[0].split("Z")[0]
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%-I:%M %p")
    except (ValueError, IndexError):
        return iso_str


def _parse_dt(iso_str: str) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not iso_str:
        return None
    try:
        clean = iso_str.split("-07:00")[0].split("+")[0].split("Z")[0]
        return datetime.fromisoformat(clean)
    except (ValueError, IndexError):
        return None


def enrich_events(events: list[dict]) -> list[dict]:
    """Add briefing-specific fields to events from fetch_events."""
    enriched = []
    for evt in events:
        evt["time"] = _format_time(evt["start_iso"])
        evt["end_time"] = _format_time(evt["end_iso"])
        enriched.append(evt)
    return enriched


def filter_buffer_events(events: list[dict]) -> list[dict]:
    """Remove events with 'buffer' in the title."""
    return [e for e in events if "buffer" not in e["title"].lower()]


def detect_conflicts(events: list[dict]) -> list[dict]:
    """Find overlapping events."""
    sorted_events = sorted(events, key=lambda e: e["start_iso"])
    conflicts = []
    for i in range(len(sorted_events) - 1):
        end_dt = _parse_dt(sorted_events[i]["end_iso"])
        next_start_dt = _parse_dt(sorted_events[i + 1]["start_iso"])
        if end_dt and next_start_dt and end_dt > next_start_dt:
            conflicts.append(
                {
                    "event_a": sorted_events[i]["title"],
                    "event_b": sorted_events[i + 1]["title"],
                    "overlap_minutes": int(
                        (end_dt - next_start_dt).total_seconds() / 60
                    ),
                }
            )
    return conflicts


def detect_no_buffer(events: list[dict], min_gap_minutes: int = 15) -> list[dict]:
    """Find consecutive events with less than min_gap_minutes between them."""
    sorted_events = sorted(events, key=lambda e: e["start_iso"])
    no_buffer = []
    for i in range(len(sorted_events) - 1):
        end_dt = _parse_dt(sorted_events[i]["end_iso"])
        next_start_dt = _parse_dt(sorted_events[i + 1]["start_iso"])
        if end_dt and next_start_dt:
            gap = (next_start_dt - end_dt).total_seconds() / 60
            if 0 <= gap < min_gap_minutes:
                no_buffer.append(
                    {
                        "event_a": sorted_events[i]["title"],
                        "event_b": sorted_events[i + 1]["title"],
                        "gap_minutes": int(gap),
                    }
                )
    return no_buffer


def compute_free_windows(
    events: list[dict],
    date_str: str,
    travel_minutes: int = TRAVEL_BUFFER_MINUTES,
    start_hour: int = BUSINESS_START_HOUR,
    end_hour: int = BUSINESS_END_HOUR,
    min_gap_minutes: int = 15,
) -> list[dict]:
    """Return free time windows during business hours, accounting for travel.

    In-person events consume an extra `travel_minutes` before and after
    (representing travel time), so the effective blocked window is wider.
    """
    year, month, day = (int(p) for p in date_str.split("-"))
    biz_start = datetime(year, month, day, start_hour, 0)
    biz_end = datetime(year, month, day, end_hour, 0)

    # Build list of (effective_start, effective_end) blocks
    blocks: list[tuple[datetime, datetime]] = []
    for evt in events:
        s = _parse_dt(evt["start_iso"])
        e = _parse_dt(evt["end_iso"])
        if not s or not e:
            continue
        # Clip to business hours
        s = max(s, biz_start)
        e = min(e, biz_end)
        if e <= s:
            continue
        if evt.get("in_person"):
            s = max(s - timedelta(minutes=travel_minutes), biz_start)
            e = min(e + timedelta(minutes=travel_minutes), biz_end)
        blocks.append((s, e))

    if not blocks:
        return [
            {
                "start": _format_time(biz_start.isoformat()),
                "end": _format_time(biz_end.isoformat()),
                "duration_minutes": (end_hour - start_hour) * 60,
            }
        ]

    # Merge overlapping blocks
    blocks.sort()
    merged: list[tuple[datetime, datetime]] = [blocks[0]]
    for s, e in blocks[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # Find gaps
    windows = []
    cursor = biz_start
    for s, e in merged:
        if (s - cursor).total_seconds() / 60 >= min_gap_minutes:
            windows.append(
                {
                    "start": _format_time(cursor.isoformat()),
                    "end": _format_time(s.isoformat()),
                    "duration_minutes": int((s - cursor).total_seconds() / 60),
                }
            )
        cursor = max(cursor, e)
    if (biz_end - cursor).total_seconds() / 60 >= min_gap_minutes:
        windows.append(
            {
                "start": _format_time(cursor.isoformat()),
                "end": _format_time(biz_end.isoformat()),
                "duration_minutes": int((biz_end - cursor).total_seconds() / 60),
            }
        )
    return windows


def detect_bb_aitb_overcommit(
    events: list[dict],
    date_str: str,
    threshold_minutes: int = 120,
) -> dict | None:
    """Warn if BB/AITB meetings exceed threshold on an Intuit workday.

    An Intuit workday is defined as any day where the Work calendar has at
    least one timed event during business hours.
    """
    year, month, day = (int(p) for p in date_str.split("-"))
    biz_start = datetime(year, month, day, BUSINESS_START_HOUR, 0)
    biz_end = datetime(year, month, day, BUSINESS_END_HOUR, 0)

    # Is it an Intuit workday?
    intuit_events = [e for e in events if e.get("source") in INTUIT_WORK_SOURCES]
    is_workday = any(
        (s := _parse_dt(e["start_iso"]))
        and (en := _parse_dt(e["end_iso"]))
        and s < biz_end
        and en > biz_start
        for e in intuit_events
    )
    if not is_workday:
        return None

    # Sum BB + AITB minutes overlapping business hours
    bb_aitb_minutes = 0
    for evt in events:
        if evt.get("source") not in OVERCOMMIT_SOURCES:
            continue
        s = _parse_dt(evt["start_iso"])
        e = _parse_dt(evt["end_iso"])
        if not s or not e:
            continue
        overlap_start = max(s, biz_start)
        overlap_end = min(e, biz_end)
        if overlap_end > overlap_start:
            bb_aitb_minutes += (overlap_end - overlap_start).total_seconds() / 60

    if bb_aitb_minutes <= threshold_minutes:
        return None

    free_windows = compute_free_windows(events, date_str)
    return {
        "message": (
            f"BB/AITB meetings total {round(bb_aitb_minutes / 60, 1)}h during Intuit work hours "
            f"(threshold: {threshold_minutes // 60}h). Consider rescheduling."
        ),
        "bb_aitb_hours": round(bb_aitb_minutes / 60, 1),
        "threshold_hours": threshold_minutes / 60,
        "free_windows": free_windows,
    }


def calculate_stats(
    events: list[dict],
    conflicts: list[dict],
    no_buffer: list[dict],
    date_str: str,
) -> dict:
    """Calculate summary statistics."""
    total_minutes = 0
    for evt in events:
        start = _parse_dt(evt["start_iso"])
        end = _parse_dt(evt["end_iso"])
        if start and end:
            total_minutes += (end - start).total_seconds() / 60

    in_person_events = [e["title"] for e in events if e.get("in_person")]
    free_windows = compute_free_windows(events, date_str)
    bb_aitb_warning = detect_bb_aitb_overcommit(events, date_str)

    return {
        "total_events": len(events),
        "meeting_hours": round(total_minutes / 60, 1),
        "conflicts": conflicts,
        "no_buffer": no_buffer,
        "free_windows": free_windows,
        "in_person_meetings": in_person_events,
        "bb_aitb_warning": bb_aitb_warning,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Gather calendar events for morning briefing"
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to fetch events for (YYYY-MM-DD, default: today)",
    )
    args = parser.parse_args()

    # Fetch events using shared data layer (single-day range)
    event_data = get_all_events(args.date, args.date)
    all_events = event_data.get("events", [])

    # Enrich with briefing-specific fields and filter
    all_events = enrich_events(all_events)
    all_events = filter_buffer_events(all_events)
    all_events.sort(key=lambda e: e["start_iso"])

    conflicts = detect_conflicts(all_events)
    no_buffer = detect_no_buffer(all_events)
    stats = calculate_stats(all_events, conflicts, no_buffer, args.date)

    result = {
        "events": all_events,
        "stats": stats,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
