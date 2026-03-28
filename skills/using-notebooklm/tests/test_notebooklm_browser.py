"""Tests for notebooklm_browser.py — browser factory and helpers."""

from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import notebooklm_browser


# ---------------------------------------------------------------------------
# click_with_fallback
# ---------------------------------------------------------------------------


class TestClickWithFallback:
    """click_with_fallback tries selectors in order."""

    def test_succeeds_on_first_selector(self, mock_page: MagicMock):
        # Act
        notebooklm_browser.click_with_fallback(mock_page, "create_notebook")

        # Assert — called click with the first selector
        mock_page.click.assert_called_once()

    def test_falls_back_on_timeout(self, mock_page: MagicMock):
        # Arrange — first selector times out, second succeeds
        mock_page.click.side_effect = [
            PlaywrightTimeoutError("timeout"),
            None,
        ]

        # Act
        notebooklm_browser.click_with_fallback(mock_page, "create_notebook")

        # Assert
        assert mock_page.click.call_count == 2

    def test_raises_after_all_fail(self, mock_page: MagicMock):
        # Arrange — all selectors time out
        mock_page.click.side_effect = PlaywrightTimeoutError("timeout")

        # Act & Assert
        with pytest.raises(PlaywrightTimeoutError, match="All selectors failed"):
            notebooklm_browser.click_with_fallback(mock_page, "create_notebook")

    def test_invalid_key_raises_keyerror(self, mock_page: MagicMock):
        with pytest.raises(KeyError):
            notebooklm_browser.click_with_fallback(mock_page, "nonexistent_key")


# ---------------------------------------------------------------------------
# fill_with_fallback
# ---------------------------------------------------------------------------


class TestFillWithFallback:
    """fill_with_fallback tries selectors in order for text input."""

    def test_succeeds_on_first_selector(self, mock_page: MagicMock):
        # Act
        notebooklm_browser.fill_with_fallback(mock_page, "chat_input", "hello")

        # Assert
        mock_page.fill.assert_called_once()

    def test_falls_back_on_timeout(self, mock_page: MagicMock):
        # Arrange
        mock_page.fill.side_effect = [
            PlaywrightTimeoutError("timeout"),
            None,
        ]

        # Act
        notebooklm_browser.fill_with_fallback(mock_page, "chat_input", "hello")

        # Assert
        assert mock_page.fill.call_count == 2

    def test_raises_after_all_fail(self, mock_page: MagicMock):
        # Arrange
        mock_page.fill.side_effect = PlaywrightTimeoutError("timeout")

        # Act & Assert
        with pytest.raises(PlaywrightTimeoutError, match="All selectors failed"):
            notebooklm_browser.fill_with_fallback(mock_page, "chat_input", "hello")


# ---------------------------------------------------------------------------
# wait_for_any
# ---------------------------------------------------------------------------


class TestWaitForAny:
    """wait_for_any waits for any selector in the fallback list."""

    def test_returns_matched_selector(self, mock_page: MagicMock):
        # Act
        result = notebooklm_browser.wait_for_any(mock_page, "signed_in_indicator")

        # Assert
        mock_page.wait_for_selector.assert_called_once()
        assert isinstance(result, str)

    def test_raises_on_timeout(self, mock_page: MagicMock):
        # Arrange
        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("timeout")

        # Act & Assert
        with pytest.raises(PlaywrightTimeoutError, match="None of the selectors"):
            notebooklm_browser.wait_for_any(mock_page, "signed_in_indicator")


# ---------------------------------------------------------------------------
# human_type
# ---------------------------------------------------------------------------


class TestHumanType:
    """human_type types with per-character delays."""

    def test_clicks_then_types_each_char(self, mock_page: MagicMock):
        # Act
        notebooklm_browser.human_type(mock_page, "input.test", "hi")

        # Assert
        locator = mock_page.locator.return_value
        locator.click.assert_called_once()
        assert locator.press_sequentially.call_count == 2

    def test_empty_string_no_typing(self, mock_page: MagicMock):
        # Act
        notebooklm_browser.human_type(mock_page, "input.test", "")

        # Assert
        locator = mock_page.locator.return_value
        locator.click.assert_called_once()
        locator.press_sequentially.assert_not_called()


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------


