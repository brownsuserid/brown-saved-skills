"""Tests for search_tasks.py -- ensures task output includes all required fields."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Provide a dummy token so config loading works
os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)
sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "executing-tasks"
        )
    ),
)

from airtable_config import get_people, load_config

from search_tasks import (  # noqa: E402
    _fetch_record,
    build_filter,
    resolve_assignee_id,
    resolve_hierarchy,
    search_base,
)

# Load config once for all tests
_config = load_config()


def _make_airtable_response(records: list[dict]) -> bytes:
    """Build a fake Airtable API response body."""
    return json.dumps({"records": records}).encode()


def _make_record(
    record_id: str = "rec123",
    task: str = "Test task",
    description: str = "Definition of done text",
    status: str = "Not Started",
    score: int = 80,
    notes: str = "Some notes",
    due_date: str = "2026-03-01",
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
    }
    if assignee_ids is not None:
        fields["Assignee"] = assignee_ids
    return {"id": record_id, "fields": fields}


class TestSearchBaseOutputFields:
    """search_base must return description, notes, and all other fields."""

    @patch("urllib.request.urlopen")
    def test_output_includes_description_field(self, mock_urlopen):
        # Arrange
        record = _make_record(description="Must ship by Friday")
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert len(results) == 1
        assert "description" in results[0]
        assert results[0]["description"] == "Must ship by Friday"

    @patch("urllib.request.urlopen")
    def test_output_includes_notes_field(self, mock_urlopen):
        # Arrange
        record = _make_record(notes="Blocked on Aaron review")
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results[0]["notes"] == "Blocked on Aaron review"

    @patch("urllib.request.urlopen")
    def test_output_includes_task_name(self, mock_urlopen):
        # Arrange
        record = _make_record(task="Follow up with Dan")
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results[0]["task"] == "Follow up with Dan"

    @patch("urllib.request.urlopen")
    def test_output_includes_airtable_url(self, mock_urlopen):
        # Arrange
        record = _make_record(record_id="rec456")
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert "airtable_url" in results[0]
        assert "rec456" in results[0]["airtable_url"]

    @patch("urllib.request.urlopen")
    def test_empty_description_returns_empty_string(self, mock_urlopen):
        """Tasks without a Definition of Done should return '' not KeyError."""
        # Arrange
        record = {
            "id": "rec789",
            "fields": {"Task": "Quick task", "Status": "Not Started", "Score": 50},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results[0]["description"] == ""
        assert results[0]["notes"] == ""


class TestBuildFilterExcludesArchived:
    """build_filter must exclude Archived status when include_done=False."""

    def test_personal_filter_excludes_archived(self):
        formula = build_filter(
            _config, "personal", status=None, query=None, include_done=False
        )
        assert "Archived" in formula
        assert "{Status}!='Archived'" in formula

    def test_bb_filter_excludes_archived(self):
        formula = build_filter(
            _config, "bb", status=None, query=None, include_done=False
        )
        assert "{Status}!='Archived'" in formula

    def test_aitb_filter_excludes_archived(self):
        formula = build_filter(
            _config, "aitb", status=None, query=None, include_done=False
        )
        assert "{Status}!='Archived'" in formula

    def test_include_done_does_not_filter_archived(self):
        formula = build_filter(
            _config, "personal", status=None, query=None, include_done=True
        )
        assert "Archived" not in formula


class TestResolveAssigneeId:
    """resolve_assignee_id() translates names to record IDs."""

    def test_known_assignee_returns_id(self):
        result = resolve_assignee_id(_config, "pablo", "personal")
        assert result is not None
        assert result.startswith("rec")

    def test_unknown_assignee_returns_none(self):
        result = resolve_assignee_id(_config, "unknown_person", "personal")
        assert result is None

    def test_record_id_passed_through(self):
        result = resolve_assignee_id(_config, "recXYZ123", "personal")
        assert result == "recXYZ123"

    def test_empty_assignee_returns_none(self):
        result = resolve_assignee_id(_config, "", "personal")
        assert result is None

    def test_none_assignee_returns_none(self):
        result = resolve_assignee_id(_config, None, "personal")
        assert result is None


class TestBuildFilterStatus:
    """build_filter() handles status filtering correctly."""

    def test_single_status_filter(self):
        formula = build_filter(
            _config, "personal", status="in_progress", query=None, include_done=True
        )
        assert "{Status}='In Progress'" in formula

    def test_comma_separated_status_filter(self):
        formula = build_filter(
            _config,
            "personal",
            status="in_progress,blocked",
            query=None,
            include_done=True,
        )
        assert "OR(" in formula
        assert "{Status}='In Progress'" in formula
        assert "{Status}='Blocked'" in formula


class TestBuildFilterQuery:
    """build_filter() handles text search queries."""

    def test_query_searches_task_and_description(self):
        formula = build_filter(
            _config, "personal", status=None, query="urgent", include_done=True
        )
        assert "FIND(LOWER('urgent'), LOWER({Task}))" in formula
        assert "Definition of Done" in formula

    def test_query_escapes_single_quotes(self):
        formula = build_filter(
            _config,
            "personal",
            status=None,
            query="it's important",
            include_done=True,
        )
        assert "it\\'s important" in formula


class TestSearchBaseFiltering:
    """search_base() filters by assignee locally."""

    @patch("urllib.request.urlopen")
    def test_filters_by_assignee_locally(self, mock_urlopen):
        # Arrange - two records, only one assigned to Pablo
        people = get_people(_config)
        pablo_id = people["pablo"]["personal"]
        aaron_id = people["aaron"]["personal"]

        record_pablo = _make_record(record_id="rec1", assignee_ids=[pablo_id])
        record_aaron = _make_record(record_id="rec2", assignee_ids=[aaron_id])

        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response(
            [record_pablo, record_aaron]
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act - search for Pablo's tasks only
        results = search_base(_config, "personal", "", 10, pablo_id)

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "rec1"

    @patch("urllib.request.urlopen")
    def test_http_error_returns_empty_list(self, mock_urlopen):
        # Arrange
        import urllib.error

        error_response = MagicMock()
        error_response.read.return_value = b'{"error": "Bad request"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 400, "Bad Request", {}, error_response
        )

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results == []

    @patch("urllib.request.urlopen")
    def test_generic_error_returns_empty_list(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = Exception("Network timeout")

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results == []


class TestSearchBaseProjectIds:
    """search_base must include project_ids in task output."""

    @patch("urllib.request.urlopen")
    def test_output_includes_project_ids(self, mock_urlopen):
        # Arrange
        record = {
            "id": "rec1",
            "fields": {
                "Task": "Test task",
                "Status": "In Progress",
                "Score": 80,
                "Project": ["recP1", "recP2"],
            },
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results[0]["project_ids"] == ["recP1", "recP2"]

    @patch("urllib.request.urlopen")
    def test_empty_project_ids_returns_empty_list(self, mock_urlopen):
        # Arrange
        record = {
            "id": "rec1",
            "fields": {"Task": "No project", "Status": "Not Started", "Score": 50},
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "personal", "", 10, None)

        # Assert
        assert results[0]["project_ids"] == []

    @patch("urllib.request.urlopen")
    def test_bb_base_uses_rock_field_for_project_ids(self, mock_urlopen):
        """BB base uses 'Rock' field instead of 'Project'."""
        # Arrange
        record = {
            "id": "rec1",
            "fields": {
                "Task": "BB task",
                "Status": "In Progress",
                "Score": 90,
                "Rock": ["recR1"],
            },
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_base(_config, "bb", "", 10, None)

        # Assert
        assert results[0]["project_ids"] == ["recR1"]


def _mock_fetch_response(data):
    """Create a urlopen mock that returns a single JSON record."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestFetchRecord:
    """_fetch_record fetches a single record and handles errors."""

    @patch("urllib.request.urlopen")
    def test_returns_record_on_success(self, mock_urlopen):
        # Arrange
        record = {"id": "rec1", "fields": {"Name": "Test"}}
        mock_urlopen.return_value = _mock_fetch_response(record)

        # Act
        result = _fetch_record("appXXX", "tblXXX", "rec1")

        # Assert
        assert result["id"] == "rec1"
        assert result["fields"]["Name"] == "Test"

    @patch("urllib.request.urlopen")
    def test_url_encodes_table_name_with_spaces(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_fetch_response({"id": "rec1", "fields": {}})

        # Act
        _fetch_record("appXXX", "Rocks (7d)", "rec1")

        # Assert
        url = mock_urlopen.call_args[0][0].full_url
        assert "Rocks%20%287d%29" in url

    @patch("urllib.request.urlopen")
    def test_returns_none_on_error(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = Exception("Connection refused")

        # Act
        result = _fetch_record("appXXX", "tblXXX", "recMissing")

        # Assert
        assert result is None


class TestResolveHierarchyProjectOnly:
    """resolve_hierarchy annotates tasks with project_name when mountains disabled."""

    @patch("search_tasks._fetch_record")
    def test_adds_project_name_to_tasks(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = {
            "id": "recP1",
            "fields": {"Project": "My Project", "Mountains (30d)": ["recM1"]},
        }
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=False, include_goals=False)

        # Assert
        assert tasks[0]["project_name"] == "My Project"
        assert "mountain_name" not in tasks[0]

    @patch("search_tasks._fetch_record")
    def test_skips_tasks_without_project_ids(self, mock_fetch):
        # Arrange
        tasks = [{"base": "personal", "project_ids": []}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=False)

        # Assert
        assert "project_name" not in tasks[0]
        mock_fetch.assert_not_called()

    @patch("search_tasks._fetch_record")
    def test_skips_tasks_with_unknown_base(self, mock_fetch):
        # Arrange
        tasks = [{"base": "nonexistent", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=False)

        # Assert
        assert "project_name" not in tasks[0]
        mock_fetch.assert_not_called()

    @patch("search_tasks._fetch_record")
    def test_handles_failed_project_fetch(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = None
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=False)

        # Assert
        assert tasks[0]["project_name"] == ""


class TestResolveHierarchyWithMountains:
    """resolve_hierarchy annotates tasks with mountain_name."""

    @patch("search_tasks._fetch_record")
    def test_adds_mountain_name(self, mock_fetch):
        # Arrange -- project fetch, then mountain fetch
        mock_fetch.side_effect = [
            {
                "id": "recP1",
                "fields": {"Project": "My Project", "Mountains (30d)": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "Revenue Mountain", "1yr Goal": ["recG1"]},
            },
        ]
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True, include_goals=False)

        # Assert
        assert tasks[0]["project_name"] == "My Project"
        assert tasks[0]["mountain_name"] == "Revenue Mountain"
        assert "goal_name" not in tasks[0]

    @patch("search_tasks._fetch_record")
    def test_skips_mountain_when_project_has_no_mountain_link(self, mock_fetch):
        # Arrange -- project has no mountain IDs
        mock_fetch.return_value = {
            "id": "recP1",
            "fields": {"Project": "Solo Project"},
        }
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True)

        # Assert
        assert tasks[0]["project_name"] == "Solo Project"
        assert "mountain_name" not in tasks[0]

    @patch("search_tasks._fetch_record")
    def test_bb_base_uses_correct_field_names(self, mock_fetch):
        # Arrange -- BB uses "Project name" and "Mountains"
        mock_fetch.side_effect = [
            {
                "id": "recR1",
                "fields": {"Project name": "Weekly Rock", "Mountains": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "BB Mountain", "Objective (1y)": ["recG1"]},
            },
        ]
        tasks = [{"base": "bb", "project_ids": ["recR1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True, include_goals=False)

        # Assert
        assert tasks[0]["project_name"] == "Weekly Rock"
        assert tasks[0]["mountain_name"] == "BB Mountain"


class TestResolveHierarchyWithGoals:
    """resolve_hierarchy annotates tasks with goal_name when include_goals=True."""

    @patch("search_tasks._fetch_record")
    def test_adds_goal_name(self, mock_fetch):
        # Arrange -- project, mountain, goal
        mock_fetch.side_effect = [
            {
                "id": "recP1",
                "fields": {"Project": "My Project", "Mountains (30d)": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "Revenue Mountain", "1yr Goal": ["recG1"]},
            },
            {
                "id": "recG1",
                "fields": {"Name": "10 Happy Customers"},
            },
        ]
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True, include_goals=True)

        # Assert
        assert tasks[0]["project_name"] == "My Project"
        assert tasks[0]["mountain_name"] == "Revenue Mountain"
        assert tasks[0]["goal_name"] == "10 Happy Customers"

    @patch("search_tasks._fetch_record")
    def test_bb_goal_uses_objective_field(self, mock_fetch):
        # Arrange -- BB uses "Objective" as goal name field
        mock_fetch.side_effect = [
            {
                "id": "recR1",
                "fields": {"Project name": "Rock", "Mountains": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "Mountain", "Objective (1y)": ["recG1"]},
            },
            {
                "id": "recG1",
                "fields": {"Objective": "BB Annual Goal"},
            },
        ]
        tasks = [{"base": "bb", "project_ids": ["recR1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True, include_goals=True)

        # Assert
        assert tasks[0]["goal_name"] == "BB Annual Goal"

    @patch("search_tasks._fetch_record")
    def test_skips_goal_when_mountain_has_no_goal_link(self, mock_fetch):
        # Arrange -- mountain has no goal IDs
        mock_fetch.side_effect = [
            {
                "id": "recP1",
                "fields": {"Project": "Project", "Mountains (30d)": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "Mountain"},
            },
        ]
        tasks = [{"base": "personal", "project_ids": ["recP1"]}]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True, include_goals=True)

        # Assert
        assert tasks[0]["mountain_name"] == "Mountain"
        assert "goal_name" not in tasks[0]


class TestResolveHierarchyCaching:
    """resolve_hierarchy caches fetched records to avoid duplicate API calls."""

    @patch("search_tasks._fetch_record")
    def test_same_project_fetched_only_once(self, mock_fetch):
        # Arrange -- two tasks sharing the same project
        mock_fetch.return_value = {
            "id": "recP1",
            "fields": {"Project": "Shared Project"},
        }
        tasks = [
            {"base": "personal", "project_ids": ["recP1"]},
            {"base": "personal", "project_ids": ["recP1"]},
        ]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=False)

        # Assert -- only one fetch for the project
        assert mock_fetch.call_count == 1
        assert tasks[0]["project_name"] == "Shared Project"
        assert tasks[1]["project_name"] == "Shared Project"

    @patch("search_tasks._fetch_record")
    def test_same_mountain_fetched_only_once(self, mock_fetch):
        # Arrange -- two tasks, same project, same mountain
        mock_fetch.side_effect = [
            {
                "id": "recP1",
                "fields": {"Project": "Project", "Mountains (30d)": ["recM1"]},
            },
            {
                "id": "recM1",
                "fields": {"Title": "Mountain"},
            },
        ]
        tasks = [
            {"base": "personal", "project_ids": ["recP1"]},
            {"base": "personal", "project_ids": ["recP1"]},
        ]

        # Act
        resolve_hierarchy(_config, tasks, include_mountains=True)

        # Assert -- 1 project fetch + 1 mountain fetch = 2 total
        assert mock_fetch.call_count == 2
        assert tasks[0]["mountain_name"] == "Mountain"
        assert tasks[1]["mountain_name"] == "Mountain"
