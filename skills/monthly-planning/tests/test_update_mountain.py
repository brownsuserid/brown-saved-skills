"""Tests for update_mountain.py — verifies status/priority updates per base."""

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
            os.path.dirname(__file__), "..", "..", "scripts", "monthly-planning"
        )
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from update_mountain import update_mountain  # noqa: E402


def _mock_response(record_id: str = "recMOUNTAIN123", fields: dict | None = None):
    """Build a mock urllib response matching Airtable's PATCH response."""
    data = {"id": record_id, "fields": fields or {}}
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestUpdateMountainStatus:
    """Status updates across bases."""

    @patch("urllib.request.urlopen")
    def test_archive_bb_mountain(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_mountain(
            base_key="bb",
            record_id="recMOUNTAIN123",
            config=_test_config,
            status="archived",
        )

        assert result["id"] == "recMOUNTAIN123"
        assert "status" in result["updated_fields"]

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Archived"

    @patch("urllib.request.urlopen")
    def test_complete_aitb_mountain(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_mountain(
            base_key="aitb",
            record_id="recAITBMTN",
            config=_test_config,
            status="complete",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Completed"

    @patch("urllib.request.urlopen")
    def test_update_personal_mountain_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        update_mountain(
            base_key="personal",
            record_id="recPERSMTN",
            config=_test_config,
            status="at_risk",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "At risk"


class TestUpdateMountainPriority:
    """Priority updates."""

    @patch("urllib.request.urlopen")
    def test_update_priority(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_mountain(
            base_key="bb",
            record_id="recMTN",
            config=_test_config,
            priority=9,
        )

        assert "priority" in result["updated_fields"]
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Priority"] == 9


class TestUpdateMountainMultipleFields:
    """Multiple field updates in one call."""

    @patch("urllib.request.urlopen")
    def test_status_and_priority(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_mountain(
            base_key="bb",
            record_id="recMTN",
            config=_test_config,
            status="on_track",
            priority=7,
        )

        assert "status" in result["updated_fields"]
        assert "priority" in result["updated_fields"]

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "On track"
        assert payload["fields"]["Priority"] == 7

    @patch("urllib.request.urlopen")
    def test_title_and_description(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = update_mountain(
            base_key="aitb",
            record_id="recMTN",
            config=_test_config,
            title="Updated Title",
            description="Updated DoD",
        )

        assert "title" in result["updated_fields"]
        assert "description" in result["updated_fields"]

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Title"] == "Updated Title"
        assert payload["fields"]["Definition of Done"] == "Updated DoD"

    @patch("urllib.request.urlopen")
    def test_uses_patch_method(self, mock_urlopen):
        """Updates should use PATCH, not POST."""
        mock_urlopen.return_value = _mock_response()

        update_mountain(
            base_key="bb",
            record_id="recMTN",
            config=_test_config,
            status="on_hold",
        )

        req = mock_urlopen.call_args[0][0]
        assert req.method == "PATCH"
        assert "recMTN" in req.full_url
