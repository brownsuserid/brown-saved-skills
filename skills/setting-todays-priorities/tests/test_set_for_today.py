"""Tests for set_for_today.py — validates record input and PATCH behavior."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "setting-todays-priorities"
    ),
)
SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")
sys.path.insert(0, SHARED_DIR)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(
    os.path.join(SHARED_DIR, "configs", "all.yaml")
)


from set_for_today import validate_record, update_for_today  # noqa: E402


def _mock_urlopen_with_response(data):
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


# ---------------------------------------------------------------------------
# TestValidateRecord
# ---------------------------------------------------------------------------


class TestValidateRecord:
    def test_valid_record_returns_none(self):
        record = {"id": "recABC123", "base": "personal", "value": True}
        assert validate_record(record, _test_config) is None

    def test_missing_id_returns_error(self):
        record = {"base": "personal", "value": True}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "id" in result.lower()

    def test_invalid_id_format_returns_error(self):
        record = {"id": "xyz123", "base": "personal", "value": True}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "rec" in result

    def test_missing_base_returns_error(self):
        record = {"id": "recABC123", "value": True}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "base" in result.lower()

    def test_invalid_base_returns_error(self):
        record = {"id": "recABC123", "base": "nonexistent", "value": True}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "nonexistent" in result

    def test_missing_value_returns_error(self):
        record = {"id": "recABC123", "base": "personal"}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "value" in result.lower()

    def test_non_bool_value_returns_error(self):
        record = {"id": "recABC123", "base": "personal", "value": "yes"}
        result = validate_record(record, _test_config)
        assert result is not None
        assert "true or false" in result.lower() or "bool" in result.lower()


# ---------------------------------------------------------------------------
# TestUpdateForToday
# ---------------------------------------------------------------------------


class TestUpdateForToday:
    @patch("urllib.request.urlopen")
    def test_sets_for_today_true(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = [
            _mock_urlopen_with_response(
                {"id": "recABC", "fields": {"For Today": True}}
            )()
        ]

        # Act
        update_for_today("recABC", "personal", True, _test_config)

        # Assert — verify PATCH payload
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert payload["fields"]["For Today"] is True

    @patch("urllib.request.urlopen")
    def test_sets_for_today_false(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = [
            _mock_urlopen_with_response(
                {"id": "recABC", "fields": {"For Today": False}}
            )()
        ]

        # Act
        update_for_today("recABC", "personal", False, _test_config)

        # Assert
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert payload["fields"]["For Today"] is False

    @patch("urllib.request.urlopen")
    def test_uses_correct_base_url(self, mock_urlopen):
        # Arrange
        base_cfg = airtable_config.get_base(_test_config, "personal")

        mock_urlopen.side_effect = [
            _mock_urlopen_with_response(
                {"id": "recXYZ", "fields": {"For Today": True}}
            )()
        ]

        # Act
        update_for_today("recXYZ", "personal", True, _test_config)

        # Assert — URL contains the personal base_id and tasks_table_id
        req = mock_urlopen.call_args[0][0]
        url = req.full_url
        assert base_cfg["base_id"] in url
        assert base_cfg["tasks_table_id"] in url
        assert "recXYZ" in url


# ---------------------------------------------------------------------------
# TestUpdateForTodayErrorHandling
# ---------------------------------------------------------------------------


class TestUpdateForTodayErrorHandling:
    @patch("urllib.request.urlopen")
    def test_http_error_propagates(self, mock_urlopen):
        # Arrange
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://api.airtable.com/v0/test",
            code=422,
            msg="Unprocessable Entity",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=b'{"error":"INVALID"}')),
        )

        # Act & Assert
        with pytest.raises(HTTPError):
            update_for_today("recBAD", "personal", True, _test_config)
