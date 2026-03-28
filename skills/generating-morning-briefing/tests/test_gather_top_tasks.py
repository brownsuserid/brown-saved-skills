"""Tests for gather_top_tasks.py — ensures top tasks exclude blocked tasks
and only include tasks assigned to the specified person."""

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
            "generating-morning-briefing",
        )
    ),
)
SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")
TASK_EXEC_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts", "executing-tasks"
)
sys.path.insert(0, SHARED_DIR)
sys.path.insert(0, TASK_EXEC_DIR)

import airtable_config  # noqa: E402
import gather_top_tasks  # noqa: E402

_test_config = airtable_config.load_config(
    os.path.join(SHARED_DIR, "configs", "all.yaml")
)
gather_top_tasks._config = _test_config

from gather_top_tasks import (  # noqa: E402
    fetch_top_tasks,
    fetch_all_blocked,
    fetch_all_human_review,
    fetch_blocked_for_assignee,
    filter_blocked_on_person,
    merge_and_deduplicate,
)


AARON_PERSONAL_ID = "recqfhZKB6O5C3No1"


def _make_airtable_response(records: list[dict]) -> bytes:
    return json.dumps({"records": records}).encode()


def _make_record(
    record_id: str = "rec123",
    task: str = "Test task",
    status: str = "In Progress",
    score: int = 80,
    assignee_ids: list[str] | None = None,
) -> dict:
    """Build a fake Airtable record using personal base field names."""
    fields: dict = {
        "Task": task,
        "Definition of Done": "",
        "Status": status,
        "Score": score,
        "Notes": "",
        "Deadline": "",
    }
    if assignee_ids is not None:
        fields["Assignee"] = assignee_ids
    return {"id": record_id, "fields": fields}


def _mock_urlopen_with_records(records_by_call: list[list[dict]]):
    """Create mock responses — one per Airtable API call (one per base)."""
    responses = []
    for records in records_by_call:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response(records)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        responses.append(mock_resp)
    return responses


PABLO_PERSONAL_ID = "recVET2m8HSdXH15s"


class TestFetchTopTasksAssigneeFiltering:
    """fetch_top_tasks must only return tasks assigned to the specified person."""

    @patch("urllib.request.urlopen")
    def test_excludes_tasks_assigned_to_others(self, mock_urlopen):
        """Tasks assigned to someone else should not appear in results."""
        # Arrange — mix of Aaron's and Pablo's tasks
        records = [
            _make_record("rec1", "Aaron task", "In Progress", 90, [AARON_PERSONAL_ID]),
            _make_record("rec2", "Pablo task", "In Progress", 95, [PABLO_PERSONAL_ID]),
            _make_record("rec3", "Unassigned task", "In Progress", 85),
        ]
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [records, [], []]  # personal, aitb, bb
        )

        # Act
        results = fetch_top_tasks("aaron", 10, _test_config)

        # Assert — only Aaron's task should appear
        assert len(results) == 1
        assert results[0]["task"] == "Aaron task"


