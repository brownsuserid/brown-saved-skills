"""Tests for notebooklm_sources.py — adding sources to notebooks."""

from unittest.mock import MagicMock, patch

import notebooklm_sources


# ---------------------------------------------------------------------------
# wait_for_ingestion
# ---------------------------------------------------------------------------


class TestWaitForIngestion:
    """wait_for_ingestion waits for spinner to appear then disappear."""

    def test_no_spinner_returns_quickly(self, mock_page: MagicMock):
        # Arrange — wait_for_selector raises (no spinner)
        mock_page.wait_for_selector.side_effect = Exception("no spinner")

        # Act — should not raise
        notebooklm_sources.wait_for_ingestion(mock_page)

    def test_waits_for_spinner_to_detach(self, mock_page: MagicMock):
        # Arrange — first call finds spinner, second waits for detach
        mock_page.wait_for_selector.side_effect = [None, None]

        # Act
        notebooklm_sources.wait_for_ingestion(mock_page)

        # Assert — called twice (attached, then detached)
        assert mock_page.wait_for_selector.call_count == 2


# ---------------------------------------------------------------------------
# add_source
# ---------------------------------------------------------------------------


class TestAddSource:
    """add_source adds different source types to a notebook."""

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_adds_website_source(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="website",
            value="https://example.com",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "added"
        assert result["source_type"] == "website"
        mock_fill.assert_any_call(page, "source_url_input", "https://example.com")
        context.close.assert_called_once()

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_adds_text_source(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="text",
            value="Some pasted content",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "added"
        assert result["source_type"] == "text"
        mock_fill.assert_any_call(page, "source_text_input", "Some pasted content")

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_adds_youtube_source(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="youtube",
            value="https://youtube.com/watch?v=xyz",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "added"
        assert result["source_type"] == "youtube"

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_adds_file_source(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Create a temp file to upload
        test_file = tmp_path / "doc.pdf"
        test_file.write_text("fake pdf")

        file_chooser = MagicMock()
        page.expect_file_chooser.return_value.__enter__ = MagicMock(
            return_value=MagicMock(value=file_chooser)
        )
        page.expect_file_chooser.return_value.__exit__ = MagicMock(return_value=False)

        # Act
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="file",
            value=str(test_file),
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "added"
        assert result["source_type"] == "file"

    def test_file_source_not_found_returns_error(self, tmp_path):
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="file",
            value="/nonexistent/file.pdf",
        )
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_adds_drive_source(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="drive",
            value="https://drive.google.com/file/d/abc123",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "added"
        assert result["source_type"] == "drive"
        mock_fill.assert_any_call(
            page, "source_drive_url_input", "https://drive.google.com/file/d/abc123"
        )

    def test_unknown_source_type_returns_error(self):
        result = notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="pdf",
            value="something",
        )
        assert result["status"] == "error"

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback")
    @patch("notebooklm_sources.get_browser_and_page")
    def test_sets_title_when_provided(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        notebooklm_sources.add_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_type="website",
            value="https://example.com",
            title="My Source",
            state_file=tmp_path / "s.json",
        )

        # Assert — fill called for url AND title
        fill_calls = [c for c in mock_fill.call_args_list]
        selector_keys = [c.args[1] for c in fill_calls]
        assert "source_title_input" in selector_keys

    @patch("notebooklm_sources.wait_for_ingestion")
    @patch("notebooklm_sources.fill_with_fallback")
    @patch("notebooklm_sources.click_with_fallback", side_effect=Exception("fail"))
    @patch("notebooklm_sources.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_click, mock_fill, mock_wait, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        try:
            notebooklm_sources.add_source(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                source_type="website",
                value="https://example.com",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()
