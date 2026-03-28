"""Tests for notebooklm_delete.py — delete notebooks."""

from unittest.mock import MagicMock, patch

import notebooklm_delete


# ---------------------------------------------------------------------------
# _extract_notebook_id
# ---------------------------------------------------------------------------


class TestExtractNotebookId:
    """_extract_notebook_id parses notebook ID from URL."""

    def test_standard_url(self):
        url = "https://notebooklm.google.com/notebook/abc123"
        assert notebooklm_delete._extract_notebook_id(url) == "abc123"

    def test_returns_none_for_invalid(self):
        assert notebooklm_delete._extract_notebook_id("not-a-url") is None


# ---------------------------------------------------------------------------
# _find_notebook_card
# ---------------------------------------------------------------------------


class TestFindNotebookCard:
    """_find_notebook_card locates a card by notebook URL."""

    def test_finds_matching_card(self, mock_page: MagicMock):
        # Arrange
        card = MagicMock()
        card.get_attribute.return_value = "/notebook/abc123"
        cards_loc = MagicMock()
        cards_loc.count.return_value = 1
        cards_loc.nth.return_value = card
        mock_page.locator.return_value = cards_loc

        # Act
        result = notebooklm_delete._find_notebook_card(
            mock_page, "https://notebooklm.google.com/notebook/abc123"
        )

        # Assert
        assert result is card

    def test_returns_none_when_not_found(self, mock_page: MagicMock):
        # Arrange
        card = MagicMock()
        card.get_attribute.return_value = "/notebook/other-id"
        cards_loc = MagicMock()
        cards_loc.count.return_value = 1
        cards_loc.nth.return_value = card
        mock_page.locator.return_value = cards_loc

        # Act
        result = notebooklm_delete._find_notebook_card(
            mock_page, "https://notebooklm.google.com/notebook/abc123"
        )

        # Assert
        assert result is None

    def test_returns_none_for_invalid_url(self, mock_page: MagicMock):
        result = notebooklm_delete._find_notebook_card(mock_page, "not-a-url")
        assert result is None


# ---------------------------------------------------------------------------
# delete_notebook
# ---------------------------------------------------------------------------


class TestDeleteNotebook:
    """delete_notebook finds and deletes a notebook."""

    @patch("notebooklm_delete.click_with_fallback")
    @patch("notebooklm_delete._find_notebook_card")
    @patch("notebooklm_delete.get_browser_and_page")
    def test_deletes_notebook(self, mock_get_browser, mock_find, mock_click, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        card = MagicMock()
        more_btn = MagicMock()
        more_btn.count.return_value = 1
        card.locator.return_value = more_btn
        mock_find.return_value = card

        # Act
        result = notebooklm_delete.delete_notebook(
            notebook_url="https://notebooklm.google.com/notebook/abc123",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "deleted"
        assert result["notebook_id"] == "abc123"
        context.close.assert_called_once()

    @patch("notebooklm_delete._find_notebook_card")
    @patch("notebooklm_delete.get_browser_and_page")
    def test_not_found_returns_error(self, mock_get_browser, mock_find, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_find.return_value = None

        # Act
        result = notebooklm_delete.delete_notebook(
            notebook_url="https://notebooklm.google.com/notebook/abc123",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()
        context.close.assert_called_once()

    def test_invalid_url_returns_error(self):
        result = notebooklm_delete.delete_notebook(notebook_url="not-a-url")
        assert result["status"] == "error"

    @patch("notebooklm_delete.click_with_fallback", side_effect=Exception("fail"))
    @patch("notebooklm_delete._find_notebook_card")
    @patch("notebooklm_delete.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_find, mock_click, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        card = MagicMock()
        more_btn = MagicMock()
        more_btn.count.return_value = 0
        card.locator.return_value = more_btn
        mock_find.return_value = card

        # Act
        try:
            notebooklm_delete.delete_notebook(
                notebook_url="https://notebooklm.google.com/notebook/abc123",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()
