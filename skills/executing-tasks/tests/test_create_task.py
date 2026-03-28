"""Tests for create_task.py -- Airtable task POST creation."""

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

from airtable_config import load_config

import create_task

# Load config once for all tests
_config = load_config()


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


# ---------------------------------------------------------------------------
# TestCreateTaskBasicFields
# ---------------------------------------------------------------------------


class TestCreateTaskBasicFields:
    """create_task() POSTs to Airtable with correct basic field mappings."""

    @patch("urllib.request.urlopen")
    def test_creates_task_with_title_only(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW1", "fields": {"Task": "Buy milk"}}
        ).return_value

        # Act
        result = create_task.create_task(_config, "personal", "Buy milk")

        # Assert
        assert result["id"] == "recNEW1"
        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        payload = json.loads(req.data)
        assert payload["fields"]["Task"] == "Buy milk"

    @patch("urllib.request.urlopen")
    def test_creates_task_with_all_fields(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW2", "fields": {}}
        ).return_value

        # Act
        result = create_task.create_task(
            _config,
            "personal",
            "Full task",
            description="Do the thing",
            assignee="aaron",
            project_id="recPROJ1",
            status="in_progress",
            due_date="2026-04-01",
            notes="Some notes",
        )

        # Assert
        assert result["id"] == "recNEW2"
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        fields = payload["fields"]
        assert fields["Task"] == "Full task"
        assert fields["Definition of Done"] == "Do the thing"
        assert fields["Assignee"] == ["recqfhZKB6O5C3No1"]
        assert fields["Project"] == ["recPROJ1"]
        assert fields["Status"] == "In Progress"
        assert fields["Due Date"] == "2026-04-01"
        assert fields["Notes"] == "Some notes"

    @patch("urllib.request.urlopen")
    def test_default_assignee_is_pablo(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW3", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(_config, "personal", "Default assignee task")

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Assignee"] == ["recVET2m8HSdXH15s"]

    @patch("urllib.request.urlopen")
    def test_default_status_is_not_started(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW4", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(_config, "personal", "Default status task")

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Status"] == "Not Started"


# ---------------------------------------------------------------------------
# TestCreateTaskOptionalFields
# ---------------------------------------------------------------------------


class TestCreateTaskOptionalFields:
    """Optional fields: for_today, recurrence, linked_task."""

    @patch("urllib.request.urlopen")
    def test_for_today_sets_checkbox(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW5", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(_config, "personal", "Urgent task", for_today=True)

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["For Today"] is True

    @patch("urllib.request.urlopen")
    def test_recurrence_sets_field(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW6", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(
            _config, "personal", "Weekly standup", recurrence="Weekly"
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Recurrence"] == "Weekly"

    @patch("urllib.request.urlopen")
    def test_linked_task_appends_to_notes(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW7", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(
            _config, "personal", "Follow-up task", linked_task="recORIG123"
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert "Follow-up from: recORIG123" in payload["fields"]["Notes"]

    @patch("urllib.request.urlopen")
    def test_linked_task_with_existing_notes(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW8", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(
            _config,
            "personal",
            "Follow-up task",
            notes="Existing context",
            linked_task="recORIG456",
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        notes_val = payload["fields"]["Notes"]
        assert "Existing context" in notes_val
        assert "Follow-up from: recORIG456" in notes_val


# ---------------------------------------------------------------------------
# TestCreateTaskDealLinking
# ---------------------------------------------------------------------------


class TestCreateTaskDealLinking:
    """Deal linking calls link_task_to_deal for bb/aitb bases only."""

    @patch("create_task.link_task_to_deal", return_value=True)
    @patch("urllib.request.urlopen")
    def test_deal_linking_for_bb_base(self, mock_urlopen, mock_link):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW9", "fields": {}}
        ).return_value

        # Act
        result = create_task.create_task(_config, "bb", "Deal task", deal_id="recDEAL1")

        # Assert
        mock_link.assert_called_once_with(_config, "bb", "recDEAL1", "recNEW9")
        assert result["_deal_linked"] is True

    @patch("create_task.link_task_to_deal")
    @patch("urllib.request.urlopen")
    def test_deal_linking_skipped_for_personal(self, mock_urlopen, mock_link):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW10", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(
            _config, "personal", "Personal task", deal_id="recDEAL2"
        )

        # Assert
        mock_link.assert_not_called()


# ---------------------------------------------------------------------------
# TestCreateTaskErrorHandling
# ---------------------------------------------------------------------------


class TestCreateTaskDependencies:
    """Depends On field sets linked record IDs."""

    @patch("urllib.request.urlopen")
    def test_depends_on_sets_field(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW11", "fields": {}}
        ).return_value

        # Act
        create_task.create_task(
            "personal", "Blocked task", depends_on=["recDEP1", "recDEP2"]
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Depends On"] == ["recDEP1", "recDEP2"]

    @patch("urllib.request.urlopen")
    def test_depends_on_single(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW12", "fields": {}}
        ).return_value

        # Act
        create_task.create_task("bb", "BB blocked task", depends_on=["recDEP3"])

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Depends On"] == ["recDEP3"]

    @patch("urllib.request.urlopen")
    def test_no_depends_on_omits_field(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "recNEW13", "fields": {}}
        ).return_value

        # Act
        create_task.create_task("personal", "Independent task")

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert "Depends On" not in payload["fields"]


class TestCreateTaskErrorHandling:
    """Error paths exit with code 1."""

    @patch("urllib.request.urlopen")
    def test_http_error_exits(self, mock_urlopen):
        # Arrange
        import urllib.error

        error_response = MagicMock()
        error_response.read.return_value = b'{"error": "Bad request"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 400, "Bad Request", {}, error_response
        )

        # Act & Assert
        with pytest.raises(SystemExit):
            create_task.create_task(_config, "personal", "Failing task")

    @patch("urllib.request.urlopen")
    def test_generic_error_exits(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = Exception("Network error")

        # Act & Assert
        with pytest.raises(SystemExit):
            create_task.create_task(_config, "personal", "Failing task")
