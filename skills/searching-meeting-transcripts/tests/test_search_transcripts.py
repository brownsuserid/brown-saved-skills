"""Tests for search_transcripts.py — Google Drive transcript search."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "scripts",
        "searching-meeting-transcripts",
    ),
)

import search_transcripts


# ---------------------------------------------------------------------------
# TestExtractDate
# ---------------------------------------------------------------------------


class TestExtractDate:
    """_extract_date() extracts dates from transcript titles."""

    def test_iso_date(self):
        assert (
            search_transcripts._extract_date("Transcript- 2026-02-12") == "2026-02-12"
        )

    def test_compact_date(self):
        assert search_transcripts._extract_date("Transcript-2025-12-11") == "2025-12-11"

    def test_us_date(self):
        assert search_transcripts._extract_date("Meeting 02/12/2026") == "2026-02-12"

    def test_no_date(self):
        assert search_transcripts._extract_date("Random file name") == ""

    def test_date_in_path(self):
        assert (
            search_transcripts._extract_date("Standup/Transcript-2026-01-09 notes")
            == "2026-01-09"
        )


class TestExtractMeetingName:
    """_extract_meeting_name() extracts meeting name from title."""

    def test_removes_transcript_suffix(self):
        result = search_transcripts._extract_meeting_name(
            "Weekly Standup/Transcript-2026-02-12"
        )
        assert result == "Weekly Standup"

    def test_plain_title(self):
        result = search_transcripts._extract_meeting_name("Just a Name")
        assert result == "Just a Name"


# ---------------------------------------------------------------------------
# TestSearchDrive
# ---------------------------------------------------------------------------


class TestSearchDrive:
    """search_drive() queries gog CLI for transcripts."""

    @patch("subprocess.run")
    def test_returns_matching_transcripts(self, mock_run):
        # Arrange
        files = [
            {
                "id": "doc1",
                "name": "Weekly/Transcript-2026-02-12",
                "mimeType": "application/vnd.google-apps.document",
                "parents": [search_transcripts.ACCOUNTS["aitb"]["folder_id"]],
            }
        ]
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(files), stderr=""
        )

        # Act
        result = search_transcripts.search_drive("aitb", "weekly", 10)

        # Assert
        assert len(result) == 1
        assert result[0]["account"] == "aitb"
        assert "docs.google.com" in result[0]["url"]

    @patch("subprocess.run")
    def test_filters_by_folder(self, mock_run):
        # Arrange — file not in transcript folder
        files = [
            {
                "id": "doc1",
                "name": "Notes",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["other-folder-id"],
            }
        ]
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(files), stderr=""
        )

        # Act
        result = search_transcripts.search_drive("aitb", "test", 10)

        # Assert
        assert len(result) == 0

    @patch("subprocess.run")
    def test_filters_non_docs(self, mock_run):
        # Arrange — PDF, not a Google Doc
        files = [
            {
                "id": "file1",
                "name": "Report.pdf",
                "mimeType": "application/pdf",
                "parents": [search_transcripts.ACCOUNTS["aitb"]["folder_id"]],
            }
        ]
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(files), stderr=""
        )

        # Act
        result = search_transcripts.search_drive("aitb", "report", 10)

        # Assert
        assert len(result) == 0

    @patch("subprocess.run")
    def test_gog_failure_returns_empty(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        # Act
        result = search_transcripts.search_drive("aitb", "test", 10)

        # Assert
        assert result == []

    @patch("subprocess.run")
    def test_timeout_returns_empty(self, mock_run):
        # Arrange
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gog", timeout=30)

        # Act
        result = search_transcripts.search_drive("bb", "test", 10)

        # Assert
        assert result == []

    @patch("subprocess.run")
    def test_respects_max_results(self, mock_run):
        # Arrange
        folder_id = search_transcripts.ACCOUNTS["aitb"]["folder_id"]
        files = [
            {
                "id": f"doc{i}",
                "name": f"Meeting {i}/Transcript-2026-01-{10 + i:02d}",
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id],
            }
            for i in range(5)
        ]
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(files), stderr=""
        )

        # Act
        result = search_transcripts.search_drive("aitb", "meeting", 2)

        # Assert
        assert len(result) <= 2


# ---------------------------------------------------------------------------
# TestSearchAll
# ---------------------------------------------------------------------------


class TestSearchAll:
    """search_all() searches across accounts."""

    @patch("search_transcripts.search_drive")
    def test_searches_both_accounts(self, mock_search):
        # Arrange
        mock_search.return_value = []

        # Act
        result = search_transcripts.search_all("test", account="both", max_results=5)

        # Assert
        assert mock_search.call_count == 2
        assert set(result["accounts_searched"]) == {"aitb", "bb"}

    @patch("search_transcripts.search_drive")
    def test_single_account(self, mock_search):
        # Arrange
        mock_search.return_value = []

        # Act
        result = search_transcripts.search_all("test", account="aitb", max_results=5)

        # Assert
        assert mock_search.call_count == 1
        assert result["accounts_searched"] == ["aitb"]

    @patch("search_transcripts.search_drive")
    def test_combined_results_sorted_by_date(self, mock_search):
        # Arrange
        mock_search.side_effect = [
            [{"date": "2026-02-10", "title": "Older"}],
            [{"date": "2026-02-15", "title": "Newer"}],
        ]

        # Act
        result = search_transcripts.search_all("test", account="both")

        # Assert
        assert result["transcripts"][0]["title"] == "Newer"
