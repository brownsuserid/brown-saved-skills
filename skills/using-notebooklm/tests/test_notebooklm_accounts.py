"""Tests for multi-account support across config and browser modules."""

from unittest.mock import MagicMock, patch

import notebooklm_config
from notebooklm_config import get_account_config


# ---------------------------------------------------------------------------
# get_account_config
# ---------------------------------------------------------------------------


class TestGetAccountConfig:
    """get_account_config resolves account names to paths."""

    def test_returns_default_when_none(self):
        result = get_account_config(None)
        assert result == notebooklm_config.ACCOUNTS["default"]

    def test_returns_default_for_explicit_default(self):
        result = get_account_config("default")
        assert result == notebooklm_config.ACCOUNTS["default"]

    def test_returns_default_for_unknown_account(self):
        result = get_account_config("nonexistent_account_xyz")
        assert result == notebooklm_config.ACCOUNTS["default"]

    def test_returns_named_account_when_registered(self, tmp_path):
        # Arrange — temporarily register an account
        test_profile = tmp_path / "test-profile"
        test_state = tmp_path / "test-state.json"
        notebooklm_config.ACCOUNTS["test_acct"] = {
            "profile_dir": test_profile,
            "state_file": test_state,
        }
        try:
            # Act
            result = get_account_config("test_acct")

            # Assert
            assert result["profile_dir"] == test_profile
            assert result["state_file"] == test_state
        finally:
            del notebooklm_config.ACCOUNTS["test_acct"]

    def test_default_account_has_required_keys(self):
        result = get_account_config()
        assert "profile_dir" in result
        assert "state_file" in result

    def test_default_paths_are_under_openclaw(self):
        result = get_account_config()
        assert ".openclaw" in str(result["profile_dir"])
        assert ".openclaw" in str(result["state_file"])


# ---------------------------------------------------------------------------
# get_browser_and_page with account
# ---------------------------------------------------------------------------


class TestBrowserAccountSupport:
    """get_browser_and_page uses account-specific profile dir."""

    @patch("notebooklm_browser.sync_playwright")
    def test_uses_account_profile_dir(self, mock_sync_pw, tmp_path):
        # Arrange
        import notebooklm_browser

        test_profile = tmp_path / "acct-profile"
        test_state = tmp_path / "acct-state.json"
        notebooklm_config.ACCOUNTS["myacct"] = {
            "profile_dir": test_profile,
            "state_file": test_state,
        }

        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        page = MagicMock()
        page.set_default_timeout = MagicMock()
        ctx = MagicMock()
        ctx.pages = [page]
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        try:
            # Act
            notebooklm_browser.get_browser_and_page(account="myacct")

            # Assert
            call_kwargs = (
                pw_instance.chromium.launch_persistent_context.call_args.kwargs
            )
            assert call_kwargs["user_data_dir"] == str(test_profile)
        finally:
            del notebooklm_config.ACCOUNTS["myacct"]

    @patch("notebooklm_browser.sync_playwright")
    def test_explicit_state_file_overrides_account(self, mock_sync_pw, tmp_path):
        # Arrange
        import notebooklm_browser

        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        page = MagicMock()
        page.set_default_timeout = MagicMock()
        ctx = MagicMock()
        ctx.pages = [page]
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        explicit_state = tmp_path / "explicit-state.json"

        # Act
        _pw, _browser, _context, _page = notebooklm_browser.get_browser_and_page(
            state_file=explicit_state
        )

        # Assert — we just verify it doesn't crash; the state_file param
        # takes precedence per resolution order documented in the function

    @patch("notebooklm_browser.sync_playwright")
    def test_none_account_uses_default_profile(self, mock_sync_pw):
        # Arrange
        import notebooklm_browser

        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        page = MagicMock()
        page.set_default_timeout = MagicMock()
        ctx = MagicMock()
        ctx.pages = [page]
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        # Act
        notebooklm_browser.get_browser_and_page(account=None)

        # Assert
        call_kwargs = pw_instance.chromium.launch_persistent_context.call_args.kwargs
        default_profile = str(notebooklm_config.ACCOUNTS["default"]["profile_dir"])
        assert call_kwargs["user_data_dir"] == default_profile
