"""NotebookLM automation — delete a notebook.

Usage:
    python3 notebooklm_delete.py --notebook-url URL [--account name]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from notebooklm_browser import click_with_fallback, get_browser_and_page
from notebooklm_config import BASE_URL, SELECTORS


def _extract_notebook_id(url: str) -> str | None:
    """Extract notebook ID from a NotebookLM URL."""
    match = re.search(r"/notebook/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def _find_notebook_card(page, notebook_url: str):
    """Find the notebook card on the home page matching the given URL."""
    notebook_id = _extract_notebook_id(notebook_url)
    if not notebook_id:
        return None

    for selector in SELECTORS["notebook_card"]:
        try:
            cards = page.locator(selector)
            count = cards.count()
            for i in range(count):
                card = cards.nth(i)
                href = card.get_attribute("href") or ""
                if notebook_id in href:
                    return card
        except Exception:
            continue

    return None


def delete_notebook(
    notebook_url: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to home page, find notebook, and delete it."""
    notebook_id = _extract_notebook_id(notebook_url)
    if not notebook_id:
        return {"status": "error", "message": "Could not extract notebook ID from URL"}

    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        card = _find_notebook_card(page, notebook_url)
        if not card:
            return {
                "status": "error",
                "message": f"Notebook not found: {notebook_id}",
            }

        # Hover to reveal more menu, then click it
        card.hover()
        page.wait_for_timeout(500)

        # Click more menu on the card
        try:
            more_btn = card.locator(SELECTORS["notebook_more_menu"][0])
            if more_btn.count() > 0:
                more_btn.click()
            else:
                click_with_fallback(page, "notebook_more_menu")
        except Exception:
            click_with_fallback(page, "notebook_more_menu")

        page.wait_for_timeout(500)

        # Click delete
        click_with_fallback(page, "notebook_delete_option")
        page.wait_for_timeout(500)

        # Confirm deletion
        click_with_fallback(page, "notebook_delete_confirm")
        page.wait_for_timeout(2000)

        return {"status": "deleted", "notebook_id": notebook_id}
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="Delete a NotebookLM notebook")
    parser.add_argument("--notebook-url", required=True, help="Notebook URL to delete")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--account", type=str, default=None, help="Named account")
    args = parser.parse_args()

    sf = Path(args.state_file) if args.state_file else None

    result = delete_notebook(
        notebook_url=args.notebook_url,
        headless=args.headless,
        state_file=sf,
        account=args.account,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