class TestSaveState:
    """save_state persists storage state to disk."""

    def test_calls_storage_state(self, mock_context: MagicMock, tmp_path):
        # Arrange
        state_path = tmp_path / "state.json"

        # Act
        notebooklm_browser.save_state(mock_context, path=state_path)

        # Assert
        mock_context.storage_state.assert_called_once_with(path=str(state_path))

    def test_creates_parent_dirs(self, mock_context: MagicMock, tmp_path):
        # Arrange
        state_path = tmp_path / "subdir" / "state.json"

        # Act
        notebooklm_browser.save_state(mock_context, path=state_path)

        # Assert
        assert state_path.parent.exists()


# ---------------------------------------------------------------------------
# retry
# ---------------------------------------------------------------------------


class TestRetry:
    """retry wraps a callable with retries on specified exceptions."""

    def test_returns_on_first_success(self):
        # Arrange
        fn = MagicMock(return_value=42)

        # Act
        result = notebooklm_browser.retry(fn, max_retries=3)

        # Assert
        assert result == 42
        fn.assert_called_once()

    @patch("notebooklm_browser.time.sleep")
    def test_retries_on_timeout(self, mock_sleep):
        # Arrange
        fn = MagicMock(
            side_effect=[PlaywrightTimeoutError("fail"), 42],
        )

        # Act
        result = notebooklm_browser.retry(fn, max_retries=3, delay_seconds=0.5)

        # Assert
        assert result == 42
        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(0.5)

    @patch("notebooklm_browser.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        # Arrange
        fn = MagicMock(side_effect=PlaywrightTimeoutError("fail"))

        # Act & Assert
        with pytest.raises(PlaywrightTimeoutError):
            notebooklm_browser.retry(fn, max_retries=2)

        assert fn.call_count == 2

    def test_does_not_catch_unexpected_exceptions(self):
        # Arrange
        fn = MagicMock(side_effect=ValueError("unexpected"))

        # Act & Assert
        with pytest.raises(ValueError, match="unexpected"):
            notebooklm_browser.retry(fn, max_retries=3)


# ---------------------------------------------------------------------------
# get_browser_and_page
# ---------------------------------------------------------------------------


class TestGetBrowserAndPage:
    """get_browser_and_page launches Chrome with correct settings."""

    @patch("notebooklm_browser.sync_playwright")
    def test_launches_persistent_context(self, mock_sync_pw, tmp_path):
        # Arrange
        state_file = tmp_path / "state.json"
        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        page = MagicMock()
        page.set_default_timeout = MagicMock()
        ctx = MagicMock()
        ctx.pages = [page]
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        # Act
        result = notebooklm_browser.get_browser_and_page(
            headless=True, state_file=state_file
        )

        # Assert
        pw_instance.chromium.launch_persistent_context.assert_called_once()
        call_kwargs = pw_instance.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs["channel"] == "chrome"
        assert call_kwargs.kwargs["headless"] is True
        assert result[3] is page

    @patch("notebooklm_browser.sync_playwright")
    def test_creates_new_page_when_no_pages(self, mock_sync_pw, tmp_path):
        # Arrange
        state_file = tmp_path / "state.json"
        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        ctx = MagicMock()
        ctx.pages = []
        new_page = MagicMock()
        new_page.set_default_timeout = MagicMock()
        ctx.new_page.return_value = new_page
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        # Act
        result = notebooklm_browser.get_browser_and_page(
            headless=True, state_file=state_file
        )

        # Assert
        ctx.new_page.assert_called_once()
        assert result[3] is new_page

    @patch("notebooklm_browser.sync_playwright")
    def test_does_not_pass_storage_state(self, mock_sync_pw, tmp_path):
        # Arrange — persistent contexts manage state via user_data_dir
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pw_instance = MagicMock()
        mock_sync_pw.return_value.start.return_value = pw_instance
        ctx = MagicMock()
        page = MagicMock()
        page.set_default_timeout = MagicMock()
        ctx.pages = [page]
        pw_instance.chromium.launch_persistent_context.return_value = ctx

        # Act
        notebooklm_browser.get_browser_and_page(headless=True, state_file=state_file)

        # Assert — storage_state should NOT be in the call kwargs
        call_kwargs = pw_instance.chromium.launch_persistent_context.call_args
        assert "storage_state" not in call_kwargs.kwargs
