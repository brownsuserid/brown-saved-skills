"""Tests for update_spreadsheet.py — spreadsheet update and status management."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "managing-outreach"),
)

import update_spreadsheet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path):
    config = {
        "spreadsheet": {
            "id": "sheet-id",
            "developersTab": "Developers",
            "columns": "A:F",
            "account": "test@example.com",
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    return config, str(config_path)


# ---------------------------------------------------------------------------
# TestStatusPriority
# ---------------------------------------------------------------------------


class TestRunGog:
    """run_gog() wraps gog CLI calls."""

    @patch("subprocess.run")
    def test_returns_stdout_on_success(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(
            returncode=0, stdout="result output", stderr=""
        )

        # Act
        result = update_spreadsheet.run_gog(["sheets", "get", "id", "range"])

        # Assert
        assert result == "result output"

    @patch("subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        # Act
        result = update_spreadsheet.run_gog(["sheets", "get", "id", "range"])

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# TestFindRowByName
# ---------------------------------------------------------------------------


class TestFindRowByName:
    """find_row_by_name() matches contacts case-insensitively."""

    def test_exact_match(self):
        # Arrange
        rows = [{"Name": "Alice Smith", "Status": "Invited"}]

        # Act
        row_num, row = update_spreadsheet.find_row_by_name(rows, "Alice Smith")

        # Assert
        assert row_num == 2  # 1-based + header row
        assert row["Name"] == "Alice Smith"

    def test_case_insensitive(self):
        # Arrange
        rows = [{"Name": "BOB JONES", "Status": "Invited"}]

        # Act
        row_num, row = update_spreadsheet.find_row_by_name(rows, "bob jones")

        # Assert
        assert row_num is not None

    def test_not_found(self):
        # Arrange
        rows = [{"Name": "Alice", "Status": "Invited"}]

        # Act
        row_num, row = update_spreadsheet.find_row_by_name(rows, "Nobody")

        # Assert
        assert row_num is None
        assert row is None


# ---------------------------------------------------------------------------
# TestStateFileIO
# ---------------------------------------------------------------------------


class TestStateFileIO:
    """load_state/save_state handle the outreach state file."""

    def test_save_and_load(self, tmp_path):
        # Arrange
        state_file = str(tmp_path / "outreach-state.json")
        original_state_file = update_spreadsheet.STATE_FILE
        update_spreadsheet.STATE_FILE = state_file

        try:
            state = {"lastRun": "2026-02-16T00:00:00Z", "contactsProcessed": 5}

            # Act
            update_spreadsheet.save_state(state)
            loaded = update_spreadsheet.load_state()

            # Assert
            assert loaded["lastRun"] == "2026-02-16T00:00:00Z"
            assert loaded["contactsProcessed"] == 5
        finally:
            update_spreadsheet.STATE_FILE = original_state_file

    def test_load_missing_file(self, tmp_path):
        # Arrange
        original_state_file = update_spreadsheet.STATE_FILE
        update_spreadsheet.STATE_FILE = str(tmp_path / "nonexistent.json")

        try:
            # Act
            result = update_spreadsheet.load_state()

            # Assert
            assert result == {}
        finally:
            update_spreadsheet.STATE_FILE = original_state_file


# ---------------------------------------------------------------------------
# TestCheckAirtableTickets
# ---------------------------------------------------------------------------


class TestCheckAirtableTickets:
    """check_airtable_tickets() queries Airtable for ticket holders."""

    def test_no_token_returns_empty(self, monkeypatch):
        # Arrange
        monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
        config = {
            "airtable": {"base_id": "app1", "table": "Tickets", "event_filter": "Test"}
        }

        # Act
        result = update_spreadsheet.check_airtable_tickets(config)

        # Assert
        assert result == set()

    def test_no_airtable_config_returns_empty(self):
        # Act
        result = update_spreadsheet.check_airtable_tickets({})

        # Assert
        assert result == set()

    @patch("urllib.request.urlopen")
    def test_returns_attendee_names(self, mock_urlopen):
        # Arrange
        body = json.dumps(
            {
                "records": [
                    {"fields": {"Name": "Alice"}},
                    {"fields": {"Name": "Bob"}},
                ]
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = {
            "airtable": {"base_id": "app1", "table": "Tickets", "event_filter": "Test"}
        }

        # Act
        result = update_spreadsheet.check_airtable_tickets(config)

        # Assert
        assert "alice" in result
        assert "bob" in result
