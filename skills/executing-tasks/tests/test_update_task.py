"""Tests for update_task.py -- Airtable task PATCH updates."""

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

import update_task

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
# TestUpdateTask
# ---------------------------------------------------------------------------


class TestUpdateTask:
    """update_task() PATCHes Airtable with specified fields only."""

    @patch("urllib.request.urlopen")
    def test_updates_status(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {"Status": "In Progress"}}
        ).return_value

        # Act
        result = update_task.update_task(
            _config, "personal", "rec1", {"status": "in_progress"}
        )

        # Assert
        assert result["id"] == "rec1"
        req = mock_urlopen.call_args[0][0]
        assert req.method == "PATCH"

    @patch("urllib.request.urlopen")
    def test_updates_notes(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {"Notes": "Updated note"}}
        ).return_value

        # Act
        result = update_task.update_task(
            _config, "personal", "rec1", {"notes": "Updated note"}
        )

        # Assert
        assert result["id"] == "rec1"
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert "Notes" in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_updates_description(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(
            _config, "personal", "rec1", {"description": "New desc"}
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert "Definition of Done" in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_updates_assignee(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(_config, "personal", "rec1", {"assignee": "pablo"})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assignee_val = payload["fields"]["Assignee"]
        assert isinstance(assignee_val, list)
        assert assignee_val[0].startswith("rec")

    def test_cancelled_requires_force(self):
        # Act & Assert
        with pytest.raises(SystemExit):
            update_task.update_task(
                _config, "personal", "rec1", {"status": "cancelled"}
            )

    @patch("urllib.request.urlopen")
    def test_cancelled_with_force(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {"Status": "Cancelled"}}
        ).return_value

        # Act -- should NOT raise
        result = update_task.update_task(
            _config, "personal", "rec1", {"status": "cancelled"}, force=True
        )

        # Assert
        assert result["id"] == "rec1"

    def test_no_fields_exits(self):
        # Act & Assert
        with pytest.raises(SystemExit):
            update_task.update_task(_config, "personal", "rec1", {})

    @patch("urllib.request.urlopen")
    def test_semantic_status_translation(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(_config, "personal", "rec1", {"status": "complete"})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Status"] == "Completed"

    @patch("urllib.request.urlopen")
    def test_patch_only_specified_fields(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act -- only update notes
        update_task.update_task(_config, "personal", "rec1", {"notes": "Just notes"})

        # Assert -- payload should only contain Notes field
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert len(payload["fields"]) == 1
        assert "Notes" in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_updates_project(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(_config, "personal", "rec1", {"project": "recPROJ123"})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Project"] == ["recPROJ123"]

    @patch("urllib.request.urlopen")
    def test_updates_due_date(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(_config, "personal", "rec1", {"due": "2026-03-15"})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Due Date"] == "2026-03-15"

    @patch("urllib.request.urlopen")
    def test_updates_recurrence(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(_config, "personal", "rec1", {"recurrence": "Weekly"})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Recurrence"] == "Weekly"

    @patch("urllib.request.urlopen")
    def test_http_error_exits(self, mock_urlopen):
        # Arrange
        import urllib.error

        error_response = MagicMock()
        error_response.read.return_value = b'{"error": "Not found"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 404, "Not Found", {}, error_response
        )

        # Act & Assert
        with pytest.raises(SystemExit):
            update_task.update_task(
                _config, "personal", "rec1", {"status": "in_progress"}
            )

    @patch("urllib.request.urlopen")
    def test_generic_error_exits(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = Exception("Network error")

        # Act & Assert
        with pytest.raises(SystemExit):
            update_task.update_task(
                _config, "personal", "rec1", {"status": "in_progress"}
            )

    @patch("urllib.request.urlopen")
    def test_updates_depends_on(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(
            "personal", "rec1", {"depends_on": ["recDEP1", "recDEP2"]}
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Depends On"] == ["recDEP1", "recDEP2"]

    @patch("urllib.request.urlopen")
    def test_updates_depends_on_bb(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task("bb", "rec1", {"depends_on": ["recDEP3"]})

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["fields"]["Depends On"] == ["recDEP3"]

    @patch("urllib.request.urlopen")
    def test_multiple_fields_at_once(self, mock_urlopen):
        # Arrange
        mock_urlopen.return_value = _mock_urlopen_with_response(
            {"id": "rec1", "fields": {}}
        ).return_value

        # Act
        update_task.update_task(
            _config,
            "personal",
            "rec1",
            {
                "status": "in_progress",
                "notes": "Working on it",
                "due": "2026-03-20",
            },
        )

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert len(payload["fields"]) == 3
        assert "Status" in payload["fields"]
        assert "Notes" in payload["fields"]
        assert "Due Date" in payload["fields"]
