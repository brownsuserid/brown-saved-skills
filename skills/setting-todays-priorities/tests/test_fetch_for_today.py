"""Tests for fetch_for_today.py — ensures For Today output includes description
and excludes archived tasks."""

import json
import os
import sys
from unittest.mock import patch, MagicMock

# Provide a dummy token so _config.py doesn't exit on import
os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "scripts",
            "setting-todays-priorities",
        )
    ),
)

# Shared Airtable config + executing-tasks helpers
SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")
TASK_EXEC_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts", "executing-tasks"
)
sys.path.insert(0, SHARED_DIR)
sys.path.insert(0, TASK_EXEC_DIR)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from fetch_for_today import fetch_for_today_tasks  # noqa: E402


def _make_airtable_response(records: list[dict]) -> bytes:
    return json.dumps({"records": records}).encode()


def _make_record(
    record_id: str = "rec123",
    task: str = "Test task",
    description: str = "Ship the feature",
    status: str = "Not Started",
    score: int = 80,
    notes: str = "Some context",
    due_date: str = "2026-03-01",
    for_today: bool = True,
    assignee_ids: list[str] | None = None,
) -> dict:
    """Build a fake Airtable record using personal base field names."""
    fields = {
        "Task": task,
        "Definition of Done": description,
        "Status": status,
        "Score": score,
        "Notes": notes,
        "Deadline": due_date,
        "For Today": for_today,
    }
    if assignee_ids is not None:
        fields["Assignee"] = assignee_ids
    return {"id": record_id, "fields": fields}


def _mock_urlopen_with_records(records_by_call: list[list[dict]]):
    """Create a side_effect function that returns different records per call.

    Each call to urlopen gets the next batch of records from the list.
    """
    responses = []
    for records in records_by_call:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response(records)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        responses.append(mock_resp)
    return responses


class TestFetchForTodayOutputFields:
    """fetch_for_today_tasks must include description and notes in output."""

    @patch("urllib.request.urlopen")
    def test_output_includes_description(self, mock_urlopen):
        # Arrange — 3 bases, only personal returns a record
        record = _make_record(description="All tests pass and PR merged")
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [
                [record],  # personal
                [],  # aitb
                [],  # bb
            ]
        )

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert len(results) == 1
        assert "description" in results[0]
        assert results[0]["description"] == "All tests pass and PR merged"

    @patch("urllib.request.urlopen")
    def test_output_includes_notes(self, mock_urlopen):
        # Arrange
        record = _make_record(notes="Blocked on Aaron to provide specs")
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [
                [record],
                [],
                [],
            ]
        )

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert results[0]["notes"] == "Blocked on Aaron to provide specs"

    @patch("urllib.request.urlopen")
    def test_output_includes_task_name(self, mock_urlopen):
        # Arrange
        record = _make_record(task="Review PR for auth module")
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [
                [record],
                [],
                [],
            ]
        )

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert results[0]["task"] == "Review PR for auth module"

    @patch("urllib.request.urlopen")
    def test_output_includes_airtable_url(self, mock_urlopen):
        # Arrange
        record = _make_record(record_id="recABC")
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [
                [record],
                [],
                [],
            ]
        )

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert "airtable_url" in results[0]
        assert "recABC" in results[0]["airtable_url"]

    @patch("urllib.request.urlopen")
    def test_empty_description_returns_empty_string(self, mock_urlopen):
        """Tasks without a Definition of Done should return '' not KeyError."""
        # Arrange
        record = {
            "id": "rec000",
            "fields": {
                "Task": "Quick task",
                "Status": "In Progress",
                "Score": 60,
                "For Today": True,
            },
        }
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [
                [record],
                [],
                [],
            ]
        )

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert results[0]["description"] == ""
        assert results[0]["notes"] == ""


class TestFetchForTodayFilterFormula:
    """The Airtable filter formula must exclude Archived status."""

    @patch("urllib.request.urlopen")
    def test_filter_formula_excludes_archived(self, mock_urlopen):
        """Verify the API request includes Archived in the exclusion filter."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        fetch_for_today_tasks(None, _test_config)

        # Assert — check each call's URL contains the Archived exclusion
        for call in mock_urlopen.call_args_list:
            url = call[0][0].full_url
            # URL-encoded {Status}!='Archived' appears as %7BStatus%7D%21%3D%27Archived%27
            assert "Archived" in url, f"API request missing Archived filter: {url}"

    @patch("urllib.request.urlopen")
    def test_filter_formula_excludes_completed(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        fetch_for_today_tasks(None, _test_config)

        for call in mock_urlopen.call_args_list:
            url = call[0][0].full_url
            assert "Completed" in url


class TestFetchForTodayProjectIds:
    """fetch_for_today_tasks must include project_ids in task output."""

    @patch("urllib.request.urlopen")
    def test_output_includes_project_ids(self, mock_urlopen):
        # Arrange
        record = {
            "id": "rec1",
            "fields": {
                "Task": "Task with project",
                "Status": "In Progress",
                "Score": 80,
                "For Today": True,
                "Project": ["recP1"],
            },
        }
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record], [], []])

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert results[0]["project_ids"] == ["recP1"]

    @patch("urllib.request.urlopen")
    def test_empty_project_ids_returns_empty_list(self, mock_urlopen):
        # Arrange
        record = {
            "id": "rec1",
            "fields": {
                "Task": "No project",
                "Status": "Not Started",
                "Score": 50,
                "For Today": True,
            },
        }
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record], [], []])

        # Act
        results = fetch_for_today_tasks(None, _test_config)

        # Assert
        assert results[0]["project_ids"] == []
