"""Tests for fetch_events.py logic functions."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_events import (
    deduplicate_events,
    fetch_google_events,
    get_all_events,
    load_config,
    resolve_config_path,
)

SAMPLE_CONFIG = {
    "timezone": "America/Phoenix",
    "google_calendars": [
        {"label": "BB", "account": "aaron@brainbridge.app", "calendar_id": "primary"},
        {
            "label": "Personal",
            "account": "aaroneden77@gmail.com",
            "calendar_id": "primary",
        },
    ],
    "apple_calendars": [],
}


class TestFetchGoogleEvents:
    def _mock_gog_response(self, events_list):
        """Create a mock subprocess result with gog JSON output."""
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = json.dumps({"events": events_list})
        mock.stderr = ""
        return mock

    @patch("fetch_events.subprocess.run")
    def test_fetches_from_all_calendars(self, mock_run):
        mock_run.return_value = self._mock_gog_response([])
        succeeded = []
        fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG, succeeded)
        assert mock_run.call_count == 2
        assert "aaron@brainbridge.app" in succeeded
        assert "aaroneden77@gmail.com" in succeeded

    @patch("fetch_events.subprocess.run")
    def test_skips_all_day_events(self, mock_run):
        mock_run.return_value = self._mock_gog_response(
            [
                {
                    "summary": "All Day",
                    "start": {"date": "2026-03-10"},
                    "end": {"date": "2026-03-11"},
                }
            ]
        )
        events = fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert len(events) == 0

    @patch("fetch_events.subprocess.run")
    def test_parses_timed_events(self, mock_run):
        mock_run.return_value = self._mock_gog_response(
            [
                {
                    "summary": "Standup",
                    "start": {"dateTime": "2026-03-10T10:00:00-07:00"},
                    "end": {"dateTime": "2026-03-10T10:30:00-07:00"},
                    "attendees": [],
                }
            ]
        )
        events = fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        # Two calendars, same mock response, so 2 events
        assert len(events) == 2
        assert events[0]["title"] == "Standup"
        assert events[0]["declined"] is False

    @patch("fetch_events.subprocess.run")
    def test_detects_declined_events(self, mock_run):
        mock_run.return_value = self._mock_gog_response(
            [
                {
                    "summary": "Declined Meeting",
                    "start": {"dateTime": "2026-03-10T14:00:00-07:00"},
                    "end": {"dateTime": "2026-03-10T15:00:00-07:00"},
                    "attendees": [{"self": True, "responseStatus": "declined"}],
                }
            ]
        )
        events = fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert events[0]["declined"] is True

    @patch("fetch_events.subprocess.run")
    def test_detects_tentative_events(self, mock_run):
        mock_run.return_value = self._mock_gog_response(
            [
                {
                    "summary": "Maybe",
                    "start": {"dateTime": "2026-03-10T14:00:00-07:00"},
                    "end": {"dateTime": "2026-03-10T15:00:00-07:00"},
                    "attendees": [{"self": True, "responseStatus": "tentative"}],
                }
            ]
        )
        events = fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert events[0]["tentative"] is True

    @patch("fetch_events.subprocess.run")
    def test_graceful_on_gog_failure(self, mock_run):
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "auth error"
        mock_run.return_value = mock_fail
        succeeded = []
        events = fetch_google_events(
            "2026-03-10", "2026-03-10", SAMPLE_CONFIG, succeeded
        )
        assert len(events) == 0
        assert len(succeeded) == 0

    @patch("fetch_events.subprocess.run")
    def test_graceful_on_invalid_json(self, mock_run):
        mock_bad = MagicMock()
        mock_bad.returncode = 0
        mock_bad.stdout = "not json"
        mock_bad.stderr = ""
        mock_run.return_value = mock_bad
        succeeded = []
        events = fetch_google_events(
            "2026-03-10", "2026-03-10", SAMPLE_CONFIG, succeeded
        )
        assert len(events) == 0
        assert len(succeeded) == 0

    @patch(
        "fetch_events.subprocess.run", side_effect=FileNotFoundError("gog not found")
    )
    def test_graceful_on_missing_gog(self, mock_run):
        events = fetch_google_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert len(events) == 0


class TestGetAllEvents:
    @patch("fetch_events.fetch_apple_events", return_value=[])
    @patch("fetch_events.fetch_google_events")
    def test_calendars_checked_tracks_successes(self, mock_google, mock_apple):
        def side_effect(start, end, config, succeeded=None):
            if succeeded is not None:
                succeeded.append("aaron@brainbridge.app")
            return [
                {
                    "title": "Meeting",
                    "source": "google:BB",
                    "calendar": "aaron@brainbridge.app",
                    "start_iso": "2026-03-10T10:00:00-07:00",
                    "end_iso": "2026-03-10T11:00:00-07:00",
                    "declined": False,
                    "tentative": False,
                }
            ]

        mock_google.side_effect = side_effect
        result = get_all_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert result["calendars_checked"] == ["aaron@brainbridge.app"]
        assert len(result["events"]) == 1

    @patch("fetch_events.fetch_apple_events", return_value=[])
    @patch("fetch_events.fetch_google_events", return_value=[])
    def test_empty_calendars_checked_when_all_fail(self, mock_google, mock_apple):
        result = get_all_events("2026-03-10", "2026-03-10", SAMPLE_CONFIG)
        assert result["calendars_checked"] == []


class TestDeduplicateEvents:
    def test_no_duplicates_returns_all(self):
        events = [
            {
                "title": "Meeting A",
                "source": "google:BB",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            },
            {
                "title": "Meeting B",
                "source": "apple:Intuit",
                "start_iso": "2026-02-10T14:00:00-07:00",
                "end_iso": "2026-02-10T15:00:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        assert len(result) == 2

    def test_duplicate_prefers_google_over_apple(self):
        events = [
            {
                "title": "Standup",
                "source": "apple:Intuit",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T10:30:00-07:00",
            },
            {
                "title": "Standup",
                "source": "google:BB",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T10:30:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        assert result[0]["source"] == "google:BB"

    def test_same_title_different_time_not_deduplicated(self):
        events = [
            {
                "title": "Standup",
                "source": "google:BB",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T10:30:00-07:00",
            },
            {
                "title": "Standup",
                "source": "google:BB",
                "start_iso": "2026-02-11T10:00:00-07:00",
                "end_iso": "2026-02-11T10:30:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        assert len(result) == 2

    def test_google_to_google_duplicate_keeps_first(self):
        events = [
            {
                "title": "Cross-cal",
                "source": "google:BB",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            },
            {
                "title": "Cross-cal",
                "source": "google:AITB",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        assert result[0]["source"] == "google:BB"

    def test_no_source_collision_between_google_and_apple_family(self):
        """The old code had a bug where google 'Family' label collided
        with apple 'Family' source. With prefixed sources this is fixed."""
        events = [
            {
                "title": "Dinner",
                "source": "google:Family",
                "start_iso": "2026-02-10T18:00:00-07:00",
                "end_iso": "2026-02-10T19:00:00-07:00",
            },
            {
                "title": "Different Dinner",
                "source": "apple:Family",
                "start_iso": "2026-02-10T18:00:00-07:00",
                "end_iso": "2026-02-10T19:00:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        # Different titles, should not be deduplicated
        assert len(result) == 2

    def test_empty_events_returns_empty(self):
        assert deduplicate_events([]) == []

    def test_start_time_normalized_to_minute(self):
        """Events with same title and same minute but different seconds
        should be deduplicated."""
        events = [
            {
                "title": "Meeting",
                "source": "apple:Intuit",
                "start_iso": "2026-02-10T10:00:00-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            },
            {
                "title": "Meeting",
                "source": "google:BB",
                "start_iso": "2026-02-10T10:00:30-07:00",
                "end_iso": "2026-02-10T11:00:00-07:00",
            },
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        assert result[0]["source"] == "google:BB"


class TestResolveConfigPath:
    def test_cli_flag_takes_priority(self):
        with patch.dict("os.environ", {"OPENCLAW_CALENDAR_CONFIG": "/env/config.yaml"}):
            result = resolve_config_path("/cli/config.yaml")
            assert result == Path("/cli/config.yaml")

    def test_env_var_used_when_no_cli(self):
        with patch.dict("os.environ", {"OPENCLAW_CALENDAR_CONFIG": "/env/config.yaml"}):
            result = resolve_config_path(None)
            assert result == Path("/env/config.yaml")

    def test_default_when_no_cli_or_env(self):
        with patch.dict("os.environ", {}, clear=True):
            result = resolve_config_path(None)
            assert result.name == "config.yaml"
            assert "finding-calendar-availability" in str(result)


class TestLoadConfig:
    def test_loads_from_explicit_path(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("timezone: America/New_York\ngoogle_calendars: []\n")
        result = load_config(str(config_file))
        assert result["timezone"] == "America/New_York"

    def test_loads_from_env_var(self, tmp_path):
        config_file = tmp_path / "env.yaml"
        config_file.write_text("timezone: Europe/London\ngoogle_calendars: []\n")
        with patch.dict("os.environ", {"OPENCLAW_CALENDAR_CONFIG": str(config_file)}):
            result = load_config()
            assert result["timezone"] == "Europe/London"

    def test_exits_on_missing_file(self):
        import pytest

        with pytest.raises(SystemExit):
            load_config("/nonexistent/config.yaml")
