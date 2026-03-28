"""Tests for gamma.py — Gamma API CLI wrapper."""

import os
import sys
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GAMMA_API_KEY", "test-gamma-key")

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "scripts"),
)

import gamma


# ---------------------------------------------------------------------------
# TestPollGeneration
# ---------------------------------------------------------------------------


class TestPollGeneration:
    """poll_generation() polls until completion or timeout."""

    @patch("time.sleep")
    @patch("requests.get")
    def test_completed_immediately(self, mock_get, mock_sleep):
        # Arrange
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "completed", "url": "https://gamma.app/doc/1"},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        # Act
        result = gamma.poll_generation("gen-123", {"X-API-KEY": "test"})

        # Assert
        assert result["status"] == "completed"
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("requests.get")
    def test_polls_until_complete(self, mock_get, mock_sleep):
        # Arrange
        pending = MagicMock(
            status_code=200,
            json=lambda: {"status": "pending"},
        )
        pending.raise_for_status = MagicMock()
        completed = MagicMock(
            status_code=200,
            json=lambda: {"status": "completed", "url": "https://gamma.app/doc/1"},
        )
        completed.raise_for_status = MagicMock()
        mock_get.side_effect = [pending, pending, completed]

        # Act
        result = gamma.poll_generation("gen-123", {"X-API-KEY": "test"})

        # Assert
        assert result["status"] == "completed"
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    @patch("requests.get")
    def test_failed_generation_exits(self, mock_get, mock_sleep):
        # Arrange
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "failed", "error": "out of credits"},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        # Act & Assert
        with pytest.raises(SystemExit):
            gamma.poll_generation("gen-123", {"X-API-KEY": "test"})

    @patch("time.sleep")
    @patch("requests.get")
    def test_timeout_exits(self, mock_get, mock_sleep):
        # Arrange — always returns pending
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "pending"},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        # Act & Assert
        with pytest.raises(SystemExit):
            gamma.poll_generation("gen-123", {"X-API-KEY": "test"})


# ---------------------------------------------------------------------------
# TestCmdGenerate
# ---------------------------------------------------------------------------


class TestCmdGenerate:
    """cmd_generate() constructs and sends generation requests."""

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_basic_generation(self, mock_post, mock_poll):
        # Arrange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "gen-1"},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {
            "status": "completed",
            "url": "https://gamma.app/doc/1",
        }

        args = Namespace(
            text="Create a sales deck",
            text_file=None,
            format="presentation",
            text_mode="generate",
            num_cards=10,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as=None,
            json_pretty=False,
        )

        # Act
        gamma.cmd_generate(args)

        # Assert
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["inputText"] == "Create a sales deck"
        assert body["format"] == "presentation"

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_http_error_in_post(self, mock_post, mock_poll):
        # Arrange
        import requests

        resp = MagicMock()
        resp.status_code = 400
        resp.json.return_value = {"error": "bad request"}
        resp.text = "bad request"
        mock_post.return_value = resp
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError(
            response=resp
        )

        args = Namespace(
            text="test",
            text_file=None,
            format="presentation",
            text_mode="generate",
            num_cards=10,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as=None,
            json_pretty=False,
        )

        # Act & Assert
        with pytest.raises(requests.HTTPError):
            gamma.cmd_generate(args)


# ---------------------------------------------------------------------------
# TestCmdFromTemplate
# ---------------------------------------------------------------------------


class TestCmdFromTemplate:
    """cmd_from_template() generates from a Gamma template."""

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_sends_gamma_id(self, mock_post, mock_poll):
        # Arrange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "gen-1"},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {"status": "completed"}

        args = Namespace(
            gamma_id="template-abc",
            prompt="Customize for AI",
            export_as=None,
            theme_id=None,
            json_pretty=False,
        )

        # Act
        gamma.cmd_from_template(args)

        # Assert
        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get(
            "json"
        )
        assert body["gammaId"] == "template-abc"
        assert body["prompt"] == "Customize for AI"


# ---------------------------------------------------------------------------
# TestCmdThemesAndFolders
# ---------------------------------------------------------------------------


