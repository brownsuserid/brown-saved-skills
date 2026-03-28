"""Tests for query_goals.py — Airtable goal querying per base/type."""

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

import query_goals

# Load config for tests
import sys as _sys

_sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")
)
import airtable_config  # noqa: E402

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


def _make_goal_record(goal_id="recG1", name="Ship v2", status="On Track", **extra):
    fields = {"Name": name, "Status": status, **extra}
    return {"id": goal_id, "fields": fields}


# ---------------------------------------------------------------------------
# TestFetchGoals
# ---------------------------------------------------------------------------


class TestFetchGoals:
    """fetch_goals() queries the correct table per base/type combination."""

    @patch("urllib.request.urlopen")
    def test_personal_annual_uses_1yr_goals_table(self, mock_urlopen):
        # Arrange
        record = _make_goal_record()
        mock_urlopen.side_effect = _mock_urlopen_with_records([record]).side_effect
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_goals.fetch_goals("personal", "annual", _test_config)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "Ship v2"
        url = mock_urlopen.call_args[0][0].full_url
        assert "1yr%20Goals" in url

    @patch("urllib.request.urlopen")
    def test_bb_annual_uses_objective_field(self, mock_urlopen):
        # Arrange — BB annual uses "Objective" as name field
        record = {
            "id": "recG1",
            "fields": {"Objective": "Grow Revenue", "Status": "Active"},
        }
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_goals.fetch_goals("bb", "annual", _test_config)

        # Assert
        assert result[0]["name"] == "Grow Revenue"

    @patch("urllib.request.urlopen")
    def test_aitb_monthly_uses_title_field(self, mock_urlopen):
        # Arrange — AITB monthly uses "Title" as name field
        record = {"id": "recG1", "fields": {"Title": "Q1 Mountain", "Status": "Active"}}
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_goals.fetch_goals("aitb", "monthly", _test_config)

        # Assert
        assert result[0]["name"] == "Q1 Mountain"

    @patch("urllib.request.urlopen")
    def test_linked_down_included(self, mock_urlopen):
        # Arrange
        record = _make_goal_record()
        record["fields"]["Mountains (30d)"] = ["recM1", "recM2"]
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_goals.fetch_goals("aitb", "annual", _test_config)

        # Assert
        assert result[0]["linked_down"] == ["recM1", "recM2"]

    @patch("urllib.request.urlopen")
    def test_linked_projects_for_personal(self, mock_urlopen):
        # Arrange
        record = _make_goal_record()
        record["fields"]["Projects"] = ["recP1"]
        mock_urlopen.return_value = _mock_urlopen_with_records([record]).return_value

        # Act
        result = query_goals.fetch_goals("personal", "annual", _test_config)

        # Assert
        assert result[0]["linked_projects"] == ["recP1"]

    def test_invalid_base_exits(self):
        # Act & Assert
        import pytest

        with pytest.raises(SystemExit):
            query_goals.fetch_goals("nonexistent", "annual", _test_config)

    def test_invalid_type_exits(self):
        # Personal doesn't have monthly goals
        import pytest

        with pytest.raises(SystemExit):
            query_goals.fetch_goals("personal", "monthly", _test_config)

    @patch("urllib.request.urlopen")
    def test_empty_results(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_records([]).return_value

        # Act
        result = query_goals.fetch_goals("bb", "annual", _test_config)

        # Assert
        assert result == []
