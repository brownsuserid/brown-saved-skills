"""Tests for notebooklm_query.py — asking questions in notebooks."""

from unittest.mock import MagicMock, patch

import notebooklm_query


# ---------------------------------------------------------------------------
# wait_for_stable_response
# ---------------------------------------------------------------------------


class TestWaitForStableResponse:
    """wait_for_stable_response polls until text stabilizes."""

    def test_returns_after_consecutive_identical_readings(self, mock_page: MagicMock):
        # Arrange — locator returns same text every time
        locator = MagicMock()
        locator.count.return_value = 1
        locator.last.text_content.return_value = "stable answer"
        mock_page.locator.return_value = locator

        # Act
        result = notebooklm_query.wait_for_stable_response(
            mock_page, checks=3, interval_ms=0
        )

        # Assert
        assert result == "stable answer"

    @patch("notebooklm_query.time.sleep")
    def test_waits_for_text_to_stabilize(self, mock_sleep, mock_page: MagicMock):
        # Arrange — text changes then stabilizes
        # Use a counter-based function since locator is called multiple times per loop
        responses = iter(
            [
                "partial...",
                "partial answer",
                "final answer",
                "final answer",
                "final answer",
            ]
        )
        current = {"val": ""}

        def next_text():
            try:
                current["val"] = next(responses)
            except StopIteration:
                pass
            return current["val"]

        locator = MagicMock()
        locator.count.return_value = 1
        locator.last.text_content = next_text
        mock_page.locator.return_value = locator

        # Act
        result = notebooklm_query.wait_for_stable_response(
            mock_page, checks=3, interval_ms=10
        )

        # Assert
        assert result == "final answer"

    @patch("notebooklm_query.time.sleep")
    def test_returns_last_text_on_timeout(self, mock_sleep, mock_page: MagicMock):
        # Arrange — text never stabilizes (always changes)
        locator = MagicMock()
        locator.count.return_value = 1
        counter = {"i": 0}

        def changing_text():
            counter["i"] += 1
            return f"text-{counter['i']}"

        locator.last.text_content = changing_text
        mock_page.locator.return_value = locator

        # Act — will hit the upper bound
        result = notebooklm_query.wait_for_stable_response(
            mock_page, checks=3, interval_ms=0
        )

        # Assert — returns whatever was last
        assert result.startswith("text-")


# ---------------------------------------------------------------------------
# get_cited_sources
# ---------------------------------------------------------------------------


class TestGetCitedSources:
    """get_cited_sources extracts citations from the page."""

    def test_returns_citations(self, mock_page: MagicMock):
        # Arrange
        loc = MagicMock()
        loc.count.return_value = 2
        loc.nth.side_effect = [
            MagicMock(text_content=MagicMock(return_value="Source 1")),
            MagicMock(text_content=MagicMock(return_value="Source 2")),
        ]
        mock_page.locator.return_value = loc

        # Act
        result = notebooklm_query.get_cited_sources(mock_page)

        # Assert
        assert result == ["Source 1", "Source 2"]

    def test_returns_empty_list_when_no_citations(self, mock_page: MagicMock):
        # Arrange
        loc = MagicMock()
        loc.count.return_value = 0
        mock_page.locator.return_value = loc

        # Act
        result = notebooklm_query.get_cited_sources(mock_page)

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# ask_question
# ---------------------------------------------------------------------------


class TestAskQuestion:
    """ask_question navigates and asks questions."""

    @patch("notebooklm_query.get_cited_sources", return_value=["src1"])
    @patch("notebooklm_query.wait_for_stable_response", return_value="The answer")
    @patch("notebooklm_query.wait_for_any")
    @patch("notebooklm_query.click_with_fallback")
    @patch("notebooklm_query.fill_with_fallback")
    @patch("notebooklm_query.get_browser_and_page")
    def test_returns_answer(
        self,
        mock_get_browser,
        mock_fill,
        mock_click,
        mock_wait_any,
        mock_wait_stable,
        mock_sources,
        tmp_path,
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        result = notebooklm_query.ask_question(
            notebook_url="https://notebooklm.google.com/notebook/abc",
            question="What is X?",
            state_file=tmp_path / "s.json",
        )

        # Assert
        assert result["question"] == "What is X?"
        assert result["answer"] == "The answer"
        assert result["sources_cited"] == ["src1"]
        mock_fill.assert_called_with(page, "chat_input", "What is X?")
        context.close.assert_called_once()

    @patch("notebooklm_query.get_cited_sources", return_value=[])
    @patch("notebooklm_query.wait_for_stable_response", return_value="Answer")
    @patch("notebooklm_query.wait_for_any")
    @patch("notebooklm_query.click_with_fallback")
    @patch("notebooklm_query.fill_with_fallback", side_effect=Exception("fail"))
    @patch("notebooklm_query.get_browser_and_page")
    def test_closes_browser_on_error(
        self,
        mock_get_browser,
        mock_fill,
        mock_click,
        mock_wait_any,
        mock_wait_stable,
        mock_sources,
        tmp_path,
    ):
        # Arrange
        pw = MagicMock()
        context = MagicMock()
        page = MagicMock()
        mock_get_browser.return_value = (pw, context, context, page)

        # Act
        try:
            notebooklm_query.ask_question(
                notebook_url="https://notebooklm.google.com/notebook/abc",
                question="What?",
                state_file=tmp_path / "s.json",
            )
        except Exception:
            pass

        # Assert
        context.close.assert_called_once()
        pw.stop.assert_called_once()