class TestCmdThemes:
    """cmd_themes() lists available themes."""

    @patch("requests.get")
    def test_lists_themes(self, mock_get):
        # Arrange
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"themes": [{"id": "t1", "name": "Modern"}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        args = Namespace(query=None, limit=None, json_pretty=False)

        # Act — should not raise
        gamma.cmd_themes(args)

        # Assert
        mock_get.assert_called_once()


class TestCmdFolders:
    """cmd_folders() lists folders."""

    @patch("requests.get")
    def test_lists_folders(self, mock_get):
        # Arrange
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"folders": [{"id": "f1", "name": "Sales"}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        args = Namespace(query="Sales", limit=10, json_pretty=False)

        # Act
        gamma.cmd_folders(args)

        # Assert
        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["query"] == "Sales"


# ---------------------------------------------------------------------------
# TestCmdGenerateOptionalParams
# ---------------------------------------------------------------------------


class TestCmdGenerateOptionalParams:
    """cmd_generate() includes optional params when provided."""

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_text_options_included(self, mock_post, mock_poll):
        # Arrange
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"id": "gen-1"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {"status": "completed"}

        args = Namespace(
            text="deck about AI",
            text_file=None,
            format="presentation",
            text_mode="generate",
            num_cards=8,
            card_split="auto",
            tone="professional",
            audience="investors",
            language="Spanish",
            amount="concise",
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as="pptx",
            json_pretty=False,
        )

        # Act
        gamma.cmd_generate(args)

        # Assert
        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get(
            "json"
        )
        assert body["textOptions"]["tone"] == "professional"
        assert body["textOptions"]["audience"] == "investors"
        assert body["textOptions"]["language"] == "Spanish"
        assert body["textOptions"]["amount"] == "concise"
        assert body["exportAs"] == "pptx"

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_image_options_included(self, mock_post, mock_poll):
        # Arrange
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"id": "gen-1"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {"status": "completed"}

        args = Namespace(
            text="visual deck",
            text_file=None,
            format="presentation",
            text_mode="generate",
            num_cards=5,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source="aiGenerated",
            image_model="imagen-4-pro",
            image_style="photorealistic",
            theme_id="theme-123",
            additional_instructions="Use blue color scheme",
            export_as=None,
            json_pretty=False,
        )

        # Act
        gamma.cmd_generate(args)

        # Assert
        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get(
            "json"
        )
        assert body["imageOptions"]["source"] == "aiGenerated"
        assert body["imageOptions"]["model"] == "imagen-4-pro"
        assert body["imageOptions"]["style"] == "photorealistic"
        assert body["themeId"] == "theme-123"
        assert body["additionalInstructions"] == "Use blue color scheme"


# ---------------------------------------------------------------------------
# TestCmdGenerateTextFile
# ---------------------------------------------------------------------------


class TestCmdGenerateTextFile:
    """cmd_generate() reads input from a file when --text-file is used."""

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_reads_from_file(self, mock_post, mock_poll, tmp_path):
        # Arrange
        content_file = tmp_path / "content.md"
        content_file.write_text("# My Presentation\nSlide content here.")

        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"id": "gen-1"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {"status": "completed"}

        args = Namespace(
            text=None,
            text_file=str(content_file),
            format="presentation",
            text_mode="condense",
            num_cards=5,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as=None,
            json_pretty=False,
        )

        # Act
        gamma.cmd_generate(args)

        # Assert
        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get(
            "json"
        )
        assert body["inputText"] == "# My Presentation\nSlide content here."
        assert body["textMode"] == "condense"

    def test_missing_file_exits(self):
        # Arrange
        args = Namespace(
            text=None,
            text_file="/nonexistent/path/content.md",
            format="presentation",
            text_mode="generate",
            num_cards=10,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as=None,
            json_pretty=False,
        )

        # Act & Assert
        with pytest.raises(SystemExit):
            gamma.cmd_generate(args)

    @patch("gamma.poll_generation")
    @patch("requests.post")
    def test_text_file_overrides_text(self, mock_post, mock_poll, tmp_path):
        # Arrange
        content_file = tmp_path / "override.md"
        content_file.write_text("File content wins")

        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"id": "gen-1"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_poll.return_value = {"status": "completed"}

        args = Namespace(
            text="This should be overridden",
            text_file=str(content_file),
            format="presentation",
            text_mode="generate",
            num_cards=10,
            card_split="auto",
            tone=None,
            audience=None,
            language=None,
            amount=None,
            image_source=None,
            image_model=None,
            image_style=None,
            theme_id=None,
            additional_instructions=None,
            export_as=None,
            json_pretty=False,
        )

        # Act
        gamma.cmd_generate(args)

        # Assert
        body = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get(
            "json"
        )
        assert body["inputText"] == "File content wins"


# ---------------------------------------------------------------------------
# TestCmdStatus
# ---------------------------------------------------------------------------


class TestCmdStatus:
    """cmd_status() checks generation status."""

    @patch("requests.get")
    def test_returns_status(self, mock_get):
        # Arrange
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "completed", "url": "https://gamma.app/doc/1"},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        args = Namespace(id="gen-123", json_pretty=False)

        # Act — should not raise
        gamma.cmd_status(args)

        # Assert
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "gen-123" in call_url
