"""Tests for gather_roadmap_context.py — ensures roadmap query and output work correctly."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0, str(os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))
)
sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "drafting-pr-faqs"
        )
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from gather_roadmap_context import build_filter, search_roadmap  # noqa: E402


def _make_airtable_response(records: list[dict]) -> bytes:
    """Build a fake Airtable API response body."""
    return json.dumps({"records": records}).encode()


def _make_record(
    record_id: str = "rec123",
    feature: str = "AI Teammates",
    status: str = "In Progress",
    priority: str = "High",
    definition_of_done: str = "Ship v1",
    notes: str = "Core product feature",
    product: str = "Brain Bridge Platform",
    dependencies: str = "",
) -> dict:
    """Build a fake Airtable roadmap record."""
    return {
        "id": record_id,
        "fields": {
            "Feature": feature,
            "Status": status,
            "Priority": priority,
            "Definition of Done": definition_of_done,
            "Notes": notes,
            "Product": product,
            "Dependencies": dependencies,
        },
    }


class TestBuildFilter:
    """build_filter() produces correct Airtable formula."""

    def test_searches_feature_and_notes(self):
        formula = build_filter("AI Teammates")
        assert "FIND(LOWER('AI Teammates'), LOWER({Feature}))" in formula
        assert "FIND(LOWER('AI Teammates'), LOWER({Notes}))" in formula

    def test_escapes_single_quotes(self):
        formula = build_filter("it's here")
        assert "it\\'s here" in formula

    def test_or_wrapper(self):
        formula = build_filter("test")
        assert formula.startswith("OR(")


class TestSearchRoadmap:
    """search_roadmap() returns structured roadmap items."""

    @patch("urllib.request.urlopen")
    def test_returns_all_fields(self, mock_urlopen):
        # Arrange
        record = _make_record()
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_roadmap("AI Teammates", 10, _test_config)

        # Assert
        assert len(results) == 1
        item = results[0]
        assert item["feature"] == "AI Teammates"
        assert item["status"] == "In Progress"
        assert item["priority"] == "High"
        assert item["definition_of_done"] == "Ship v1"
        assert item["notes"] == "Core product feature"
        assert item["product"] == "Brain Bridge Platform"
        assert "airtable_url" in item
        assert "rec123" in item["airtable_url"]

    @patch("urllib.request.urlopen")
    def test_missing_fields_default_to_empty_string(self, mock_urlopen):
        # Arrange
        record = {"id": "rec456", "fields": {"Feature": "Bare feature"}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([record])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        results = search_roadmap("Bare", 10, _test_config)

        # Assert
        assert results[0]["status"] == ""
        assert results[0]["notes"] == ""
        assert results[0]["priority"] == ""

    @patch("urllib.request.urlopen")
    def test_http_error_returns_empty_list(self, mock_urlopen):
        # Arrange
        import urllib.error

        error_response = MagicMock()
        error_response.read.return_value = b'{"error": "Bad request"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 400, "Bad Request", {}, error_response
        )

        # Act
        results = search_roadmap("test", 10, _test_config)

        # Assert
        assert results == []

    @patch("urllib.request.urlopen")
    def test_generic_error_returns_empty_list(self, mock_urlopen):
        # Arrange
        mock_urlopen.side_effect = Exception("Network timeout")

        # Act
        results = search_roadmap("test", 10, _test_config)

        # Assert
        assert results == []

    @patch("urllib.request.urlopen")
    def test_respects_max_records(self, mock_urlopen):
        # Arrange
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response([])
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # Act
        search_roadmap("test", 5, _test_config)

        # Assert
        call_args = mock_urlopen.call_args[0][0]
        assert "maxRecords=5" in call_args.full_url
