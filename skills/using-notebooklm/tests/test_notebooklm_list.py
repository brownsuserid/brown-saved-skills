"""Tests for notebooklm_list.py — list and search notebooks."""

from unittest.mock import MagicMock, patch

import notebooklm_list


# ---------------------------------------------------------------------------
# _extract_notebook_id
# ---------------------------------------------------------------------------


class TestExtractNotebookId:
    """_extract_notebook_id parses notebook ID from URL."""

    def test_standard_url(self):
        url = "https://notebooklm.google.com/notebook/abc123"
        assert notebooklm_list._extract_notebook_id(url) == "abc123"

    def test_no_notebook_path(self):
        assert (
            notebooklm_list._extract_notebook_id("https://notebooklm.google.com/")
            is None
        )

    def test_empty_string(self):
        assert notebooklm_list._extract_notebook_id("") is None


# ---------------------------------------------------------------------------
# _scrape_notebook_cards
# ---------------------------------------------------------------------------


class TestScrapeNotebookCards:
    """_scrape_notebook_cards extracts notebook info from page."""

    def test_returns_notebooks_from_cards(self, mock_page: MagicMock):
        # Arrange
        card = MagicMock()
        card.get_attribute.return_value = "/notebook/abc123"
        name_loc = MagicMock()
        name_loc.count.return_value = 1
        name_loc.first.text_content.return_value = "My Notebook"
        card.locator.return_value = name_loc

        cards_loc = MagicMock()
        cards_loc.count.return_value = 1
        cards_loc.nth.return_value = card
        mock_page.locator.return_value = cards_loc

        # Act
        result = notebooklm_list._scrape_notebook_cards(mock_page)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "My Notebook"
        assert result[0]["notebook_id"] == "abc123"

    def test_returns_empty_when_no_cards(self, mock_page: MagicMock):
        # Arrange
        loc = MagicMock()
        loc.count.return_value = 0
        mock_page.locator.return_value = loc

        # Act
        result = notebooklm_list._scrape_notebook_cards(mock_page)

        # Assert
        assert result == []

    def test_handles_card_without_href(self, mock_page: MagicMock):
        # Arrange
        card = MagicMock()
        card.get_attribute.return_value = ""
        card.text_content.return_value = "Untitled"
        name_loc = MagicMock()
        name_loc.count.return_value = 0
        card.locator.return_value = name_loc

        cards_loc = MagicMock()
        cards_loc.count.return_value = 1
        cards_loc.nth.return_value = card
        mock_page.locator.return_value = cards_loc

        # Act
        result = notebooklm_list._scrape_notebook_cards(mock_page)

        # Assert
        assert len(result) == 1
        assert result[0]["notebook_id"] is None


# ---------------------------------------------------------------------------
# list_notebooks
# ---------------------------------------------------------------------------


class TestListNotebooks:
    """list_notebooks scrapes and optionally filters notebooks."""

    @patch("notebooklm_list._scrape_notebook_cards")
    @patch("notebooklm_list.get_browser_and_page")
    def test_returns_all_notebooks(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_scrape.return_value = [
            {"name": "NB1", "url": "u1", "notebook_id": "id1"},
            {"name": "NB2", "url": "u2", "notebook_id": "id2"},
        ]

        # Act
        result = notebooklm_list.list_notebooks(state_file=tmp_path / "s.json")

        # Assert
        assert result["count"] == 2
        assert len(result["notebooks"]) == 2
        context.close.assert_called_once()

    @patch("notebooklm_list._scrape_notebook_cards")
    @patch("notebooklm_list.get_browser_and_page")
    def test_filters_by_query(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_scrape.return_value = [
            {"name": "AI Research", "url": "u1", "notebook_id": "id1"},
            {"name": "Meeting Notes", "url": "u2", "notebook_id": "id2"},
        ]

        # Act
        result = notebooklm_list.list_notebooks(
            query="research", state_file=tmp_path / "s.json"
        )

        # Assert
        assert result["count"] == 1
        assert result["notebooks"][0]["name"] == "AI Research"

    @patch("notebooklm_list._scrape_notebook_cards")
    @patch("notebooklm_list.get_browser_and_page")
    def test_query_is_case_insensitive(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_scrape.return_value = [
            {"name": "AI RESEARCH", "url": "u1", "notebook_id": "id1"},
        ]

        # Act
        result = notebooklm_list.list_notebooks(
            query="research", state_file=tmp_path / "s.json"
        )

        # Assert
        assert result["count"] == 1

    @patch("notebooklm_list._scrape_notebook_cards")
    @patch("notebooklm_list.get_browser_and_page")
    def test_empty_results(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_scrape.return_value = []

        # Act
        result = notebooklm_list.list_notebooks(state_file=tmp_path / "s.json")

        # Assert
        assert result["count"] == 0
        assert result["notebooks"] == []

    @patch("notebooklm_list._scrape_notebook_cards", side_effect=Exception("fail"))
    @patch("notebooklm_list.get_browser_and_page")
    def test_closes_browser_on_error(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        try:
            notebooklm_list.list_notebooks(state_file=tmp_path / "s.json")
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()
