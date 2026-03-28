"""Tests for notebooklm_create.py — notebook creation."""

from unittest.mock import MagicMock, patch

import notebooklm_create


# ---------------------------------------------------------------------------
# extract_notebook_id
# ---------------------------------------------------------------------------


class TestExtractNotebookId:
    """extract_notebook_id parses notebook ID from URL."""

    def test_standard_url(self):
        url = "https://notebooklm.google.com/notebook/abc123-def_456"
        assert notebooklm_create.extract_notebook_id(url) == "abc123-def_456"

    def test_url_with_trailing_path(self):
        url = "https://notebooklm.google.com/notebook/abc123/sources"
        assert notebooklm_create.extract_notebook_id(url) == "abc123"

    def test_no_notebook_path(self):
        url = "https://notebooklm.google.com/"
        assert notebooklm_create.extract_notebook_id(url) is None

    def test_empty_string(self):
        assert notebooklm_create.extract_notebook_id("") is None


# ---------------------------------------------------------------------------
# create_notebook
# ---------------------------------------------------------------------------


class TestCreateNotebook:
    """create_notebook launches browser and creates a notebook."""

    @patch("notebooklm_create.fill_with_fallback")
    @patch("notebooklm_create.click_with_fallback")
    @patch("notebooklm_create.get_browser_and_page")
    def test_returns_notebook_info(
        self, mock_get_browser, mock_click, mock_fill, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        page.url = "https://notebooklm.google.com/notebook/new-id-123"
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_create.create_notebook(
            name="Test Notebook",
            headless=True,
            state_file=tmp_path / "state.json",
        )

        # Assert
        assert result["notebook_id"] == "new-id-123"
        assert result["name"] == "Test Notebook"
        assert "url" in result
        context.close.assert_called_once()
        pw.stop.assert_called_once()

    @patch("notebooklm_create.fill_with_fallback")
    @patch("notebooklm_create.click_with_fallback")
    @patch("notebooklm_create.get_browser_and_page")
    def test_navigates_to_base_url(
        self, mock_get_browser, mock_click, mock_fill, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        page.url = "https://notebooklm.google.com/notebook/abc"
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        notebooklm_create.create_notebook(name="Test", state_file=tmp_path / "s.json")

        # Assert
        page.goto.assert_called_once_with(notebooklm_create.BASE_URL)

    @patch("notebooklm_create.fill_with_fallback")
    @patch("notebooklm_create.click_with_fallback")
    @patch("notebooklm_create.get_browser_and_page")
    def test_clicks_create_notebook(
        self, mock_get_browser, mock_click, mock_fill, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        page.url = "https://notebooklm.google.com/notebook/abc"
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        notebooklm_create.create_notebook(name="Test", state_file=tmp_path / "s.json")

        # Assert
        mock_click.assert_called_with(page, "create_notebook")

    @patch("notebooklm_create.fill_with_fallback", side_effect=Exception("no input"))
    @patch("notebooklm_create.click_with_fallback")
    @patch("notebooklm_create.get_browser_and_page")
    def test_handles_missing_name_input(
        self, mock_get_browser, mock_click, mock_fill, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        page.url = "https://notebooklm.google.com/notebook/abc"
        mock_get_browser.return_value = (pw, context, context, page)

        # Act — should not raise despite fill failing
        result = notebooklm_create.create_notebook(
            name="Test", state_file=tmp_path / "s.json"
        )

        # Assert
        assert result["notebook_id"] == "abc"

    @patch("notebooklm_create.fill_with_fallback")
    @patch("notebooklm_create.click_with_fallback", side_effect=Exception("boom"))
    @patch("notebooklm_create.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_click, mock_fill, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act & Assert
        try:
            notebooklm_create.create_notebook(
                name="Test", state_file=tmp_path / "s.json"
            )
        except Exception:
            pass

        context.close.assert_called_once()
        pw.stop.assert_called_once()
