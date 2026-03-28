"""NotebookLM automation — ask questions and get answers.

Usage:
    python3 notebooklm_query.py --notebook-url URL --question "What is ...?" [--timeout 60]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from notebooklm_browser import (
    click_with_fallback,
    fill_with_fallback,
    get_browser_and_page,
    wait_for_any,
)
from notebooklm_config import (
    QUERY_STABILITY_CHECKS,
    QUERY_STABILITY_INTERVAL_MS,
    SELECTORS,
)


def wait_for_stable_response(
    page,
    checks: int = QUERY_STABILITY_CHECKS,
    interval_ms: int = QUERY_STABILITY_INTERVAL_MS,
) -> str:
    """Poll response text until it stabilizes (N consecutive identical readings)."""
    last_text = ""
    stable_count = 0

    for _ in range(checks * 10):  # Upper bound to prevent infinite loop
        selectors = SELECTORS["chat_response"]
        current_text = ""
        for selector in selectors:
            try:
                loc = page.locator(selector)
                if loc.count() > 0:
                    current_text = loc.last.text_content() or ""
                    break
            except Exception:
                continue

        if current_text and current_text == last_text:
            stable_count += 1
            if stable_count >= checks:
                return current_text
        else:
            stable_count = 0

        last_text = current_text
        time.sleep(interval_ms / 1000)

    return last_text


def get_cited_sources(page) -> list[str]:
    """Extract citation elements from the response."""
    sources = []
    for selector in SELECTORS["chat_sources_cited"]:
        try:
            loc = page.locator(selector)
            count = loc.count()
            for i in range(count):
                text = loc.nth(i).text_content()
                if text:
                    sources.append(text.strip())
            if sources:
                break
        except Exception:
            continue
    return sources


def ask_question(
    notebook_url: str,
    question: str,
    timeout: int = 60,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to notebook, ask a question, and return the answer."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        clean_url = notebook_url.split("?")[0]
        page.goto(clean_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Close any overlay dialog (e.g., add source dialog on empty notebooks)
        try:
            page.click("button[aria-label='Close']", timeout=2000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        # Type the question
        fill_with_fallback(page, "chat_input", question)

        # Submit
        click_with_fallback(page, "chat_submit")

        # Wait for response to appear and stabilize
        wait_for_any(page, "chat_response", timeout=timeout * 1000)
        answer = wait_for_stable_response(page)

        # Get cited sources
        sources = get_cited_sources(page)

        return {
            "question": question,
            "answer": answer,
            "sources_cited": sources,
        }
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="Ask a question in NotebookLM")
    parser.add_argument("--notebook-url", required=True, help="Notebook URL")
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument(
        "--timeout", type=int, default=60, help="Response timeout in seconds"
    )
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--account", type=str, default=None, help="Named account")
    args = parser.parse_args()

    sf = Path(args.state_file) if args.state_file else None

    result = ask_question(
        notebook_url=args.notebook_url,
        question=args.question,
        timeout=args.timeout,
        headless=args.headless,
        state_file=sf,
        account=args.account,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
