"""Tests for update_objective.py — verifies correct PATCH fields per base."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    str(os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")),
)
sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "annual-planning"
        )
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from update_objective import update_objective  # noqa: E402


def _mock_response(record_id: str = "recOBJ123", name: str = "Test"):
    """Build a mock urllib response matching Airtable's PATCH response."""
    data = {"id": record_id, "fields": {"Name": name}}
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestUpdateObjectiveStatus:
    """Status updates with per-base translation."""

    @patch("urllib.request.urlopen")
    def test_personal_done(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_objective(
            base_key="personal",
            record_id="recOBJ123",
            config=_test_config,
            status="done",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Done"
        assert result["updated_fields"] == ["Status"]
        assert mock_urlopen.call_args[0][0].method == "PATCH"

    @patch("urllib.request.urlopen")
    def test_aitb_on_track(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_objective(
            base_key="aitb",
            record_id="recOBJ456",
            config=_test_config,
            status="on_track",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "In progress"

    @patch("urllib.request.urlopen")
    def test_bb_archived(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_objective(
            base_key="bb", record_id="recOBJ789", config=_test_config, status="archived"
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Archived"


class TestUpdateObjectiveName:
    """Name field updates use correct per-base field name."""

    @patch("urllib.request.urlopen")
    def test_personal_uses_name(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_objective(
            base_key="personal",
            record_id="recOBJ123",
            config=_test_config,
            name="Updated Goal",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Name" in payload["fields"]
        assert "Objective" not in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_bb_uses_objective(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_objective(
            base_key="bb",
            record_id="recOBJ789",
            config=_test_config,
            name="Updated Objective",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Objective" in payload["fields"]
        assert "Name" not in payload["fields"]


class TestUpdateMultipleFields:
    """Multiple fields updated in one call."""

    @patch("urllib.request.urlopen")
    def test_status_and_description(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_objective(
            base_key="personal",
            record_id="recOBJ123",
            config=_test_config,
            status="on_track",
            description="Updated measurements",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "On Track"
        assert payload["fields"]["Measurements"] == "Updated measurements"
        assert len(result["updated_fields"]) == 2
