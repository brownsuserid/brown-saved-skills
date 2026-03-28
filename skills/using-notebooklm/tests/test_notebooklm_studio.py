"""Tests for notebooklm_studio.py — unified studio outputs."""

from unittest.mock import MagicMock, patch

import notebooklm_studio
from notebooklm_config import STUDIO_TYPES


# ---------------------------------------------------------------------------
# generate_studio_output
# ---------------------------------------------------------------------------


class TestGenerateStudioOutput:
    """generate_studio_output triggers generation for any studio type."""

    @patch("notebooklm_studio._wait_for_ready", return_value=True)
    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_returns_ready_for_video(
        self, mock_get_browser, mock_close, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_studio.generate_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="video",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "ready"
        assert result["output_type"] == "video"
        context.close.assert_called_once()

    @patch("notebooklm_studio._wait_for_ready", return_value=False)
    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_returns_generating_on_timeout(
        self, mock_get_browser, mock_close, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_studio.generate_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="report",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "generating"

    @patch("notebooklm_studio._wait_for_ready", return_value=True)
    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_includes_style_when_provided(
        self, mock_get_browser, mock_close, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_studio.generate_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="audio",
            style="deep_dive",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["style"] == "deep_dive"

    def test_unknown_type_returns_error(self):
        result = notebooklm_studio.generate_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="unknown_thing",
        )
        assert result["status"] == "error"

    @patch("notebooklm_studio._wait_for_ready", return_value=True)
    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_close, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        page.goto.side_effect = Exception("fail")

        # Act
        try:
            notebooklm_studio.generate_studio_output(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                output_type="video",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# check_studio_status
# ---------------------------------------------------------------------------


class TestCheckStudioStatus:
    """check_studio_status checks if output is ready/generating/not_started."""

    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_returns_not_started(self, mock_get_browser, mock_close, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        # All locator counts return 0
        loc = MagicMock()
        loc.count.return_value = 0
        loc.is_visible.return_value = False
        page.locator.return_value = loc

        # Act
        result = notebooklm_studio.check_studio_status(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="video",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "not_started"
        context.close.assert_called_once()

    def test_unknown_type_returns_error(self):
        result = notebooklm_studio.check_studio_status(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="unknown_thing",
        )
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# download_studio_output
# ---------------------------------------------------------------------------


class TestDownloadStudioOutput:
    """download_studio_output downloads generated outputs."""

    def test_unknown_type_returns_error(self):
        result = notebooklm_studio.download_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="unknown_thing",
            output_path="/tmp/out",
        )
        assert result["status"] == "error"

    def test_non_downloadable_returns_error(self):
        result = notebooklm_studio.download_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="mind_map",
            output_path="/tmp/out",
        )
        assert result["status"] == "error"
        assert "not downloadable" in result["message"]

    def test_flashcards_not_downloadable(self):
        result = notebooklm_studio.download_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="flashcards",
            output_path="/tmp/out",
        )
        assert result["status"] == "error"

    def test_quiz_not_downloadable(self):
        result = notebooklm_studio.download_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="quiz",
            output_path="/tmp/out",
        )
        assert result["status"] == "error"

    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.click_with_fallback")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_downloads_audio(self, mock_get_browser, mock_click, mock_close, tmp_path):
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
        result = notebooklm_studio.download_studio_output(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            output_type="audio",
            output_path=output,
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "downloaded"
        context.close.assert_called_once()

    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_closes_browser_on_error(self, mock_get_browser, mock_close, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        page.goto.side_effect = Exception("fail")

        # Act
        try:
            notebooklm_studio.download_studio_output(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                output_type="video",
                output_path="/tmp/out",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# list_studio_outputs
# ---------------------------------------------------------------------------


class TestListStudioOutputs:
    """list_studio_outputs returns status for all studio types."""

    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_returns_all_types(self, mock_get_browser, mock_close, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc

        # Act
        result = notebooklm_studio.list_studio_outputs(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert len(result["outputs"]) == len(STUDIO_TYPES)
        types = [o["type"] for o in result["outputs"]]
        assert "audio" in types
        assert "video" in types
        assert "mind_map" in types
        context.close.assert_called_once()

    @patch("notebooklm_studio._close_overlay_dialog")
    @patch("notebooklm_studio.get_browser_and_page")
    def test_includes_downloadable_flag(self, mock_get_browser, mock_close, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc

        # Act
        result = notebooklm_studio.list_studio_outputs(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert — mind_map should not be downloadable
        mind_map = next(o for o in result["outputs"] if o["type"] == "mind_map")
        assert mind_map["downloadable"] is False

        audio = next(o for o in result["outputs"] if o["type"] == "audio")
        assert audio["downloadable"] is True


# ---------------------------------------------------------------------------
# STUDIO_TYPES registry
# ---------------------------------------------------------------------------


class TestStudioTypes:
    """STUDIO_TYPES registry is well-formed."""

    def test_all_types_have_required_keys(self):
        for key, info in STUDIO_TYPES.items():
            assert "label" in info, f"{key} missing label"
            assert "ext" in info, f"{key} missing ext"
            assert "downloadable" in info, f"{key} missing downloadable"

    def test_nine_types_registered(self):
        assert len(STUDIO_TYPES) == 9

    def test_non_downloadable_have_no_ext(self):
        for key, info in STUDIO_TYPES.items():
            if not info["downloadable"]:
                assert info["ext"] is None, f"{key} is not downloadable but has ext"
