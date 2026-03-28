"""Tests for notebooklm_audio.py — audio generation, download, and status."""

from unittest.mock import MagicMock, patch


import notebooklm_audio


# ---------------------------------------------------------------------------
# _close_overlay_dialog / _open_audio_customize
# ---------------------------------------------------------------------------


class TestCloseOverlayDialog:
    """_close_overlay_dialog closes any open dialog overlay."""

    def test_does_not_raise_on_failure(self):
        page = MagicMock()
        page.click.side_effect = Exception("not found")
        # Should not raise
        notebooklm_audio._close_overlay_dialog(page)


class TestOpenAudioCustomize:
    """_open_audio_customize attempts to click the customize button."""

    @patch("notebooklm_audio.click_with_fallback")
    def test_clicks_customize(self, mock_click):
        page = MagicMock()
        notebooklm_audio._open_audio_customize(page)
        mock_click.assert_called_once()

    @patch("notebooklm_audio.click_with_fallback", side_effect=Exception("not found"))
    def test_does_not_raise_on_failure(self, mock_click):
        page = MagicMock()
        # Should not raise
        notebooklm_audio._open_audio_customize(page)


# ---------------------------------------------------------------------------
# _wait_for_audio_ready
# ---------------------------------------------------------------------------


class TestWaitForAudioReady:
    """_wait_for_audio_ready polls until play button appears."""

    @patch("notebooklm_audio.time.sleep")
    def test_returns_true_when_play_button_visible(self, mock_sleep):
        # Arrange
        page = MagicMock()
        loc = MagicMock()
        loc.is_visible.return_value = True
        page.locator.return_value = loc

        # Act
        result = notebooklm_audio._wait_for_audio_ready(page, timeout_ms=10_000)

        # Assert
        assert result is True

    @patch("notebooklm_audio.time.sleep")
    def test_returns_false_on_timeout(self, mock_sleep):
        # Arrange
        page = MagicMock()
        loc = MagicMock()
        loc.is_visible.return_value = False
        page.locator.return_value = loc

        # Act — small timeout so it finishes quickly
        result = notebooklm_audio._wait_for_audio_ready(page, timeout_ms=1000)

        # Assert
        assert result is False

    @patch("notebooklm_audio.time.sleep")
    def test_detects_when_spinner_disappears(self, mock_sleep):
        # Arrange — spinner visible first, then gone, then play button visible
        page = MagicMock()
        call_count = {"n": 0}

        def mock_is_visible():
            call_count["n"] += 1
            # After a few calls, return True (play button visible)
            return call_count["n"] > 6

        loc = MagicMock()
        loc.is_visible = mock_is_visible
        page.locator.return_value = loc

        # Act
        result = notebooklm_audio._wait_for_audio_ready(page, timeout_ms=60_000)

        # Assert
        assert result is True


# ---------------------------------------------------------------------------
# generate_audio
# ---------------------------------------------------------------------------


class TestGenerateAudio:
    """generate_audio triggers audio generation."""

    @patch("notebooklm_audio._wait_for_audio_ready", return_value=True)
    @patch("notebooklm_audio._open_audio_customize")
    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.click_with_fallback")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_returns_ready_status(
        self,
        mock_get_browser,
        mock_click,
        mock_close,
        mock_customize,
        mock_wait,
        tmp_path,
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_audio.generate_audio(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            style="deep_dive",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "ready"
        assert result["style"] == "deep_dive"
        context.close.assert_called_once()

    @patch("notebooklm_audio._wait_for_audio_ready", return_value=False)
    @patch("notebooklm_audio._open_audio_customize")
    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.click_with_fallback")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_returns_generating_on_timeout(
        self,
        mock_get_browser,
        mock_click,
        mock_close,
        mock_customize,
        mock_wait,
        tmp_path,
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_audio.generate_audio(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "generating"

    @patch("notebooklm_audio._wait_for_audio_ready", return_value=True)
    @patch("notebooklm_audio._open_audio_customize")
    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.click_with_fallback", side_effect=Exception("fail"))
    @patch("notebooklm_audio.get_browser_and_page")
    def test_closes_browser_on_error(
        self,
        mock_get_browser,
        mock_click,
        mock_close,
        mock_customize,
        mock_wait,
        tmp_path,
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        try:
            notebooklm_audio.generate_audio(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# download_audio
# ---------------------------------------------------------------------------


class TestDownloadAudio:
    """download_audio downloads generated audio."""

    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.click_with_fallback")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_downloads_via_button(
        self, mock_get_browser, mock_click, mock_open, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        download_mock = MagicMock()
        page.expect_download.return_value.__enter__ = MagicMock(
            return_value=MagicMock(value=download_mock)
        )
        page.expect_download.return_value.__exit__ = MagicMock(return_value=False)

        output = str(tmp_path / "audio.mp3")

        # Act
        result = notebooklm_audio.download_audio(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_path=output,
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "downloaded"
        context.close.assert_called_once()

    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.click_with_fallback")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_click, mock_open, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        page.expect_download.side_effect = Exception("no download")
        page.route = MagicMock()
        page.unroute = MagicMock()
        page.wait_for_timeout = MagicMock()

        loc = MagicMock()
        page.locator.return_value = loc

        output = str(tmp_path / "audio.mp3")

        # Act
        notebooklm_audio.download_audio(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_path=output,
            state_file=tmp_path / "s.json",
        )

        # Assert — should return error, not crash
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------


class TestCheckStatus:
    """check_status checks audio generation state."""

    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_ready_when_play_button_visible(
        self, mock_get_browser, mock_open, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        loc = MagicMock()
        loc.is_visible.return_value = True
        page.locator.return_value = loc

        # Act
        result = notebooklm_audio.check_status(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "ready"

    @patch("notebooklm_audio._close_overlay_dialog")
    @patch("notebooklm_audio.get_browser_and_page")
    def test_not_started_when_nothing_visible(
        self, mock_get_browser, mock_open, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        loc = MagicMock()
        loc.is_visible.return_value = False
        page.locator.return_value = loc

        # Act
        result = notebooklm_audio.check_status(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "not_started"
        context.close.assert_called_once()
