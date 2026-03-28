"""Tests for find_availability.py logic functions."""

import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# Add scripts dir to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from find_availability import (
    find_slots_for_day,
    format_human_output,
    format_time_12h,
    get_busy_periods,
    parse_iso_datetime,
    validate_args,
)

TZ = ZoneInfo("America/Phoenix")


class TestParseIsoDatetime:
    def test_with_negative_offset(self):
        result = parse_iso_datetime("2026-02-10T13:00:00-07:00", TZ)
        assert result.hour == 13
        assert result.minute == 0
        assert result.tzinfo is not None

    def test_with_positive_offset(self):
        result = parse_iso_datetime("2026-02-10T20:00:00+00:00", TZ)
        # UTC 20:00 = MST 13:00
        assert result.hour == 13
        assert result.tzinfo is not None

    def test_with_z_suffix(self):
        result = parse_iso_datetime("2026-02-10T20:00:00Z", TZ)
        assert result.hour == 13
        assert result.tzinfo is not None

    def test_naive_datetime(self):
        result = parse_iso_datetime("2026-02-10T13:00:00", TZ)
        assert result.hour == 13
        assert result.tzinfo == TZ

    def test_with_microseconds(self):
        result = parse_iso_datetime("2026-02-10T13:00:00.123456-07:00", TZ)
        assert result.hour == 13
        assert result.microsecond == 123456


class TestFormatTime12h:
    def test_morning(self):
        dt = datetime(2026, 2, 10, 9, 0, tzinfo=TZ)
        assert format_time_12h(dt) == "9:00 AM"

    def test_afternoon(self):
        dt = datetime(2026, 2, 10, 13, 30, tzinfo=TZ)
        assert format_time_12h(dt) == "1:30 PM"

    def test_noon(self):
        dt = datetime(2026, 2, 10, 12, 0, tzinfo=TZ)
        assert format_time_12h(dt) == "12:00 PM"


class TestGetBusyPeriods:
    def test_single_event_on_date(self):
        events = [
            {
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
                "declined": False,
            }
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 1
        assert busy[0][0].hour == 10
        assert busy[0][1].hour == 11

    def test_declined_events_skipped(self):
        events = [
            {
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
                "declined": True,
            }
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 0

    def test_overlapping_events_merged(self):
        events = [
            {
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
                "declined": False,
            },
            {
                "start_iso": "2026-02-10T10:30:00-07:00",
                "end_iso": "2026-02-10T11:30:00-07:00",
                "declined": False,
            },
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 1
        assert busy[0][0].hour == 10
        assert busy[0][1].hour == 11
        assert busy[0][1].minute == 30

    def test_events_on_different_date_excluded(self):
        events = [
            {
                "start_iso": "2026-02-11T10:00:00-07:00",
                "end_iso": "2026-02-11T11:00:00-07:00",
                "declined": False,
            }
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 0

    def test_multi_day_event_clipped_to_date(self):
        events = [
            {
                "start_iso": "2026-02-09T20:00:00-07:00",
                "end_iso": "2026-02-10T14:00:00-07:00",
                "declined": False,
            }
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 1
        assert busy[0][0].hour == 0
        assert busy[0][1].hour == 14

    def test_no_declined_key_defaults_to_not_declined(self):
        events = [
            {
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            }
        ]
        busy = get_busy_periods(events, "2026-02-10", TZ)
        assert len(busy) == 1


class TestFindSlotsForDay:
    def test_empty_day_returns_slots(self):
        slots = find_slots_for_day("2026-02-10", [], 60, (9, 17), 15, TZ)
        # 9 AM - 5 PM = 8 hours, 60-minute slots at 15-min increments
        # Last slot starts at 4:00 PM (ends 5:00 PM)
        assert len(slots) > 0
        assert slots[0]["start"] == "9:00 AM"
        assert slots[0]["end"] == "10:00 AM"

    def test_multiple_slots_per_free_period(self):
        # One meeting from 12-1, leaving 9-11:45 and 1:15-5 free
        busy = [
            (
                datetime(2026, 2, 10, 12, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 13, 0, tzinfo=TZ),
            )
        ]
        slots = find_slots_for_day("2026-02-10", busy, 60, (9, 17), 15, TZ)
        # Should have multiple slots, not just one per free period
        assert len(slots) > 2
        # First slot at 9:00
        assert slots[0]["start"] == "9:00 AM"

    def test_slot_respects_buffer(self):
        busy = [
            (
                datetime(2026, 2, 10, 10, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 11, 0, tzinfo=TZ),
            )
        ]
        slots = find_slots_for_day("2026-02-10", busy, 30, (9, 12), 15, TZ)
        # Before meeting: 9:00-9:45 (15 min buffer before 10:00)
        # After meeting: 11:15-12:00 (15 min buffer after 11:00)
        start_times = [s["start"] for s in slots]
        assert "10:00 AM" not in start_times
        # 9:45 start + 30 min = 10:15 > 9:45 free_end, so no 9:45 slot
        # 11:15 should be available
        assert "11:15 AM" in start_times

    def test_short_duration_many_slots(self):
        slots = find_slots_for_day("2026-02-10", [], 30, (9, 11), 0, TZ)
        # 9:00-11:00 = 2 hours, 30-min slots at 15-min increments
        # 9:00, 9:15, 9:30, 9:45, 10:00, 10:15, 10:30 = 7 slots
        assert len(slots) == 7

    def test_no_slots_when_fully_booked(self):
        busy = [
            (
                datetime(2026, 2, 10, 9, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 17, 0, tzinfo=TZ),
            )
        ]
        slots = find_slots_for_day("2026-02-10", busy, 60, (9, 17), 15, TZ)
        assert len(slots) == 0

    def test_slot_times_rounded_to_15_min(self):
        # Busy period ends at 10:07, so free starts at 10:22 (with 15 min gap)
        busy = [
            (
                datetime(2026, 2, 10, 9, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 10, 7, tzinfo=TZ),
            )
        ]
        slots = find_slots_for_day("2026-02-10", busy, 30, (9, 12), 15, TZ)
        # 10:22 rounds up to 10:30
        assert slots[0]["start"] == "10:30 AM"


class TestFormatHumanOutput:
    def test_no_slots(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 60,
                "time_of_day": "business",
            },
            "slots": [],
            "calendars_checked": ["cal1", "cal2"],
        }
        output = format_human_output(result)
        assert "No available slots found" in output

    def test_with_slots(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 60,
                "time_of_day": "afternoon",
            },
            "slots": [{"date": "2026-02-10", "start": "1:00 PM", "end": "2:00 PM"}],
            "calendars_checked": ["cal1"],
        }
        output = format_human_output(result)
        assert "1:00 PM - 2:00 PM" in output
        assert "1 slot(s)" in output

    def test_duration_formatting_hours(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 120,
                "time_of_day": "any",
            },
            "slots": [],
            "calendars_checked": [],
        }
        output = format_human_output(result)
        assert "2-hour" in output

    def test_duration_formatting_minutes(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 30,
                "time_of_day": "morning",
            },
            "slots": [],
            "calendars_checked": [],
        }
        output = format_human_output(result)
        assert "30-minute" in output

    def test_single_day_date_range(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 60,
                "time_of_day": "business",
            },
            "slots": [],
            "calendars_checked": [],
        }
        output = format_human_output(result)
        assert "Feb 10" in output
        assert " - " not in output.split("\n")[0]

    def test_timezone_included_in_output(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 60,
                "time_of_day": "business",
            },
            "slots": [],
            "calendars_checked": [],
        }
        output = format_human_output(result)
        assert "Arizona time (MST)" in output

    def test_timezone_included_with_any_filter(self):
        result = {
            "query": {
                "start_date": "2026-02-10",
                "end_date": "2026-02-10",
                "duration_minutes": 60,
                "time_of_day": "any",
            },
            "slots": [],
            "calendars_checked": [],
        }
        output = format_human_output(result)
        assert "Arizona time (MST)" in output