class TestFetchTopTasksExcludesBlocked:
    """fetch_top_tasks must NOT return tasks with Blocked status."""

    @patch("urllib.request.urlopen")
    def test_blocked_tasks_excluded_from_results(self, mock_urlopen):
        """Blocked tasks should never appear in top_tasks even if they have scores."""
        # Arrange — personal base returns a mix of in-progress and blocked tasks
        records = [
            _make_record(
                "rec1", "High score task", "In Progress", 90, [AARON_PERSONAL_ID]
            ),
            _make_record("rec2", "Blocked task", "Blocked", 85, [AARON_PERSONAL_ID]),
            _make_record(
                "rec3", "Another active", "In Progress", 70, [AARON_PERSONAL_ID]
            ),
        ]
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [records, [], []]  # personal, aitb, bb
        )

        # Act
        results = fetch_top_tasks("aaron", 10, _test_config)

        # Assert — blocked task should not be in results
        statuses = [t["status"] for t in results]
        assert "Blocked" not in statuses
        assert len(results) == 2

    @patch("urllib.request.urlopen")
    def test_api_filter_excludes_blocked_status(self, mock_urlopen):
        """The Airtable API request should include Blocked in the exclusion filter."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        fetch_top_tasks("aaron", 10, _test_config)

        # Assert — every API call should exclude Blocked in the filter formula
        for call in mock_urlopen.call_args_list:
            url = call[0][0].full_url
            assert "Blocked" in url, (
                f"API request missing Blocked exclusion filter: {url}"
            )

    @patch("urllib.request.urlopen")
    def test_only_returns_actionable_statuses(self, mock_urlopen):
        """Top tasks should only contain Not Started or In Progress tasks."""
        records = [
            _make_record("rec1", "Active task", "In Progress", 90, [AARON_PERSONAL_ID]),
            _make_record("rec2", "Blocked task", "Blocked", 85, [AARON_PERSONAL_ID]),
            _make_record("rec3", "New task", "Not Started", 75, [AARON_PERSONAL_ID]),
        ]
        mock_urlopen.side_effect = _mock_urlopen_with_records([records, [], []])

        # Act
        results = fetch_top_tasks("aaron", 10, _test_config)

        # Assert
        allowed_statuses = {"In Progress", "Not Started"}
        for task in results:
            assert task["status"] in allowed_statuses, (
                f"Task '{task['task']}' has non-actionable status: {task['status']}"
            )


class TestFetchAllBlocked:
    """fetch_all_blocked(_test_config) returns all blocked tasks across bases."""

    @patch("urllib.request.urlopen")
    def test_returns_blocked_tasks_from_all_bases(self, mock_urlopen):
        # Arrange
        blocked_task = _make_record("rec1", "Blocked task", "Blocked", 80)
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [[blocked_task], [], []]  # personal, aitb, bb
        )

        # Act
        results = fetch_all_blocked(_test_config)

        # Assert
        assert len(results) == 1
        assert results[0]["status"] == "Blocked"


class TestFetchAllHumanReview:
    """fetch_all_human_review(_test_config) returns tasks needing human review."""

    @patch("urllib.request.urlopen")
    def test_returns_human_review_tasks(self, mock_urlopen):
        # Arrange
        review_task = _make_record("rec1", "Review this", "Human Review", 75)
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [[review_task], [], []]  # personal, aitb, bb
        )

        # Act
        results = fetch_all_human_review(_test_config)

        # Assert
        assert len(results) == 1
        assert results[0]["task"] == "Review this"


class TestFetchBlockedForAssignee:
    """fetch_blocked_for_assignee() returns blocked tasks for a specific person."""

    @patch("urllib.request.urlopen")
    def test_returns_blocked_for_pablo(self, mock_urlopen):
        # Arrange
        pablo_blocked = _make_record(
            "rec1", "Pablo blocked", "Blocked", 70, [PABLO_PERSONAL_ID]
        )
        aaron_blocked = _make_record(
            "rec2", "Aaron blocked", "Blocked", 65, [AARON_PERSONAL_ID]
        )
        mock_urlopen.side_effect = _mock_urlopen_with_records(
            [[pablo_blocked, aaron_blocked], [], []]
        )

        # Act
        results = fetch_blocked_for_assignee("pablo", _test_config)

        # Assert
        assert len(results) == 1
        assert results[0]["task"] == "Pablo blocked"


class TestFilterBlockedOnPerson:
    """filter_blocked_on_person() filters tasks mentioning a person in notes."""

    def test_filters_by_name_in_notes(self):
        # Arrange
        tasks = [
            {
                "id": "rec1",
                "task": "Waiting on Aaron",
                "notes": "Blocked on Aaron for review",
            },
            {
                "id": "rec2",
                "task": "Waiting on Dan",
                "notes": "Blocked on Dan for approval",
            },
            {"id": "rec3", "task": "No notes", "notes": ""},
        ]

        # Act
        results = filter_blocked_on_person(tasks, "aaron")

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "rec1"

    def test_case_insensitive_match(self):
        # Arrange
        tasks = [
            {"id": "rec1", "notes": "Waiting on AARON"},
            {"id": "rec2", "notes": "aaron needs to review"},
        ]

        # Act
        results = filter_blocked_on_person(tasks, "Aaron")

        # Assert
        assert len(results) == 2

    def test_word_boundary_match(self):
        # Arrange
        tasks = [
            {"id": "rec1", "notes": "Blocked on Aaron"},  # Full word match
            {"id": "rec2", "notes": "Aaronson helped"},  # Not a match (substring)
        ]

        # Act
        results = filter_blocked_on_person(tasks, "aaron")

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "rec1"


class TestMergeAndDeduplicate:
    """merge_and_deduplicate() merges lists without duplicates."""

    def test_removes_duplicates_by_id(self):
        # Arrange
        list1 = [{"id": "rec1", "score": 90}, {"id": "rec2", "score": 80}]
        list2 = [{"id": "rec2", "score": 80}, {"id": "rec3", "score": 70}]

        # Act
        results = merge_and_deduplicate(list1, list2)

        # Assert
        assert len(results) == 3
        ids = [t["id"] for t in results]
        assert ids == ["rec1", "rec2", "rec3"]

    def test_sorts_by_score_descending(self):
        # Arrange
        list1 = [{"id": "rec1", "score": 50}]
        list2 = [{"id": "rec2", "score": 90}]
        list3 = [{"id": "rec3", "score": 70}]

        # Act
        results = merge_and_deduplicate(list1, list2, list3)

        # Assert
        scores = [t["score"] for t in results]
        assert scores == [90, 70, 50]

    def test_handles_empty_lists(self):
        # Act
        results = merge_and_deduplicate([], [], [])

        # Assert
        assert results == []

    def test_handles_missing_score(self):
        # Arrange
        list1 = [{"id": "rec1"}]  # No score
        list2 = [{"id": "rec2", "score": 80}]

        # Act
        results = merge_and_deduplicate(list1, list2)

        # Assert
        assert len(results) == 2
        # rec2 should come first (has score 80, rec1 defaults to 0)
        assert results[0]["id"] == "rec2"


class TestTaskOutputIncludesProjectIds:
    """Tasks returned by fetch functions must include project_ids."""

    @patch("urllib.request.urlopen")
    def test_top_tasks_include_project_ids(self, mock_urlopen):
        # Arrange
        records = [
            {
                "id": "rec1",
                "fields": {
                    "Task": "Task with project",
                    "Status": "In Progress",
                    "Score": 90,
                    "Assignee": [AARON_PERSONAL_ID],
                    "Project": ["recP1"],
                },
            }
        ]
        mock_urlopen.side_effect = _mock_urlopen_with_records([records, [], []])

        # Act
        results = fetch_top_tasks("aaron", 10, _test_config)

        # Assert
        assert results[0]["project_ids"] == ["recP1"]

    @patch("urllib.request.urlopen")
    def test_blocked_tasks_include_project_ids(self, mock_urlopen):
        # Arrange
        records = [
            {
                "id": "rec1",
                "fields": {
                    "Task": "Blocked task",
                    "Status": "Blocked",
                    "Score": 80,
                    "Project": ["recP2"],
                },
            }
        ]
        mock_urlopen.side_effect = _mock_urlopen_with_records([records, [], []])

        # Act
        results = fetch_all_blocked(_test_config)

        # Assert
        assert results[0]["project_ids"] == ["recP2"]
