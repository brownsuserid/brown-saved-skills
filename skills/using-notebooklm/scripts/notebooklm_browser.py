"""NotebookLM automation — shared browser factory and helpers."""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Callable, TypeVar

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from notebooklm_config import (
    DEFAULT_TIMEOUT_MS,
    SELECTORS,
    STATE_FILE,
    TYPING_DELAY_MAX_MS,
    TYPING_DELAY_MIN_MS,
    VIEWPORT,
    get_account_config,
)

T = TypeVar("T")


def get_browser_and_page(
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> tuple[Playwright, Browser, BrowserContext, Page]:
    """Launch Chrome with anti-detection flags and optional saved state.

    Resolution order for paths: explicit *state_file* > *account* lookup > default.

    Returns (playwright, browser, context, page) tuple.
    Caller is responsible for closing playwright when done.
    """
    acct = get_account_config(account)
    profile_dir = acct["profile_dir"]
    state_file = state_file or acct["state_file"]

    pw = sync_playwright().start()

    launch_args = [
        "--disable-blink-features=AutomationControlled",
    ]

    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        channel="chrome",
        headless=headless,
        args=launch_args,
        viewport=VIEWPORT,
    )

    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)

    return pw, context, context, page  # browser=context for persistent contexts


def click_with_fallback(
    page: Page,
    selector_key: str,
    timeout: int = DEFAULT_TIMEOUT_MS,
) -> None:
    """Try each selector in SELECTORS[selector_key] until one succeeds."""
    selectors = SELECTORS[selector_key]
    last_error: Exception | None = None

    per_selector_timeout = max(timeout // len(selectors), 2000)

    for selector in selectors:
        try:
            page.click(selector, timeout=per_selector_timeout)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc
            continue

    raise PlaywrightTimeoutError(
        f"All selectors failed for '{selector_key}': {selectors}"
    ) from last_error


def fill_with_fallback(
    page: Page,
    selector_key: str,
    text: str,
    timeout: int = DEFAULT_TIMEOUT_MS,
) -> None:
    """Try each selector in SELECTORS[selector_key] for fill(), until one works."""
    selectors = SELECTORS[selector_key]
    last_error: Exception | None = None

    per_selector_timeout = max(timeout // len(selectors), 2000)

    for selector in selectors:
        try:
            page.fill(selector, text, timeout=per_selector_timeout)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc
            continue

    raise PlaywrightTimeoutError(
        f"All selectors failed for '{selector_key}': {selectors}"
    ) from last_error


def wait_for_any(
    page: Page,
    selector_key: str,
    timeout: int = DEFAULT_TIMEOUT_MS,
) -> str:
    """Wait until any selector in SELECTORS[selector_key] appears. Returns the matched selector."""
    selectors = SELECTORS[selector_key]
    # Build a combined selector using Playwright's comma-separated matching
    combined = ", ".join(selectors)
    try:
        page.wait_for_selector(combined, timeout=timeout)
    except PlaywrightTimeoutError:
        raise PlaywrightTimeoutError(
            f"None of the selectors appeared for '{selector_key}': {selectors}"
        )
    # Return whichever selector is actually visible
    for selector in selectors:
        if page.locator(selector).count() > 0:
            return selector
    return selectors[0]


def human_type(page: Page, selector: str, text: str) -> None:
    """Type text with random per-character delays to mimic human input."""
    locator = page.locator(selector)
    locator.click()
    for char in text:
        locator.press_sequentially(
            char,
            delay=random.randint(TYPING_DELAY_MIN_MS, TYPING_DELAY_MAX_MS),
        )


def save_state(context: BrowserContext, path: Path | None = None) -> None:
    """Persist browser storage state to disk."""
    path = path or STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(path))


def retry(
    fn: Callable[..., T],
    max_retries: int = 3,
    delay_seconds: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (PlaywrightTimeoutError,),
) -> T:
    """Retry a callable up to max_retries times on specified exceptions."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except exceptions as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(delay_seconds)
    raise last_error  # type: ignore[misc]
