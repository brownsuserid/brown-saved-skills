"""Tests for gather_annual_data.py — Mountains, project stats, and mountain stats."""

import json
import os
import sys
from unittest.mock import MagicMock, patch


os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "annual-planning")
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

from gather_annual_data import (  # noqa: E402
    fetch_all_mountains,
    fetch_project_stats,
    compute_mountain_stats,
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
# TestFetchAllMountains
# ---------------------------------------------------------------------------


class TestFetchAllMountains:
    @patch("gather_annual_data.urllib.request.urlopen")
    def test_returns_all_mountains_including_completed(self, mock_urlopen):
        api_data = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Title": "Launch MVP",
                        "Status": "Complete",
                        "1yr Goals": ["recObj1"],
                    },
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Title": "Hire team",
                        "Status": "In Progress",
                        "1yr Goals": ["recObj2"],
                    },
                },
                {
                    "id": "rec3",
                    "fields": {
                        "Title": "Old initiative",
                        "Status": "Archived",
                        "1yr Goals": [],
                    },
                },
            ]
        }
        mock_urlopen.return_value = _mock_urlopen_with_response(api_data).return_value

        result = fetch_all_mountains("personal", _test_config)

        assert len(result) == 3
        statuses = [m["status"] for m in result]
        assert "Complete" in statuses
        assert "Archived" in statuses
        assert "In Progress" in statuses
        assert result[0]["title"] == "Launch MVP"
        assert result[0]["objective_ids"] == ["recObj1"]

    @patch("gather_annual_data.urllib.request.urlopen")
    def test_handles_pagination(self, mock_urlopen):
        page1 = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Title": "Mountain A",
                        "Status": "Active",
                        "1yr Goals": [],
                    },
                },
            ],
            "offset": "itr12345",
        }
        page2 = {
            "records": [
                {
                    "id": "rec2",
                    "fields": {
                        "Title": "Mountain B",
                        "Status": "Complete",
                        "1yr Goals": [],
                    },
                },
            ],
        }

        resp1 = MagicMock()
        resp1.read.return_value = json.dumps(page1).encode()
        resp1.__enter__ = lambda s: s
        resp1.__exit__ = MagicMock(return_value=False)

        resp2 = MagicMock()
        resp2.read.return_value = json.dumps(page2).encode()
        resp2.__enter__ = lambda s: s
        resp2.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [resp1, resp2]

        result = fetch_all_mountains("personal", _test_config)

        assert len(result) == 2
        assert result[0]["title"] == "Mountain A"
        assert result[1]["title"] == "Mountain B"
        assert mock_urlopen.call_count == 2

    @patch("gather_annual_data.urllib.request.urlopen")
    def test_returns_empty_on_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = _make_http_error()

        result = fetch_all_mountains("personal", _test_config)

        assert result == []


# ---------------------------------------------------------------------------
# TestFetchProjectStats
# ---------------------------------------------------------------------------


class TestFetchProjectStats:
    @patch("gather_annual_data.urllib.request.urlopen")
    def test_computes_completion_rate(self, mock_urlopen):
        api_data = {
            "records": [
                {"id": "p1", "fields": {"Status": "Complete"}},
                {"id": "p2", "fields": {"Status": "Done"}},
                {"id": "p3", "fields": {"Status": "Active"}},
                {"id": "p4", "fields": {"Status": "In Progress"}},
                {"id": "p5", "fields": {"Status": "Archived"}},
            ]
        }
        mock_urlopen.return_value = _mock_urlopen_with_response(api_data).return_value

        result = fetch_project_stats("personal", _test_config)

        # Complete, Done, Archived = 3 done out of 5
        assert result["total"] == 5
        assert result["completed"] == 3
        assert result["active"] == 2
        assert result["completion_rate"] == 60.0

    @patch("gather_annual_data.urllib.request.urlopen")
    def test_returns_zero_stats_on_error(self, mock_urlopen):
        mock_urlopen.side_effect = _make_http_error()

        result = fetch_project_stats("personal", _test_config)

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["active"] == 0
        assert result["completion_rate"] == 0


# ---------------------------------------------------------------------------
# TestComputeMountainStats (pure function, no mocking)
# ---------------------------------------------------------------------------


class TestComputeMountainStats:
    SAMPLE_MOUNTAINS = [
        {"id": "rec1", "title": "A", "status": "Complete", "objective_ids": ["obj1"]},
        {
            "id": "rec2",
            "title": "B",
            "status": "In Progress",
            "objective_ids": ["obj1", "obj2"],
        },
        {"id": "rec3", "title": "C", "status": "Archived", "objective_ids": ["obj2"]},
        {
            "id": "rec4",
            "title": "D",
            "status": "Not Started",
            "objective_ids": ["obj1"],
        },
        {"id": "rec5", "title": "E", "status": "Complete", "objective_ids": ["obj2"]},
    ]

    def test_all_mountains_stats(self):
        result = compute_mountain_stats(self.SAMPLE_MOUNTAINS)

        assert result["total"] == 5
        assert result["completed"] == 2
        assert result["active"] == 2  # In Progress + Not Started
        assert result["archived"] == 1
        assert result["completion_rate"] == 40.0

    def test_filters_by_objective_id(self):
        result = compute_mountain_stats(self.SAMPLE_MOUNTAINS, objective_id="obj1")

        # obj1: rec1 (Complete), rec2 (In Progress), rec4 (Not Started)
        assert result["total"] == 3
        assert result["completed"] == 1
        assert result["active"] == 2
        assert result["archived"] == 0

    def test_empty_list_returns_zeros(self):
        result = compute_mountain_stats([])

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["active"] == 0
        assert result["archived"] == 0
        assert result["completion_rate"] == 0

    def test_completion_rate_calculation(self):
        mountains = [
            {"id": "r1", "title": "X", "status": "Complete", "objective_ids": []},
            {"id": "r2", "title": "Y", "status": "Complete", "objective_ids": []},
            {"id": "r3", "title": "Z", "status": "In Progress", "objective_ids": []},
        ]
        result = compute_mountain_stats(mountains)

        # 2 out of 3 complete = 66.7%
        assert result["completion_rate"] == 66.7
        assert result["completed"] == 2
        assert result["total"] == 3
