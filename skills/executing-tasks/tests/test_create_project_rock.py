"""Tests for create_project_rock.py -- verifies correct fields sent per base."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Provide a dummy token so config loading works
os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "executing-tasks"
        )
    ),
)
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import load_config

from create_project_rock import create_project

# Load config once for all tests
_config = load_config()


def _mock_response(record_id: str = "recNEWPROJ123", fields: dict | None = None):
    """Build a mock urllib response matching Airtable's POST response."""
    data = {
        "id": record_id,
        "fields": fields or {},
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestCreateProjectPersonal:
    """Personal base: Projects table, 1yr Goals linkage, no Driver field."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(fields={"Project": "Test Project"})

        result = create_project(
            config=_config,
            base_key="personal",
            name="Test Project",
            description="Done when tests pass",
        )

        assert result["id"] == "recNEWPROJ123"

        # Verify the request payload
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode())
        fields = payload["fields"]

        assert fields["Project"] == "Test Project"
        assert fields["Definition of Done"] == "Done when tests pass"
        assert fields["Status"] == "Not Started"

    @patch("urllib.request.urlopen")
    def test_goal_linkage(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="personal",
            name="Goal-linked Project",
            description="Done when linked",
            goal_id="recGOAL123",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["1yr Goals"] == ["recGOAL123"]

    @patch("urllib.request.urlopen")
    def test_driver_ignored_with_warning(self, mock_urlopen, capsys):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="personal",
            name="Driver Test",
            description="Done when tested",
            driver="aaron",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert "Driver" not in fields

        captured = capsys.readouterr()
        assert "no Driver field" in captured.err


class TestCreateProjectAITB:
    """AITB base: Projects table, no goal field, Driver field."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(
            fields={"Project Name": "AITB Project"}
        )

        create_project(
            config=_config,
            base_key="aitb",
            name="AITB Project",
            description="Done when shipped",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Project Name"] == "AITB Project"
        assert fields["Definition of Done"] == "Done when shipped"

    @patch("urllib.request.urlopen")
    def test_driver_set(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="aitb",
            name="Driver Test",
            description="Done when tested",
            driver="aaron",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        # Aaron's AITB record ID from people config
        assert fields["Driver"] == ["recQcvtMt34CXBV4p"]

    @patch("urllib.request.urlopen")
    def test_goal_appended_to_notes(self, mock_urlopen):
        """AITB has no goal field -- goal reference goes into notes."""
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="aitb",
            name="Goal Test",
            description="Done when tested",
            goal_id="recOBJ456",
            notes="Some context",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert "recOBJ456" in fields["Notes"]
        assert "Some context" in fields["Notes"]


class TestCreateProjectBB:
    """BB base: Rocks (7d) table, Mountains linkage, Driver field."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(fields={"Project name": "BB Rock"})

        create_project(
            config=_config,
            base_key="bb",
            name="BB Rock",
            description="Done when delivered",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Project name"] == "BB Rock"
        assert fields["Definition of Done"] == "Done when delivered"

    @patch("urllib.request.urlopen")
    def test_mountain_linkage(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="bb",
            name="Mountain-linked Rock",
            description="Done when linked",
            goal_id="recMOUNTAIN789",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Mountains"] == ["recMOUNTAIN789"]
        # Should NOT be in 1yr Goals (that's Personal)
        assert "1yr Goals" not in fields

    @patch("urllib.request.urlopen")
    def test_driver_set(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="bb",
            name="Driver Test",
            description="Done when tested",
            driver="pablo",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        # Pablo's BB record ID from people config
        assert fields["Driver"] == ["recQd0uiIifJAXXIM"]

    @patch("urllib.request.urlopen")
    def test_custom_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="bb",
            name="Status Test",
            description="Done when tested",
            status="in_progress",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Status"] == "In Progress"

    @patch("urllib.request.urlopen")
    def test_notes_field(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_project(
            config=_config,
            base_key="bb",
            name="Notes Test",
            description="Done when tested",
            notes="Created during routing. Source: inbox task.",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Notes"] == "Created during routing. Source: inbox task."
