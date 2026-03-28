"""Tests for gather_for_today_tasks.py — For Today task aggregation."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

import airtable_config  # noqa: E402
import gather_for_today_tasks  # noqa: E402

_test_config = airtable_config.load_config(None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_urlopen_with_records(records):
    body = json.dumps({"records": records}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


def _make_task_record(
    task_id="recT1", name="Do thing", score=50, status="In Progress", assignee_ids=None
):
    return {
        "id": task_id,
        "fields": {
            "Task": name,
            "Score": score,
            "Status": status,
            "For Today": True,
            "Assignee": assignee_ids or [],
        },
    }


# ---------------------------------------------------------------------------
# TestResolveAssigneeId
# ---------------------------------------------------------------------------


class TestResolveAssigneeId:
    """resolve_assignee_id() maps names to base-specific record IDs."""

    def test_aaron_personal(self):
        result = gather_for_today_tasks.resolve_assignee_id(
            "aaron", "personal", airtable_config.get_people(_test_config)
        )
        assert result is not None
        assert result.startswith("rec")

    def test_unknown_name(self):
        result = gather_for_today_tasks.resolve_assignee_id(
            "nobody", "personal", airtable_config.get_people(_test_config)
        )
        assert result is None

    def test_aaron_bb(self):
        result = gather_for_today_tasks.resolve_assignee_id(
            "aaron", "bb", airtable_config.get_people(_test_config)
        )
        assert result is not None


# ---------------------------------------------------------------------------
# TestFetchForTodayTasks
# ---------------------------------------------------------------------------


class TestFetchForTodayTasks:
    """fetch_for_today_tasks() queries Airtable for For Today tasks."""

    @patch("gather_for_today_tasks.make_request")
    def test_returns_tasks(self, mock_request):
        # Arrange
        mock_request.return_value = {
            "records": [
                _make_task_record(score=80),
                _make_task_record(task_id="recT2", score=60),
            ]
        }

        # Act
        result = gather_for_today_tasks.fetch_for_today_tasks(
            "personal", "test-token", _test_config
        )

        # Assert
        assert len(result) == 2
        assert result[0]["task"] == "Do thing"
        assert result[0]["score"] == 80

    @patch("gather_for_today_tasks.make_request")
    def test_assignee_filter(self, mock_request):
        # Arrange
        aaron_id = gather_for_today_tasks.resolve_assignee_id(
            "aaron", "personal", airtable_config.get_people(_test_config)
        )
        mock_request.return_value = {
            "records": [
                _make_task_record(task_id="recT1", assignee_ids=[aaron_id]),
                _make_task_record(task_id="recT2", assignee_ids=["recOther"]),
            ]
        }

        # Act
        result = gather_for_today_tasks.fetch_for_today_tasks(
            "personal", "test-token", _test_config, assignee="aaron"
        )

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "recT1"

    @patch("gather_for_today_tasks.make_request")
    def test_no_assignee_filter_returns_all(self, mock_request):
        # Arrange
        mock_request.return_value = {
            "records": [
                _make_task_record(task_id="recT1"),
                _make_task_record(task_id="recT2"),
            ]
        }

        # Act
        result = gather_for_today_tasks.fetch_for_today_tasks(
            "personal", "test-token", _test_config, assignee=None
        )

        # Assert
        assert len(result) == 2

    @patch("gather_for_today_tasks.make_request")
    def test_includes_airtable_url(self, mock_request):
        # Arrange
        mock_request.return_value = {"records": [_make_task_record()]}

        # Act
        result = gather_for_today_tasks.fetch_for_today_tasks(
            "personal", "test-token", _test_config
        )

        # Assert
        assert "airtable_url" in result[0]
        assert "airtable.com" in result[0]["airtable_url"]

    @patch("gather_for_today_tasks.make_request")
    def test_empty_results(self, mock_request):
        # Arrange
        mock_request.return_value = {"records": []}

        # Act
        result = gather_for_today_tasks.fetch_for_today_tasks(
            "bb", "test-token", _test_config
        )

        # Assert
        assert result == []
