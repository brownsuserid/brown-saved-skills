"""Tests for parse_recurrence.py."""

import os
import sys
from datetime import date
from unittest.mock import patch


sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "regenerating-recurring-tasks"
    ),
)

from parse_recurrence import parse_recurrence, add_months, next_weekday


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FROZEN_DATE = date(2026, 3, 9)  # A Sunday


def _freeze(mock_date, d=FROZEN_DATE):
    mock_date.today.return_value = d
    mock_date.side_effect = lambda *args, **kw: date(*args, **kw)


# ---------------------------------------------------------------------------
# TestAddMonths
# ---------------------------------------------------------------------------


class TestAddMonths:
    def test_add_one_month(self):
        assert add_months(date(2026, 1, 15), 1) == date(2026, 2, 15)

    def test_add_months_clamps_day(self):
        # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year)
        assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)

    def test_add_twelve_months(self):
        assert add_months(date(2026, 3, 9), 12) == date(2027, 3, 9)


# ---------------------------------------------------------------------------
# TestNextWeekday
# ---------------------------------------------------------------------------


class TestNextWeekday:
    def test_next_monday_from_sunday(self):
        sunday = date(2026, 3, 8)  # Sunday
        assert sunday.weekday() == 6
        result = next_weekday(sunday, 0)  # Monday
        assert result == date(2026, 3, 9)

    def test_next_friday_from_friday(self):
        friday = date(2026, 3, 13)
        assert friday.weekday() == 4
        result = next_weekday(friday, 4)  # Friday
        # Should be 7 days later, not same day
        assert result == date(2026, 3, 20)


# ---------------------------------------------------------------------------
# TestCanonicalPatterns
# ---------------------------------------------------------------------------


class TestCanonicalPatterns:
    @patch("parse_recurrence.date")
    def test_daily(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("daily")
        assert result["next_date"] == "2026-03-10"

    @patch("parse_recurrence.date")
    def test_weekly(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("weekly")
        assert result["next_date"] == "2026-03-16"

    @patch("parse_recurrence.date")
    def test_biweekly(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("bi-weekly")
        assert result["next_date"] == "2026-03-23"

    @patch("parse_recurrence.date")
    def test_monthly(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("monthly")
        assert result["next_date"] == "2026-04-09"
        assert result["canonical"] == "Monthly"

    @patch("parse_recurrence.date")
    def test_quarterly(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("quarterly")
        assert result["next_date"] == "2026-06-09"
        assert result["canonical"] == "Quarterly"

    @patch("parse_recurrence.date")
    def test_annually(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("annually")
        assert result["next_date"] == "2027-03-09"
        assert result["canonical"] == "Annually"


# ---------------------------------------------------------------------------
# TestNaturalLanguage
# ---------------------------------------------------------------------------


class TestNaturalLanguage:
    @patch("parse_recurrence.date")
    def test_every_day(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("every day")
        assert result["next_date"] == "2026-03-10"
        assert result["canonical"] == "Daily"

    @patch("parse_recurrence.date")
    def test_every_week(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("every week")
        assert result["next_date"] == "2026-03-16"
        assert result["canonical"] == "Weekly"

    @patch("parse_recurrence.date")
    def test_every_month(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("every month")
        assert result["next_date"] == "2026-04-09"
        assert result["canonical"] == "Monthly"

    @patch("parse_recurrence.date")
    def test_every_3_months(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("every 3 months")
        assert result["next_date"] == "2026-06-09"

    @patch("parse_recurrence.date")
    def test_every_friday(self, mock_date):
        _freeze(mock_date)
        # Sunday 2026-03-09 -> next Friday is 2026-03-13
        result = parse_recurrence("every friday")
        assert result["next_date"] == "2026-03-13"
        assert result["canonical"] == "Weekly"

    @patch("parse_recurrence.date")
    def test_every_other_tuesday(self, mock_date):
        _freeze(mock_date)
        # Sunday 2026-03-09 -> next Tuesday is 2026-03-10, + 1 week = 2026-03-17
        result = parse_recurrence("every other tuesday")
        assert result["next_date"] == "2026-03-17"


# ---------------------------------------------------------------------------
# TestFrequency
# ---------------------------------------------------------------------------


class TestFrequency:
    @patch("parse_recurrence.date")
    def test_4x_weekly(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("4x weekly")
        # 7 // 4 = 1 day interval
        assert result["next_date"] == "2026-03-10"

    @patch("parse_recurrence.date")
    def test_twice_a_week(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("twice a week")
        # 3 day interval
        assert result["next_date"] == "2026-03-12"

    @patch("parse_recurrence.date")
    def test_twice_a_month(self, mock_date):
        _freeze(mock_date)
        result = parse_recurrence("twice a month")
        # 15 day interval
        assert result["next_date"] == "2026-03-24"


# ---------------------------------------------------------------------------
# TestPlaceholders
# ---------------------------------------------------------------------------


class TestPlaceholders:
    def test_empty_string_skips(self):
        result = parse_recurrence("")
        assert result["skip"] is True
        assert "reason" in result

    def test_none_skips(self):
        result = parse_recurrence("none")
        assert result["skip"] is True

    def test_placeholder_text_skips(self):
        result = parse_recurrence(
            "a description of when you would like the task to repeat"
        )
        assert result["skip"] is True


# ---------------------------------------------------------------------------
# TestUnparseable
# ---------------------------------------------------------------------------


class TestUnparseable:
    def test_garbage_returns_error(self):
        result = parse_recurrence("florbglorp every zazzle")
        assert "error" in result

    def test_error_includes_original_text(self):
        text = "whenever the moon is full"
        result = parse_recurrence(text)
        assert "error" in result
        assert text in result["error"]
