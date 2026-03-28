"""Shared fixtures for NotebookLM tests."""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add scripts dir to path so imports work like they do at runtime.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "scripts"),
)


@pytest.fixture()
def mock_page() -> MagicMock:
    """A configured Playwright Page mock with locator chains."""
    page = MagicMock()
    page.set_default_timeout = MagicMock()

    # locator() returns a mock whose .count() defaults to 1
    locator = MagicMock()
    locator.count.return_value = 1
    locator.text_content.return_value = "some text"
    page.locator.return_value = locator
    return page


@pytest.fixture()
def mock_context() -> MagicMock:
    """A configured Playwright BrowserContext mock."""
    context = MagicMock()
    context.pages = []
    new_page = MagicMock()
    new_page.set_default_timeout = MagicMock()
    context.new_page.return_value = new_page
    context.storage_state = MagicMock()
    return context


@pytest.fixture()
def mock_playwright(
    mock_context: MagicMock,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Returns (pw, browser, context, page) tuple with mocked Playwright."""
    pw = MagicMock()
    page = MagicMock()
    page.set_default_timeout = MagicMock()
    mock_context.pages = [page]
    pw.chromium.launch_persistent_context.return_value = mock_context
    return pw, mock_context, mock_context, page
