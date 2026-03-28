"""Tests for get_task.py -- single task fetch with link resolution."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "executing-tasks"),
)
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import get_base, load_config

import get_task

# Load config once for all tests
_config = load_config()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_record(task_id="recT1", name="Test Task", project_ids=None, **extra):
    fields = {
        "Task": name,
        "Status": "In Progress",
        "Definition of Done": "Ship it",
        "Notes": "Some notes",
        "Deadline": "2026-03-01",
        "Score": 80,
        "Assignee": ["recA1"],
        "Project": project_ids or [],
        **extra,
    }
    return {"id": task_id, "fields": fields}


def _make_project_record(
    project_id="recP1", name="My Project", goals=None, mountains=None
):
    fields = {
        "Project": name,
        "Status": "Active",
        "Definition of Done": "Project desc",
        "1yr Goals": goals or [],
        "Mountains (30d)": mountains or [],
    }
    return {"id": project_id, "fields": fields}


def _make_mountain_record(mountain_id="recM1", name="Test Mountain", goals=None):
    fields = {"Title": name, "Status": "Active", "1yr Goal": goals or []}
    return {"id": mountain_id, "fields": fields}


def _make_goal_record(goal_id="recG1", name="Big Goal"):
    return {"id": goal_id, "fields": {"Name": name, "Status": "On Track"}}


def _mock_fetch(return_value):
    body = json.dumps(return_value).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# TestGetTask
# ---------------------------------------------------------------------------


class TestGetTask:
    """get_task() fetches a task and optionally resolves linked records."""

    @patch("urllib.request.urlopen")
    def test_basic_task_fields(self, mock_urlopen):
        # Arrange
        task_record = _make_task_record()
        mock_urlopen.return_value = _mock_fetch(task_record)

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=False)

        # Assert
        assert result["id"] == "recT1"
        assert result["task"] == "Test Task"
        assert result["status"] == "In Progress"
        assert result["description"] == "Ship it"
        assert result["notes"] == "Some notes"
        assert "airtable_url" in result

    @patch("urllib.request.urlopen")
    def test_resolves_project_with_goal_fallback(self, mock_urlopen):
        """When project has no mountain link, falls back to direct project->goal."""
        # Arrange
        task_record = _make_task_record(project_ids=["recP1"])
        project_record = _make_project_record(goals=["recG1"])  # no mountains
        goal_record = _make_goal_record()

        mock_urlopen.side_effect = [
            _mock_fetch(task_record),  # fetch task
            _mock_fetch(project_record),  # resolve project
            _mock_fetch(project_record),  # re-fetch project for mountain/goal
            _mock_fetch(goal_record),  # resolve goal (fallback path)
        ]

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=True)

        # Assert
        assert "project" in result
        assert result["project"]["name"] == "My Project"
        assert "mountain" not in result
        assert "goal" in result
        assert result["goal"]["name"] == "Big Goal"

    @patch("urllib.request.urlopen")
    def test_no_resolve_links(self, mock_urlopen):
        # Arrange
        task_record = _make_task_record(project_ids=["recP1"])
        mock_urlopen.return_value = _mock_fetch(task_record)

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=False)

        # Assert
        assert "project" not in result
        assert "goal" not in result

    @patch("urllib.request.urlopen")
    def test_missing_project_link(self, mock_urlopen):
        # Arrange
        task_record = _make_task_record(project_ids=[])
        mock_urlopen.return_value = _mock_fetch(task_record)

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=True)

        # Assert
        assert "project" not in result

    @patch("get_task.fetch_record")
    def test_task_not_found_exits(self, mock_fetch_record):
        # Arrange
        mock_fetch_record.return_value = None

        # Act & Assert
        with pytest.raises(SystemExit):
            get_task.get_task(_config, "personal", "recNotFound")


class TestFetchRecord:
    """fetch_record() handles API errors gracefully."""

    @patch("urllib.request.urlopen")
    def test_returns_record(self, mock_urlopen):
        # Arrange
        record = {"id": "rec1", "fields": {"Name": "Test"}}
        mock_urlopen.return_value = _mock_fetch(record)

        # Act
        result = get_task.fetch_record("appXXX", "tblXXX", "rec1")

        # Assert
        assert result["id"] == "rec1"

    @patch("urllib.request.urlopen")
    def test_http_error_returns_none(self, mock_urlopen):
        # Arrange
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=MagicMock(read=lambda: b"not found"),
        )

        # Act
        result = get_task.fetch_record("appXXX", "tblXXX", "recMissing")

        # Assert
        assert result is None


class TestResolveMountain:
    """resolve_mountain() follows the project -> mountain link."""

    def test_returns_mountain_and_fields(self):
        # Arrange
        base_cfg = get_base(_config, "personal")
        project_fields = {"Mountains (30d)": ["recM1"]}

        with patch("get_task.fetch_record") as mock_fetch_rec:
            mock_fetch_rec.return_value = _make_mountain_record(name="Q1 Revenue")

            # Act
            mountain, mtn_fields = get_task.resolve_mountain(base_cfg, project_fields)

        # Assert
        assert mountain is not None
        assert mountain["name"] == "Q1 Revenue"
        assert mountain["id"] == "recM1"
        assert "Title" in mtn_fields

    def test_returns_none_when_no_mountain_field(self):
        # Arrange -- config with no project_mountain_field
        base_cfg = {"project_mountain_field": None}

        # Act
        mountain, fields = get_task.resolve_mountain(base_cfg, {})

        # Assert
        assert mountain is None
        assert fields == {}

    def test_returns_none_when_no_mountain_ids(self):
        # Arrange
        base_cfg = get_base(_config, "personal")
        project_fields = {"Mountains (30d)": []}

        # Act
        mountain, fields = get_task.resolve_mountain(base_cfg, project_fields)

        # Assert
        assert mountain is None

    def test_returns_none_when_fetch_fails(self):
        # Arrange
        base_cfg = get_base(_config, "personal")
        project_fields = {"Mountains (30d)": ["recM1"]}

        with patch("get_task.fetch_record") as mock_fetch_rec:
            mock_fetch_rec.return_value = None

            # Act
            mountain, fields = get_task.resolve_mountain(base_cfg, project_fields)

        # Assert
        assert mountain is None
        assert fields == {}


class TestResolveGoalFromMountain:
    """resolve_goal_from_mountain() follows the mountain -> goal link."""

    def test_returns_goal(self):
        # Arrange
        base_cfg = get_base(_config, "personal")
        mountain_fields = {"1yr Goal": ["recG1"]}

        with patch("get_task.fetch_record") as mock_fetch_rec:
            mock_fetch_rec.return_value = _make_goal_record(name="Annual Goal")

            # Act
            goal = get_task.resolve_goal_from_mountain(base_cfg, mountain_fields)

        # Assert
        assert goal is not None
        assert goal["name"] == "Annual Goal"
        assert goal["type"] == "annual"

    def test_returns_none_when_no_goal_field_configured(self):
        # Arrange
        base_cfg = {"mountain_goal_field": None}

        # Act
        goal = get_task.resolve_goal_from_mountain(base_cfg, {})

        # Assert
        assert goal is None

    def test_returns_none_when_no_goal_ids(self):
        # Arrange
        base_cfg = get_base(_config, "personal")
        mountain_fields = {"1yr Goal": []}

        # Act
        goal = get_task.resolve_goal_from_mountain(base_cfg, mountain_fields)

        # Assert
        assert goal is None


class TestGetTaskMountainChain:
    """get_task resolves the full project -> mountain -> goal chain."""

    @patch("urllib.request.urlopen")
    def test_resolves_full_mountain_goal_chain(self, mock_urlopen):
        # Arrange
        task_record = _make_task_record(project_ids=["recP1"])
        project_record = _make_project_record(mountains=["recM1"])
        mountain_record = _make_mountain_record(name="Revenue Mtn", goals=["recG1"])
        goal_record = _make_goal_record(name="Annual Objective")

        mock_urlopen.side_effect = [
            _mock_fetch(task_record),  # fetch task
            _mock_fetch(project_record),  # resolve project
            _mock_fetch(project_record),  # re-fetch project for mountain chain
            _mock_fetch(mountain_record),  # resolve mountain
            _mock_fetch(goal_record),  # resolve goal from mountain
        ]

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=True)

        # Assert
        assert result["project"]["name"] == "My Project"
        assert result["mountain"]["name"] == "Revenue Mtn"
        assert result["goal"]["name"] == "Annual Objective"

    @patch("urllib.request.urlopen")
    def test_mountain_without_goal_still_resolves(self, mock_urlopen):
        # Arrange
        task_record = _make_task_record(project_ids=["recP1"])
        project_record = _make_project_record(mountains=["recM1"])
        mountain_record = _make_mountain_record(name="No Goal Mtn")  # no goals linked

        mock_urlopen.side_effect = [
            _mock_fetch(task_record),
            _mock_fetch(project_record),
            _mock_fetch(project_record),
            _mock_fetch(mountain_record),
        ]

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=True)

        # Assert
        assert result["mountain"]["name"] == "No Goal Mtn"
        assert "goal" not in result

    @patch("urllib.request.urlopen")
    def test_mountain_goal_takes_precedence_over_project_goal(self, mock_urlopen):
        """When both mountain->goal and project->goal exist, mountain path wins."""
        # Arrange
        task_record = _make_task_record(project_ids=["recP1"])
        project_record = _make_project_record(
            goals=["recG_project"], mountains=["recM1"]
        )
        mountain_record = _make_mountain_record(
            name="Mountain", goals=["recG_mountain"]
        )
        mountain_goal = {
            "id": "recG_mountain",
            "fields": {"Name": "Mountain Goal", "Status": "Active"},
        }

        mock_urlopen.side_effect = [
            _mock_fetch(task_record),
            _mock_fetch(project_record),
            _mock_fetch(project_record),
            _mock_fetch(mountain_record),
            _mock_fetch(mountain_goal),
        ]

        # Act
        result = get_task.get_task(_config, "personal", "recT1", resolve_links=True)

        # Assert -- mountain goal should win, project goal fallback should not fire
        assert result["goal"]["name"] == "Mountain Goal"
