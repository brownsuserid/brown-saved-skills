"""Tests for gather_reminders.py — macOS Reminders CLI parsing."""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "scripts",
        "generating-morning-briefing",
    ),
)

from gather_reminders import fetch_reminders


class TestFetchReminders:
    """fetch_reminders() parses remindctl CLI output."""

    @patch("subprocess.run")
    def test_parses_incomplete_reminders(self, mock_run):
        # Arrange
        output = (
            "[1] [ ] Buy groceries [Intuit]\n"
            "[2] [x] Already done [Intuit]\n"
            "[3] [ ] Write report [Intuit]\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        # Act
        result = fetch_reminders("Intuit")

        # Assert
        assert result["count"] == 2
        assert result["reminders"][0]["title"] == "Buy groceries"
        assert result["reminders"][1]["title"] == "Write report"

    @patch("subprocess.run")
    def test_empty_list(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Act
        result = fetch_reminders("Intuit")

        # Assert
        assert result["count"] == 0
        assert result["reminders"] == []

    @patch("subprocess.run")
    def test_remindctl_not_found(self, mock_run):
        # Arrange
        mock_run.side_effect = FileNotFoundError("remindctl not found")

        # Act
        result = fetch_reminders("Intuit")

        # Assert
        assert result["error"] == "remindctl not found"
        assert result["count"] == 0

    @patch("subprocess.run")
    def test_remindctl_timeout(self, mock_run):
        # Arrange
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="remindctl", timeout=30)

        # Act
        result = fetch_reminders("Intuit")

        # Assert
        assert result["error"] == "remindctl timed out"

    @patch("subprocess.run")
    def test_remindctl_failure(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="access denied"
        )

        # Act
        result = fetch_reminders("Intuit")

        # Assert
        assert "error" in result
        assert "access denied" in result["error"]

    @patch("subprocess.run")
    def test_list_name_passed_to_command(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Act
        fetch_reminders("Work")

        # Assert
        args = mock_run.call_args[0][0]
        assert args == ["remindctl", "list", "Work"]
