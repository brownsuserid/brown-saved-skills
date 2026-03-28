"""Tests for gather_monthly_data.py — Mountains, projects, and task stats."""

import json
import os
import sys
from unittest.mock import MagicMock, patch


os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "monthly-planning"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "routing-airtable-tasks"
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from gather_monthly_data import (  # noqa: E402
    fetch_mountains,
    fetch_active_projects,
    fetch_task_stats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_urlopen_with_response(data):
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


def _make_http_error():
    import urllib.error

    err = urllib.error.HTTPError(
        url="https://api.airtable.com/v0/fake",
        code=422,
        msg="Unprocessable",
        hdrs={},
        fp=MagicMock(read=MagicMock(return_value=b"error")),
    )
    err.read = MagicMock(return_value=b"error")
    return err


# ---------------------------------------------------------------------------
# TestFetchMountains
# ---------------------------------------------------------------------------


class TestFetchMountains:
    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_returns_mountains_with_fields(self, mock_urlopen):
        api_data = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Title": "Ship v2",
                        "Definition of Done": "All features deployed",
                        "Status": "In Progress",
                        "1yr Goal": ["recGoalA"],
                        "Priority": 1,
                    },
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Title": "Hire designer",
                        "Definition of Done": "Signed offer letter",
                        "Status": "Not Started",
                        "1yr Goal": [],
                        "Priority": 2,
                    },
                },
            ]
        }
        mock_urlopen.return_value = _mock_urlopen_with_response(api_data).return_value

        result = fetch_mountains("personal", config=_test_config)

        assert len(result) == 2
        assert result[0]["id"] == "rec1"
        assert result[0]["title"] == "Ship v2"
        assert result[0]["description"] == "All features deployed"
        assert result[0]["status"] == "In Progress"
        assert result[0]["objective_ids"] == ["recGoalA"]
        assert result[0]["priority"] == 1
        assert result[1]["id"] == "rec2"
        assert result[1]["title"] == "Hire designer"

    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_returns_empty_on_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = _make_http_error()

        result = fetch_mountains("personal", config=_test_config)

        assert result == []

    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_filters_by_month_when_provided(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"records": []}
        ).return_value

        fetch_mountains("personal", config=_test_config, month="2026-03")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert "Month" in request_obj.full_url
        assert "2026-03" in request_obj.full_url


# ---------------------------------------------------------------------------
# TestFetchActiveProjects
# ---------------------------------------------------------------------------


class TestFetchActiveProjects:
    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_returns_active_projects(self, mock_urlopen):
        api_data = {
            "records": [
                {
                    "id": "recP1",
                    "fields": {"Project": "Website Redesign", "Status": "Active"},
                },
                {
                    "id": "recP2",
                    "fields": {"Project": "API Migration", "Status": "In Progress"},
                },
            ]
        }
        mock_urlopen.return_value = _mock_urlopen_with_response(api_data).return_value

        result = fetch_active_projects("personal", config=_test_config)

        assert len(result) == 2
        assert result[0]["id"] == "recP1"
        assert result[0]["name"] == "Website Redesign"
        assert result[0]["status"] == "Active"
        assert result[1]["name"] == "API Migration"

    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_returns_empty_on_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = _make_http_error()

        result = fetch_active_projects("personal", config=_test_config)

        assert result == []


# ---------------------------------------------------------------------------
# TestFetchTaskStats
# ---------------------------------------------------------------------------


class TestFetchTaskStats:
    @patch("gather_monthly_data.urllib.request.urlopen")
    def test_returns_counts(self, mock_urlopen):
        # fetch_task_stats makes multiple urlopen calls per status:
        # 1) pageSize=1 probe, 2) full count fetch (if records exist)
        # 3 statuses x 2 calls = 6 calls total

        probe_response = {"records": [{"id": "rec1", "fields": {}}]}
        active_records = {
            "records": [{"id": f"rec{i}", "fields": {}} for i in range(5)]
        }
        completed_records = {
            "records": [{"id": f"recC{i}", "fields": {}} for i in range(3)]
        }
        blocked_records = {"records": [{"id": "recB1", "fields": {}}]}

        responses = []
        # active: probe then full
        for data in [
            probe_response,
            active_records,
            probe_response,
            completed_records,
            probe_response,
            blocked_records,
        ]:
            resp = MagicMock()
            resp.read.return_value = json.dumps(data).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            responses.append(resp)

        mock_urlopen.side_effect = responses

        result = fetch_task_stats("personal", config=_test_config)

        assert result["active"] == 5
        assert result["completed"] == 3
        assert result["blocked"] == 1
