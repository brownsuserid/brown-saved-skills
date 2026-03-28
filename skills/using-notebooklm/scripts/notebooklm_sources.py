"""NotebookLM automation — add sources to a notebook.

Usage:
    python3 notebooklm_sources.py --notebook-url URL --type website --value "https://..."
    python3 notebooklm_sources.py --notebook-url URL --type text --value "paste content"
    python3 notebooklm_sources.py --notebook-url URL --type text --value-file /path/to/file.txt
    python3 notebooklm_sources.py --notebook-url URL --type youtube --value "https://youtube.com/..."
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from notebooklm_browser import (
    click_with_fallback,
    fill_with_fallback,
    get_browser_and_page,
)
from notebooklm_config import SELECTORS

SOURCE_TYPE_MAP = {
    "website": "source_type_website",
    "text": "source_type_text",
    "youtube": "source_type_youtube",
    "file": "source_type_file",
    "drive": "source_type_drive",
}


def wait_for_ingestion(page, timeout: int = 60_000) -> None:
    """Wait for source ingestion spinner to disappear."""
    spinners = SELECTORS["source_loading_spinner"]
    combined = ", ".join(spinners)
    try:
        page.wait_for_selector(combined, state="attached", timeout=5000)
    except Exception:
        return  # No spinner appeared — ingestion may have been instant

    # Now wait for spinner to disappear
    try:
        page.wait_for_selector(combined, state="detached", timeout=timeout)
    except Exception:
        pass  # Timed out waiting, continue anyway


def add_source(
    notebook_url: str,
    source_type: str,
    value: str,
    title: str | None = None,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Add a source to an existing notebook."""
    if source_type not in SOURCE_TYPE_MAP:
        return {"status": "error", "message": f"Unknown source type: {source_type}"}

    # Validate file exists before launching browser
    if source_type == "file" and not Path(value).exists():
        return {"status": "error", "message": f"File not found: {value}"}

    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        # Strip addSource param to start clean
        clean_url = notebook_url.split("?")[0]
        page.goto(clean_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Check if add-source dialog is already open (empty notebooks auto-open it)
        dialog_open = False
        try:
            overlay = page.locator(".cdk-overlay-backdrop-showing")
            if overlay.count() > 0:
                dialog_open = True
        except Exception:
            pass

        if not dialog_open:
            click_with_fallback(page, "add_source_button")
            page.wait_for_timeout(1000)

        # Select source type
        type_key = SOURCE_TYPE_MAP[source_type]
        click_with_fallback(page, type_key)
        page.wait_for_timeout(1000)

        # Fill in the value
        if source_type == "file":
            with page.expect_file_chooser() as fc_info:
                click_with_fallback(page, "source_upload_button", timeout=5000)
            file_chooser = fc_info.value
            file_chooser.set_files(value)
        elif source_type == "drive":
            fill_with_fallback(page, "source_drive_url_input", value)
        elif source_type in ("website", "youtube"):
            fill_with_fallback(page, "source_url_input", value)
        else:
            fill_with_fallback(page, "source_text_input", value)

        # Optionally set title
        if title:
            try:
                fill_with_fallback(page, "source_title_input", title, timeout=3000)
            except Exception:
                pass  # Title field may not be available

        # Submit
        click_with_fallback(page, "source_submit")

        # Wait for ingestion
        wait_for_ingestion(page)

        return {
            "status": "added",
            "source_type": source_type,
            "source_count": 1,
        }
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="Add source to a NotebookLM notebook")
    parser.add_argument("--notebook-url", required=True, help="Notebook URL")
    parser.add_argument(
        "--type",
        required=True,
        choices=["website", "text", "youtube", "file", "drive"],
        help="Source type",
    )
    parser.add_argument("--value", default=None, help="Source value (URL or text)")
    parser.add_argument("--value-file", default=None, help="Read value from file")
    parser.add_argument("--title", default=None, help="Optional source title")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--state-file", type=str, default=None)
    parser.add_argument("--account", type=str, default=None, help="Named account")
    args = parser.parse_args()

    if args.value_file:
        value = Path(args.value_file).read_text()
    elif args.value:
        value = args.value
    else:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Either --value or --value-file required",
                }
            )
        )
        raise SystemExit(1)

    sf = Path(args.state_file) if args.state_file else None

    result = add_source(
        notebook_url=args.notebook_url,
        source_type=args.type,
        value=value,
        title=args.title,
        headless=args.headless,
        state_file=sf,
        account=args.account,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
