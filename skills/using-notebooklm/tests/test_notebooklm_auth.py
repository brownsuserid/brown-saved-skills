"""Tests for notebooklm_auth.py — authentication setup and validation."""

import json
from unittest.mock import MagicMock, patch

import pytest

import notebooklm_auth


# ---------------------------------------------------------------------------
# is_signed_in
# ---------------------------------------------------------------------------


class TestIsSignedIn:
    """is_signed_in checks page for signed-in indicators."""

    def test_returns_true_when_indicator_found(self, mock_page: MagicMock):
        # Arrange — locator.count() returns 1 (default from fixture)

        # Act
        result = notebooklm_auth.is_signed_in(mock_page)

        # Assert
        assert result is True

    def test_returns_false_when_no_indicator(self, mock_page: MagicMock):
        # Arrange — all locators return 0
        locator = MagicMock()
        locator.count.return_value = 0
        mock_page.locator.return_value = locator

        # Act
        result = notebooklm_auth.is_signed_in(mock_page)

        # Assert
        assert result is False

    def test_returns_true_on_second_indicator(self, mock_page: MagicMock):
        # Arrange — first indicator absent, second present
        loc_absent = MagicMock()
        loc_absent.count.return_value = 0
        loc_present = MagicMock()
        loc_present.count.return_value = 1
        mock_page.locator.side_effect = [loc_absent, loc_present]

        # Act
        result = notebooklm_auth.is_signed_in(mock_page)

        # Assert
        assert result is True


# ---------------------------------------------------------------------------
# run_login
# ---------------------------------------------------------------------------


class TestRunLogin:
    """run_login opens headed Chrome and saves state after login."""

    @patch("notebooklm_auth.save_state")
    @patch("notebooklm_auth.wait_for_any")
    @patch("notebooklm_auth.get_browser_and_page")
    def test_saves_state_after_login(
        self, mock_get_browser, mock_wait, mock_save, tmp_path, capsys
    ):
        # Arrange
        state_file = tmp_path / "state.json"
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        notebooklm_auth.run_login(state_file=state_file)

        # Assert
        mock_get_browser.assert_called_once_with(
            headless=False, state_file=state_file, account=None
        )
        page.goto.assert_called_once()
        mock_wait.assert_called_once()
        mock_save.assert_called_once_with(context, path=state_file)
        context.close.assert_called_once()
        pw.stop.assert_called_once()

        lines = capsys.readouterr().out.strip().splitlines()
        output = json.loads(lines[-1])
        assert output["status"] == "authenticated"

    @patch("notebooklm_auth.save_state")
    @patch("notebooklm_auth.wait_for_any", side_effect=Exception("timeout"))
    @patch("notebooklm_auth.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_wait, mock_save, tmp_path
    ):
        # Arrange
        state_file = tmp_path / "state.json"
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act & Assert
        with pytest.raises(Exception, match="timeout"):
            notebooklm_auth.run_login(state_file=state_file)

        # Browser still gets closed
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# run_validate
# ---------------------------------------------------------------------------


class TestRunValidate:
    """run_validate checks if saved session is still valid."""

    @patch("notebooklm_auth.is_signed_in", return_value=True)
    @patch("notebooklm_auth.get_browser_and_page")
    def test_valid_session(self, mock_get_browser, mock_signed_in, tmp_path, capsys):
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        notebooklm_auth.run_validate(state_file=state_file)

        # Assert
        output = json.loads(capsys.readouterr().out.strip())
        assert output["status"] == "valid"
        context.close.assert_called_once()

    @patch("notebooklm_auth.is_signed_in", return_value=False)
    @patch("notebooklm_auth.get_browser_and_page")
    def test_expired_session_exits(
        self, mock_get_browser, mock_signed_in, tmp_path, capsys
    ):
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act & Assert
        with pytest.raises(SystemExit):
            notebooklm_auth.run_validate(state_file=state_file)

        output = json.loads(capsys.readouterr().out.strip())
        assert output["status"] == "expired"

    def test_no_state_file_exits(self, tmp_path, capsys):
        # Arrange
        state_file = tmp_path / "nonexistent.json"

        # Act & Assert
        with pytest.raises(SystemExit):
            notebooklm_auth.run_validate(state_file=state_file)

        output = json.loads(capsys.readouterr().out.strip())
        assert output["status"] == "no_state"
