"""Tests for gather_contacts.py — Beeper LinkedIn contact gathering."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "managing-outreach"),
)

import gather_contacts


# ---------------------------------------------------------------------------
# TestListAllLinkedInChats
# ---------------------------------------------------------------------------


class TestListAllLinkedInChats:
    """list_all_linkedin_chats() paginates through Beeper search_chats."""

    @patch("gather_contacts.call_beeper")
    def test_parses_chat_entries(self, mock_beeper):
        # Arrange
        output = (
            "## Alice Smith (chatID: !abc123:beeper.local)\n"
            "## Bob Jones (chatID: !def456:beeper.local)\n"
        )
        mock_beeper.return_value = output

        # Act
        chats = gather_contacts.list_all_linkedin_chats()

        # Assert
        assert len(chats) == 2
        assert chats[0]["name"] == "Alice Smith"
        assert chats[0]["chat_id"] == "!abc123:beeper.local"
        assert chats[1]["name"] == "Bob Jones"

    @patch("gather_contacts.call_beeper")
    def test_pagination_follows_cursor(self, mock_beeper):
        # Arrange
        page1 = (
            "## Alice (chatID: !abc:beeper.local)\n"
            "Next page (older): cursor='cursor1', direction='before'"
        )
        page2 = "## Bob (chatID: !def:beeper.local)\n"
        mock_beeper.side_effect = [page1, page2]

        # Act
        chats = gather_contacts.list_all_linkedin_chats()

        # Assert
        assert len(chats) == 2
        assert mock_beeper.call_count == 2

    @patch("gather_contacts.call_beeper")
    def test_deduplicates_by_chat_id(self, mock_beeper):
        # Arrange
        output = (
            "## Alice (chatID: !abc:beeper.local)\n"
            "## Alice (chatID: !abc:beeper.local)\n"
        )
        mock_beeper.return_value = output

        # Act
        chats = gather_contacts.list_all_linkedin_chats()

        # Assert
        assert len(chats) == 1

    @patch("gather_contacts.call_beeper")
    def test_beeper_failure_returns_empty(self, mock_beeper):
        # Arrange
        mock_beeper.return_value = None

        # Act
        chats = gather_contacts.list_all_linkedin_chats()

        # Assert
        assert chats == []

    @patch("gather_contacts.call_beeper")
    def test_empty_response(self, mock_beeper):
        # Arrange
        mock_beeper.return_value = ""

        # Act
        chats = gather_contacts.list_all_linkedin_chats()

        # Assert
        assert chats == []


class TestCallBeeper:
    """call_beeper() runs beeper-read.sh with proper args."""

    @patch("subprocess.run")
    def test_success(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        # Act
        result = gather_contacts.call_beeper(
            "search_chats", {"accountIDs": ["linkedin"]}
        )

        # Assert
        assert result == "output"

    @patch("subprocess.run")
    def test_failure_returns_none(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        # Act
        result = gather_contacts.call_beeper("search_chats", {})

        # Assert
        assert result is None

    @patch("subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        # Arrange
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="beeper", timeout=60)

        # Act
        result = gather_contacts.call_beeper("search_chats", {})

        # Assert
        assert result is None
