"""NotebookLM automation — audio overview generation, download, and status.

Usage:
    python3 notebooklm_audio.py generate --notebook-url URL [--style deep_dive|summary]
    python3 notebooklm_audio.py download --notebook-url URL --output /path/to/file.mp3
    python3 notebooklm_audio.py status  --notebook-url URL
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from notebooklm_browser import (
    click_with_fallback,
    get_browser_and_page,
)
from notebooklm_config import AUDIO_GENERATION_TIMEOUT_MS, SELECTORS


def _close_overlay_dialog(page) -> None:
    """Close any overlay dialog (e.g., add source dialog on empty notebooks)."""
    try:
        page.click("button[aria-label='Close']", timeout=2000)
        page.wait_for_timeout(1000)
    except Exception:
        pass


def _open_audio_customize(page) -> None:
    """Open the Audio Overview customization dialog."""
    try:
        click_with_fallback(page, "audio_customize", timeout=5000)
    except Exception:
        pass  # Dialog may already be open


def _wait_for_audio_ready(page, timeout_ms: int = AUDIO_GENERATION_TIMEOUT_MS) -> bool:
    """Poll until audio play button appears or spinner disappears.

    Returns True if audio is ready, False on timeout.
    """
    poll_interval = 5  # seconds
    elapsed = 0

    while elapsed * 1000 < timeout_ms:
        # Check if play button is visible
        for selector in SELECTORS["audio_play_button"]:
            try:
                if page.locator(selector).is_visible():
                    return True
            except Exception:
                continue

        # Check if spinner is gone (generation finished)
        spinner_visible = False
        for selector in SELECTORS["audio_loading_spinner"]:
            try:
                if page.locator(selector).is_visible():
                    spinner_visible = True
                    break
            except Exception:
                continue

        if not spinner_visible and elapsed > 10:
            # No spinner and we've waited — check for play button one more time
            for selector in SELECTORS["audio_play_button"]:
                try:
                    if page.locator(selector).is_visible():
                        return True
                except Exception:
                    continue

        time.sleep(poll_interval)
        elapsed += poll_interval

    return False


def generate_audio(
    notebook_url: str,
    style: str = "deep_dive",
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Open notebook, configure style, and start audio generation."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)
        _open_audio_customize(page)

        # Select style if available
        style_key = f"audio_style_{style}"
        if style_key in SELECTORS:
            try:
                click_with_fallback(page, style_key, timeout=5000)
            except Exception:
                pass  # Style selection may not be available

        # Click Generate
        click_with_fallback(page, "audio_generate")

        # Wait for audio to be ready
        ready = _wait_for_audio_ready(page)

        status = "ready" if ready else "generating"
        return {
            "status": status,
            "notebook_url": notebook_url,
            "style": style,
        }
    finally:
        context.close()
        pw.stop()


def download_audio(
    notebook_url: str,
    output_path: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Navigate to notebook and download the generated audio."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        # Try More menu → Download
        try:
            click_with_fallback(page, "audio_more_menu", timeout=5000)
            page.wait_for_timeout(1000)
            with page.expect_download(timeout=30000) as download_info:
                click_with_fallback(page, "audio_download", timeout=5000)
            download = download_info.value
            download.save_as(output_path)
            return {
                "status": "downloaded",
                "output_path": output_path,
            }
        except Exception:
            pass

        # Fallback: intercept media URL on play click
        media_url = {"url": None}

        def handle_route(route):
            url = route.request.url
            if any(ext in url for ext in [".mp3", ".wav", ".ogg", "audio"]):
                media_url["url"] = url
            route.continue_()

        page.route("**/*", handle_route)

        try:
            click_with_fallback(page, "audio_play_button", timeout=10000)
            page.wait_for_timeout(3000)
        except Exception:
            pass

        page.unroute("**/*")

        if media_url["url"]:
            response = page.request.get(media_url["url"])
            Path(output_path).write_bytes(response.body())
            return {
                "status": "downloaded",
                "output_path": output_path,
            }

        return {
            "status": "error",
            "message": "Could not download audio. Try manual download.",
        }
    finally:
        context.close()
        pw.stop()


def check_status(
    notebook_url: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Check if audio has been generated for a notebook."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        # Check for play button (audio ready)
        for selector in SELECTORS["audio_play_button"]:
            try:
                if page.locator(selector).is_visible():
                    return {"status": "ready", "notebook_url": notebook_url}
            except Exception:
                continue

        # Check for generating indicator text
        for selector in SELECTORS["audio_generating_indicator"]:
            try:
                if page.locator(selector).is_visible():
                    return {"status": "generating", "notebook_url": notebook_url}
            except Exception:
                continue

        # Check for spinner (still generating)
        for selector in SELECTORS["audio_loading_spinner"]:
            try:
                if page.locator(selector).is_visible():
                    return {"status": "generating", "notebook_url": notebook_url}
            except Exception:
                continue

        return {"status": "not_started", "notebook_url": notebook_url}
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="NotebookLM audio operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate audio overview")
    gen_parser.add_argument("--notebook-url", required=True)
    gen_parser.add_argument(
        "--style", choices=["deep_dive", "summary"], default="deep_dive"
    )
    gen_parser.add_argument("--headless", action="store_true", default=True)
    gen_parser.add_argument("--no-headless", dest="headless", action="store_false")
    gen_parser.add_argument("--state-file", type=str, default=None)
    gen_parser.add_argument("--account", type=str, default=None, help="Named account")

    # download
    dl_parser = subparsers.add_parser("download", help="Download generated audio")
    dl_parser.add_argument("--notebook-url", required=True)
    dl_parser.add_argument("--output", required=True, help="Output file path")
    dl_parser.add_argument("--headless", action="store_true", default=True)
    dl_parser.add_argument("--no-headless", dest="headless", action="store_false")
    dl_parser.add_argument("--state-file", type=str, default=None)
    dl_parser.add_argument("--account", type=str, default=None, help="Named account")

    # status
    st_parser = subparsers.add_parser("status", help="Check audio generation status")
    st_parser.add_argument("--notebook-url", required=True)
    st_parser.add_argument("--headless", action="store_true", default=True)
    st_parser.add_argument("--no-headless", dest="headless", action="store_false")
    st_parser.add_argument("--state-file", type=str, default=None)
    st_parser.add_argument("--account", type=str, default=None, help="Named account")

    args = parser.parse_args()
    sf = Path(args.state_file) if args.state_file else None

    if args.command == "generate":
        result = generate_audio(
            notebook_url=args.notebook_url,
            style=args.style,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "download":
        result = download_audio(
            notebook_url=args.notebook_url,
            output_path=args.output,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "status":
        result = check_status(
            notebook_url=args.notebook_url,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
