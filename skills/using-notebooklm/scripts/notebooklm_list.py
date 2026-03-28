"""NotebookLM automation — list and search notebooks.

Usage:
    python3 notebooklm_list.py [--query "search term"] [--account name]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from notebooklm_browser import get_browser_and_page
from notebooklm_config import BASE_URL, SELECTORS


def _extract_notebook_id(url: str) -> str | None:
    """Extract notebook ID from a NotebookLM URL."""
    match = re.search(r"/notebook/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def _scrape_notebook_cards(page) -> list[dict]:
    """Scrape notebook cards from the home page."""
    notebooks: list[dict] = []

    for selector in SELECTORS["notebook_card"]:
        try:
            cards = page.locator(selector)
            count = cards.count()
            if count == 0:
                continue

            for i in range(count):
                card = cards.nth(i)
                href = card.get_attribute("href") or ""
                # Try to get the name from child elements
                name = ""
                for name_sel in SELECTORS["notebook_card_name"]:
                    try:
                        name_loc = card.locator(name_sel)
                        if name_loc.count() > 0:
                            name = name_loc.first.text_content() or ""
                            break
                    except Exception:
                        continue

                if not name:
                    name = card.text_content() or ""

                # Build full URL if relative
                if href and not href.startswith("http"):
                    href = f"{BASE_URL}{href}"

                notebook_id = _extract_notebook_id(href) if href else None

                notebooks.append(
                    {
                        "name": name.strip(),
                        "url": href,
                        "notebook_id": notebook_id,
                    }
                )

            if notebooks:
                break
        except Exception:
            continue

    return notebooks


def list_notebooks(
    query: str | None = None,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to home page, scrape notebook cards, optionally filter by query."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        notebooks = _scrape_notebook_cards(page)

        if query:
            q = query.lower()
            notebooks = [nb for nb in notebooks if q in nb["name"].lower()]

        return {"notebooks": notebooks, "count": len(notebooks)}
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="List NotebookLM notebooks")
    parser.add_argument(
        "--query", default=None, help="Filter by name (case-insensitive)"
    )
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--account", type=str, default=None, help="Named account")
    args = parser.parse_args()

    sf = Path(args.state_file) if args.state_file else None

    result = list_notebooks(
        query=args.query,
        headless=args.headless,
        state_file=sf,
        account=args.account,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
