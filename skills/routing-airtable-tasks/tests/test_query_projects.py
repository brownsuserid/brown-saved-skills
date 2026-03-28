"""Tests for query_projects.py — Airtable project querying."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "routing-airtable-tasks"
    ),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

import airtable_config  # noqa: E402
import query_projects  # noqa: E402

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


# ---------------------------------------------------------------------------
# TestFetchProjects
# ---------------------------------------------------------------------------


class TestFetchProjects:
    """fetch_projects() queries per-base with correct field mapping."""

    @patch("urllib.request.urlopen")
    def test_personal_uses_project_name_field(self, mock_urlopen):
        # Arrange
        record = {
            "id": "recP1",
            "fields": {"Project": "My Project", "Status": "Active"},
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_projects.fetch_projects("personal", _test_config)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "My Project"

    @patch("urllib.request.urlopen")
    def test_bb_uses_project_name_field(self, mock_urlopen):
        # Arrange - BB uses "Project name" field (not "Name")
        record = {
            "id": "recP1",
            "fields": {"Project name": "BB Project", "Status": "Active"},
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_projects.fetch_projects("bb", _test_config)

        # Assert
        assert result[0]["name"] == "BB Project"

    @patch("urllib.request.urlopen")
    def test_aitb_uses_project_name_field(self, mock_urlopen):
        # Arrange
        record = {
            "id": "recP1",
            "fields": {"Project Name": "AITB Proj", "Status": "In Progress"},
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_projects.fetch_projects("aitb", _test_config)

        # Assert
        assert result[0]["name"] == "AITB Proj"

    @patch("urllib.request.urlopen")
    def test_active_only_filter_personal(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_records([]).return_value

        # Act — include_all defaults to False, so done statuses are excluded
        query_projects.fetch_projects("personal", _test_config)

        # Assert
        url = mock_urlopen.call_args[0][0].full_url
        assert "filterByFormula" in url
        assert "Complete" in url

    @patch("urllib.request.urlopen")
    def test_active_only_filter_bb(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_records([]).return_value

        # Act
        query_projects.fetch_projects("bb", _test_config)

        # Assert
        url = mock_urlopen.call_args[0][0].full_url
        # BB done status is "Completed" — single condition, no AND
        assert "Completed" in url

    @patch("urllib.request.urlopen")
    def test_active_only_filter_aitb_multiple_statuses(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_records([]).return_value

        # Act
        query_projects.fetch_projects("aitb", _test_config)

        # Assert
        url = mock_urlopen.call_args[0][0].full_url
        assert "AND" in url
        assert "Complete" in url
        assert "Archived" in url

    @patch("urllib.request.urlopen")
    def test_personal_includes_linked_goals(self, mock_urlopen):
        # Arrange
        record = {
            "id": "recP1",
            "fields": {
                "Project": "Has Goals",
                "Status": "Active",
                "1yr Goals": ["recG1"],
            },
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_projects.fetch_projects("personal", _test_config)

        # Assert
        assert result[0]["linked_goals"] == ["recG1"]

    @patch("urllib.request.urlopen")
    def test_bb_omits_linked_goals(self, mock_urlopen):
        # Arrange — BB config has goals_field = None
        record = {
            "id": "recP1",
            "fields": {"Project name": "BB Proj", "Status": "Active"},
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_projects.fetch_projects("bb", _test_config)

        # Assert
        assert "linked_goals" not in result[0]

    @patch("urllib.request.urlopen")
    def test_empty_results(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_records([]).return_value

        # Act
        result = query_projects.fetch_projects("personal", _test_config)

        # Assert
        assert result == []

    def test_invalid_base_exits(self):
        import pytest

        with pytest.raises(SystemExit):
            query_projects.fetch_projects("nonexistent", _test_config)
