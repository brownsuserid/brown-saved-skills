"""Tests for gather_calendar.py — calendar analysis: conflict detection, buffer
warnings, free windows, and stats."""

import sys
import os


sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "scripts",
        "generating-morning-briefing",
    ),
)

import gather_calendar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    title="Meeting",
    source="BB",
    start="2026-02-16T09:00:00",
    end="2026-02-16T10:00:00",
    link=None,
):
    return {
        "title": title,
        "source": source,
        "calendar": "test@example.com",
        "link": link,
        "start_iso": start,
        "end_iso": end,
        "time": gather_calendar._format_time(start),
        "end_time": gather_calendar._format_time(end),
    }


# ---------------------------------------------------------------------------
# TestFormatTime
# ---------------------------------------------------------------------------


class TestFormatTime:
    """_format_time() converts ISO datetime to 12-hour string."""

    def test_morning_time(self):
        assert gather_calendar._format_time("2026-02-16T09:30:00") == "9:30 AM"

    def test_afternoon_time(self):
        assert gather_calendar._format_time("2026-02-16T14:00:00") == "2:00 PM"

    def test_with_timezone_offset(self):
        result = gather_calendar._format_time("2026-02-16T09:00:00-07:00")
        assert result == "9:00 AM"

    def test_empty_string(self):
        assert gather_calendar._format_time("") == ""


# ---------------------------------------------------------------------------
# TestEnrichEvents
# ---------------------------------------------------------------------------


class TestEnrichEvents:
    """enrich_events() adds time/end_time fields to events."""

    def test_adds_formatted_times(self):
        events = [
            {
                "title": "Standup",
                "source": "google:BB",
                "calendar": "test@example.com",
                "link": "https://calendar.google.com/event/1",
                "start_iso": "2026-02-16T09:00:00",
                "end_iso": "2026-02-16T09:30:00",
            }
        ]
        result = gather_calendar.enrich_events(events)
        assert len(result) == 1
        assert result[0]["time"] == "9:00 AM"
        assert result[0]["end_time"] == "9:30 AM"

    def test_empty_list(self):
        assert gather_calendar.enrich_events([]) == []

    def test_preserves_existing_fields(self):
        events = [
            {
                "title": "Test",
                "source": "google:BB",
                "calendar": "x",
                "link": None,
                "start_iso": "2026-02-16T14:00:00",
                "end_iso": "2026-02-16T15:00:00",
                "in_person": True,
            }
        ]
        result = gather_calendar.enrich_events(events)
        assert result[0]["in_person"] is True
        assert result[0]["title"] == "Test"


# ---------------------------------------------------------------------------
# TestFilterBufferEvents
# ---------------------------------------------------------------------------


class TestFilterBufferEvents:
    """filter_buffer_events() removes events with 'buffer' in the title."""

    def test_keeps_non_buffer_events(self):
        events = [
            _make_event(title="Standup", source="BB"),
            _make_event(title="1:1 with Dan", source="AITB"),
        ]
        result = gather_calendar.filter_buffer_events(events)
        assert len(result) == 2

    def test_removes_buffer_events(self):
        events = [
            _make_event(title="Meeting Buffer", source="BB"),
            _make_event(title="Real Meeting", source="BB"),
        ]
        result = gather_calendar.filter_buffer_events(events)
        assert len(result) == 1
        assert result[0]["title"] == "Real Meeting"

    def test_case_insensitive(self):
        events = [
            _make_event(title="BUFFER time"),
            _make_event(title="buffer"),
            _make_event(title="Actual event"),
        ]
        result = gather_calendar.filter_buffer_events(events)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestDetectConflicts
# ---------------------------------------------------------------------------


class TestDetectConflicts:
    """detect_conflicts() finds overlapping events."""

    def test_no_conflicts(self):
        # Arrange
        events = [
            _make_event(start="2026-02-16T09:00:00", end="2026-02-16T10:00:00"),
            _make_event(start="2026-02-16T10:00:00", end="2026-02-16T11:00:00"),
        ]

        # Act
        conflicts = gather_calendar.detect_conflicts(events)

        # Assert
        assert conflicts == []

    def test_overlapping_events(self):
        # Arrange
        events = [
            _make_event(
                title="A", start="2026-02-16T09:00:00", end="2026-02-16T10:30:00"
            ),
            _make_event(
                title="B", start="2026-02-16T10:00:00", end="2026-02-16T11:00:00"
            ),
        ]

        # Act
        conflicts = gather_calendar.detect_conflicts(events)

        # Assert
        assert len(conflicts) == 1
        assert conflicts[0]["overlap_minutes"] == 30

    def test_empty_events(self):
        assert gather_calendar.detect_conflicts([]) == []


# ---------------------------------------------------------------------------
# TestDetectNoBuffer
# ---------------------------------------------------------------------------


class TestDetectNoBuffer:
    """detect_no_buffer() finds consecutive events with insufficient gap."""

    def test_back_to_back_events(self):
        # Arrange
        events = [
            _make_event(start="2026-02-16T09:00:00", end="2026-02-16T10:00:00"),
            _make_event(start="2026-02-16T10:00:00", end="2026-02-16T11:00:00"),
        ]

        # Act
        result = gather_calendar.detect_no_buffer(events, min_gap_minutes=15)

        # Assert
        assert len(result) == 1
        assert result[0]["gap_minutes"] == 0

    def test_sufficient_buffer(self):
        # Arrange
        events = [
            _make_event(start="2026-02-16T09:00:00", end="2026-02-16T10:00:00"),
            _make_event(start="2026-02-16T10:30:00", end="2026-02-16T11:00:00"),
        ]

        # Act
        result = gather_calendar.detect_no_buffer(events, min_gap_minutes=15)

        # Assert
        assert result == []

    def test_custom_min_gap(self):
        # Arrange — 10 min gap, but min_gap is 5
        events = [
            _make_event(start="2026-02-16T09:00:00", end="2026-02-16T10:00:00"),
            _make_event(start="2026-02-16T10:10:00", end="2026-02-16T11:00:00"),
        ]

        # Act
        result = gather_calendar.detect_no_buffer(events, min_gap_minutes=5)

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# TestCalculateStats
# ---------------------------------------------------------------------------


class TestCalculateStats:
    """calculate_stats() computes meeting hours and summary."""

    def test_total_meeting_hours(self):
        # Arrange
        events = [
            _make_event(start="2026-02-16T09:00:00", end="2026-02-16T10:00:00"),
            _make_event(start="2026-02-16T14:00:00", end="2026-02-16T15:30:00"),
        ]

        # Act
        stats = gather_calendar.calculate_stats(events, [], [], "2026-02-16")

        # Assert
        assert stats["total_events"] == 2
        assert stats["meeting_hours"] == 2.5
