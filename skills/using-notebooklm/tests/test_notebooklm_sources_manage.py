"""Tests for notebooklm_sources_manage.py — list and delete sources."""

from unittest.mock import MagicMock, patch

import notebooklm_sources_manage


# ---------------------------------------------------------------------------
# _scrape_sources
# ---------------------------------------------------------------------------


class TestScrapeSources:
    """_scrape_sources extracts source info from the sidebar."""

    def test_returns_sources(self, mock_page: MagicMock):
        # Arrange
        item = MagicMock()
        name_loc = MagicMock()
        name_loc.count.return_value = 1
        name_loc.first.text_content.return_value = "My Source"
        item.locator.return_value = name_loc

        items_loc = MagicMock()
        items_loc.count.return_value = 1
        items_loc.nth.return_value = item
        mock_page.locator.return_value = items_loc

        # Act
        result = notebooklm_sources_manage._scrape_sources(mock_page)

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "My Source"

    def test_returns_empty_when_no_sources(self, mock_page: MagicMock):
        # Arrange
        loc = MagicMock()
        loc.count.return_value = 0
        mock_page.locator.return_value = loc

        # Act
        result = notebooklm_sources_manage._scrape_sources(mock_page)

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------


class TestListSources:
    """list_sources scrapes the source panel."""

    @patch("notebooklm_sources_manage._scrape_sources")
    @patch("notebooklm_sources_manage.get_browser_and_page")
    def test_returns_sources(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_scrape.return_value = [
            {"name": "Source 1", "type": "unknown"},
            {"name": "Source 2", "type": "unknown"},
        ]

        # Act
        result = notebooklm_sources_manage.list_sources(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["count"] == 2
        assert len(result["sources"]) == 2
        context.close.assert_called_once()

    @patch("notebooklm_sources_manage._scrape_sources", side_effect=Exception("fail"))
    @patch("notebooklm_sources_manage.get_browser_and_page")
    def test_closes_browser_on_error(self, mock_get_browser, mock_scrape, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        try:
            notebooklm_sources_manage.list_sources(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# _find_source_by_name
# ---------------------------------------------------------------------------


class TestFindSourceByName:
    """_find_source_by_name locates a source by name."""

    def test_finds_matching_source(self, mock_page: MagicMock):
        # Arrange
        item = MagicMock()
        item.text_content.return_value = "My Source Title"
        items_loc = MagicMock()
        items_loc.count.return_value = 1
        items_loc.nth.return_value = item
        mock_page.locator.return_value = items_loc

        # Act
        result = notebooklm_sources_manage._find_source_by_name(mock_page, "My Source")

        # Assert
        assert result is item

    def test_returns_none_when_not_found(self, mock_page: MagicMock):
        # Arrange
        item = MagicMock()
        item.text_content.return_value = "Other Source"
        items_loc = MagicMock()
        items_loc.count.return_value = 1
        items_loc.nth.return_value = item
        mock_page.locator.return_value = items_loc

        # Act
        result = notebooklm_sources_manage._find_source_by_name(
            mock_page, "Nonexistent"
        )

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# delete_source
# ---------------------------------------------------------------------------


class TestDeleteSource:
    """delete_source finds and removes a source."""

    @patch("notebooklm_sources_manage.click_with_fallback")
    @patch("notebooklm_sources_manage._find_source_by_name")
    @patch("notebooklm_sources_manage.get_browser_and_page")
    def test_deletes_source(self, mock_get_browser, mock_find, mock_click, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        source = MagicMock()
        menu_btn = MagicMock()
        menu_btn.count.return_value = 1
        source.locator.return_value = menu_btn
        mock_find.return_value = source

        # Act
        result = notebooklm_sources_manage.delete_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_name="My Source",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "deleted"
        assert result["source_name"] == "My Source"
        context.close.assert_called_once()

    @patch("notebooklm_sources_manage._find_source_by_name")
    @patch("notebooklm_sources_manage.get_browser_and_page")
    def test_source_not_found(self, mock_get_browser, mock_find, tmp_path):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        mock_find.return_value = None

        # Act
        result = notebooklm_sources_manage.delete_source(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            source_name="Missing",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @patch("notebooklm_sources_manage.click_with_fallback", side_effect=Exception("x"))
    @patch("notebooklm_sources_manage._find_source_by_name")
    @patch("notebooklm_sources_manage.get_browser_and_page")
    def test_closes_browser_on_error(
        self, mock_get_browser, mock_find, mock_click, tmp_path
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)
        source = MagicMock()
        menu_btn = MagicMock()
        menu_btn.count.return_value = 0
        source.locator.return_value = menu_btn
        mock_find.return_value = source

        # Act
        try:
            notebooklm_sources_manage.delete_source(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                source_name="My Source",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()