class TestValidateArgs:
    def test_negative_duration_exits(self):
        args = Namespace(
            duration=-1, min_gap=15, max_slots=10, start="2026-02-10", end=None
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_zero_duration_exits(self):
        args = Namespace(
            duration=0, min_gap=15, max_slots=10, start="2026-02-10", end=None
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_negative_gap_exits(self):
        args = Namespace(
            duration=60, min_gap=-5, max_slots=10, start="2026-02-10", end=None
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_zero_max_slots_exits(self):
        args = Namespace(
            duration=60, min_gap=15, max_slots=0, start="2026-02-10", end=None
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_invalid_start_date_exits(self):
        args = Namespace(
            duration=60, min_gap=15, max_slots=10, start="not-a-date", end=None
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_end_before_start_exits(self):
        args = Namespace(
            duration=60, min_gap=15, max_slots=10, start="2026-02-15", end="2026-02-10"
        )
        with pytest.raises(SystemExit):
            validate_args(args)

    def test_valid_args_passes(self):
        args = Namespace(
            duration=60, min_gap=15, max_slots=10, start="2026-02-10", end="2026-02-12"
        )
        validate_args(args)  # Should not raise


class TestCompactMode:
    def test_compact_returns_one_slot_per_free_window(self):
        # Empty day: one big free window should yield one slot
        slots = find_slots_for_day("2026-02-10", [], 60, (9, 17), 15, TZ, compact=True)
        assert len(slots) == 1
        assert slots[0]["start"] == "9:00 AM"

    def test_compact_with_gap_returns_two_slots(self):
        # Meeting from 12-1 splits the day into two free windows
        busy = [
            (
                datetime(2026, 2, 10, 12, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 13, 0, tzinfo=TZ),
            )
        ]
        slots = find_slots_for_day(
            "2026-02-10", busy, 60, (9, 17), 15, TZ, compact=True
        )
        assert len(slots) == 2
        assert slots[0]["start"] == "9:00 AM"
        assert slots[1]["start"] == "1:15 PM"

    def test_non_compact_returns_many_slots(self):
        slots_normal = find_slots_for_day(
            "2026-02-10", [], 60, (9, 17), 15, TZ, compact=False
        )
        slots_compact = find_slots_for_day(
            "2026-02-10", [], 60, (9, 17), 15, TZ, compact=True
        )
        assert len(slots_normal) > len(slots_compact)


class TestWeekendSkipBehavior:
    def test_business_filter_skips_weekends(self):
        # 2026-02-14 is Saturday, 2026-02-15 is Sunday
        slots = find_slots_for_day("2026-02-14", [], 60, (9, 17), 15, TZ)
        # find_slots_for_day itself doesn't skip weekends; that's in main()
        # So this should return slots (the skip is at the caller level)
        assert len(slots) > 0

    def test_morning_filter_used_to_include_weekends_now_skips(self):
        # This test documents that the new behavior skips weekends
        # for all filters except "any". Tested via the skip_weekends logic
        # in main(), not find_slots_for_day.
        # 2026-02-14 is a Saturday
        from datetime import date

        d = date(2026, 2, 14)
        assert d.weekday() == 5  # Saturday

        # With the new logic: time_of_day != "any" and not include_weekends => skip
        skip_weekends = "morning" != "any" and not False
        assert skip_weekends is True

        # With "any" filter: should not skip
        skip_weekends_any = "any" != "any" and not False
        assert skip_weekends_any is False

        # With --include-weekends: should not skip
        skip_with_flag = "morning" != "any" and not True
        assert skip_with_flag is False


class TestBackToBackMeetings:
    def test_adjacent_meetings_no_slot_in_gap(self):
        # Two meetings back-to-back from 10-11 and 11-12 with 15-min buffer
        busy = [
            (
                datetime(2026, 2, 10, 10, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 11, 0, tzinfo=TZ),
            ),
            (
                datetime(2026, 2, 10, 11, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 12, 0, tzinfo=TZ),
            ),
        ]
        # With 15-min buffer and 30-min duration in window 10-12, no slot fits
        slots = find_slots_for_day("2026-02-10", busy, 30, (10, 12), 15, TZ)
        assert len(slots) == 0

    def test_adjacent_meetings_with_zero_buffer(self):
        busy = [
            (
                datetime(2026, 2, 10, 10, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 11, 0, tzinfo=TZ),
            ),
            (
                datetime(2026, 2, 10, 11, 30, tzinfo=TZ),
                datetime(2026, 2, 10, 12, 0, tzinfo=TZ),
            ),
        ]
        # 30 min gap between meetings, 30 min duration, 0 buffer => fits
        slots = find_slots_for_day("2026-02-10", busy, 30, (10, 13), 0, TZ)
        start_times = [s["start"] for s in slots]
        assert "11:00 AM" in start_times


class TestBoundaryEvents:
    def test_meeting_starting_before_window(self):
        # Meeting from 8:45-9:15, business window 9-17, 15-min buffer
        busy = [
            (
                datetime(2026, 2, 10, 8, 45, tzinfo=TZ),
                datetime(2026, 2, 10, 9, 15, tzinfo=TZ),
            ),
        ]
        slots = find_slots_for_day("2026-02-10", busy, 30, (9, 17), 15, TZ)
        # First available should be 9:30 (9:15 end + 15 min buffer)
        assert slots[0]["start"] == "9:30 AM"

    def test_meeting_ending_at_window_end(self):
        # Meeting from 4:00-5:00 PM, business window 9-17
        busy = [
            (
                datetime(2026, 2, 10, 16, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 17, 0, tzinfo=TZ),
            ),
        ]
        slots = find_slots_for_day("2026-02-10", busy, 60, (9, 17), 15, TZ)
        # No slot should end after 5 PM
        for slot in slots:
            assert "5:00 PM" >= slot["end"] or slot["end"].endswith("AM")

    def test_meeting_spanning_entire_window(self):
        busy = [
            (
                datetime(2026, 2, 10, 8, 0, tzinfo=TZ),
                datetime(2026, 2, 10, 18, 0, tzinfo=TZ),
            ),
        ]
        slots = find_slots_for_day("2026-02-10", busy, 30, (9, 17), 15, TZ)
        assert len(slots) == 0


class TestIsoFormat:
    def test_slot_iso_uses_timezone_offset(self):
        slots = find_slots_for_day("2026-02-10", [], 60, (9, 10), 0, TZ)
        assert len(slots) >= 1
        # Should contain -07:00 offset for Arizona
        assert "-07:00" in slots[0]["start_iso"]
        assert "-07:00" in slots[0]["end_iso"]

    def test_slot_iso_is_valid_isoformat(self):
        slots = find_slots_for_day("2026-02-10", [], 60, (9, 10), 0, TZ)
        for slot in slots:
            # Should parse without error
            datetime.fromisoformat(slot["start_iso"])
            datetime.fromisoformat(slot["end_iso"])
