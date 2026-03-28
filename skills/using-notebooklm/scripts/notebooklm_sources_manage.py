"""NotebookLM automation — list and delete sources in a notebook.

Usage:
    python3 notebooklm_sources_manage.py list --notebook-url URL [--account name]
    python3 notebooklm_sources_manage.py delete --notebook-url URL --source-name "Title" [--account name]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from notebooklm_browser import click_with_fallback, get_browser_and_page
from notebooklm_config import SELECTORS


def _scrape_sources(page) -> list[dict]:
    """Scrape source items from the source panel sidebar."""
    sources: list[dict] = []

    for selector in SELECTORS["source_item"]:
        try:
            items = page.locator(selector)
            count = items.count()
            if count == 0:
                continue

            for i in range(count):
                item = items.nth(i)
                name = ""
                for name_sel in SELECTORS["source_item_name"]:
                    try:
                        name_loc = item.locator(name_sel)
                        if name_loc.count() > 0:
                            name = name_loc.first.text_content() or ""
                            break
                    except Exception:
                        continue

                if not name:
                    name = item.text_content() or ""

                sources.append({"name": name.strip(), "type": "unknown"})

            if sources:
                break
        except Exception:
            continue

    return sources


def list_sources(
    notebook_url: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to notebook and scrape the source panel."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        clean_url = notebook_url.split("?")[0]
        page.goto(clean_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        sources = _scrape_sources(page)
        return {"sources": sources, "count": len(sources)}
    finally:
        context.close()
        pw.stop()


def _find_source_by_name(page, source_name: str):
    """Find a source item element by its name."""
    for selector in SELECTORS["source_item"]:
        try:
            items = page.locator(selector)
            count = items.count()
            for i in range(count):
                item = items.nth(i)
                text = item.text_content() or ""
                if source_name.lower() in text.lower():
                    return item
        except Exception:
            continue
    return None


def delete_source(
    notebook_url: str,
    source_name: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to notebook, find a source by name, and delete it."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        clean_url = notebook_url.split("?")[0]
        page.goto(clean_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        source = _find_source_by_name(page, source_name)
        if not source:
            return {
                "status": "error",
                "message": f"Source not found: {source_name}",
            }

        # Hover to reveal menu
        source.hover()
        page.wait_for_timeout(500)

        # Click source menu
        try:
            menu_btn = source.locator(SELECTORS["source_item_menu"][0])
            if menu_btn.count() > 0:
                menu_btn.click()
            else:
                click_with_fallback(page, "source_item_menu")
        except Exception:
            click_with_fallback(page, "source_item_menu")

        page.wait_for_timeout(500)

        # Click delete
        click_with_fallback(page, "source_delete_option")
        page.wait_for_timeout(500)

        # Confirm
        click_with_fallback(page, "source_delete_confirm")
        page.wait_for_timeout(2000)

        return {"status": "deleted", "source_name": source_name}
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="Manage NotebookLM sources")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = subparsers.add_parser("list", help="List sources in a notebook")
    list_parser.add_argument("--notebook-url", required=True)
    list_parser.add_argument("--headless", action="store_true", default=True)
    list_parser.add_argument("--no-headless", dest="headless", action="store_false")
    list_parser.add_argument("--state-file", type=str, default=None)
    list_parser.add_argument("--account", type=str, default=None, help="Named account")

    # delete
    del_parser = subparsers.add_parser("delete", help="Delete a source from a notebook")
    del_parser.add_argument("--notebook-url", required=True)
    del_parser.add_argument(
        "--source-name", required=True, help="Source name to delete"
    )
    del_parser.add_argument("--headless", action="store_true", default=True)
    del_parser.add_argument("--no-headless", dest="headless", action="store_false")
    del_parser.add_argument("--state-file", type=str, default=None)
    del_parser.add_argument("--account", type=str, default=None, help="Named account")

    args = parser.parse_args()
    sf = Path(args.state_file) if args.state_file else None

    if args.command == "list":
        result = list_sources(
            notebook_url=args.notebook_url,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "delete":
        result = delete_source(
            notebook_url=args.notebook_url,
            source_name=args.source_name,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
