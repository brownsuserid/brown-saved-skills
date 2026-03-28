"""NotebookLM automation — create a new notebook.

Usage:
    python3 notebooklm_create.py --name "My Notebook" [--headless] [--state-file PATH]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from notebooklm_browser import (
    click_with_fallback,
    fill_with_fallback,
    get_browser_and_page,
)
from notebooklm_config import BASE_URL


def extract_notebook_id(url: str) -> str | None:
    """Extract notebook ID from a NotebookLM URL."""
    match = re.search(r"/notebook/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def create_notebook(
    name: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Create a new notebook and return its URL and ID."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        click_with_fallback(page, "create_notebook")
        page.wait_for_timeout(3000)

        # Try to set the notebook name
        try:
            fill_with_fallback(page, "notebook_name_input", name, timeout=5000)
        except Exception:
            pass  # Name input may not be immediately available

        # Wait for URL to contain /notebook/
        page.wait_for_url(re.compile(r"/notebook/"), timeout=15000)

        url = page.url
        notebook_id = extract_notebook_id(url)

        return {
            "notebook_id": notebook_id,
            "url": url,
            "name": name,
        }
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="Create a NotebookLM notebook")
    parser.add_argument("--name", required=True, help="Notebook name")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)",
    )
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--account", type=str, default=None, help="Named account")
    args = parser.parse_args()

    state_file = Path(args.state_file) if args.state_file else None

    result = create_notebook(
        name=args.name,
        headless=args.headless,
        state_file=state_file,
        account=args.account,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
