"""NotebookLM automation — unified studio outputs (generate/status/download/list).

Supports all 9 Studio types: audio, video, mind_map, report, flashcards,
quiz, infographic, slide_deck, data_table.

Usage:
    python3 notebooklm_studio.py generate --notebook-url URL --type video [--style explainer]
    python3 notebooklm_studio.py status --notebook-url URL --type video
    python3 notebooklm_studio.py download --notebook-url URL --type video --output /path/to/file
    python3 notebooklm_studio.py list --notebook-url URL
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from notebooklm_browser import click_with_fallback, get_browser_and_page
from notebooklm_config import SELECTORS, STUDIO_GENERATION_TIMEOUT_MS, STUDIO_TYPES


def _close_overlay_dialog(page) -> None:
    """Close any overlay dialog."""
    try:
        page.click("button[aria-label='Close']", timeout=2000)
        page.wait_for_timeout(1000)
    except Exception:
        pass


def _get_customize_selector(label: str) -> str:
    """Build the aria-label selector for a studio type's customize button."""
    return f"[aria-label='Customize {label}']"


def _get_ready_selector(label: str) -> str:
    """Build a selector to detect if a studio output is ready (has play/view button)."""
    return f"button[aria-label='Play']:near([aria-label*='{label}']), button:has-text('{label}'):near(button[aria-label='Play'])"


def _get_generating_selector(label: str) -> str:
    """Build a selector to detect if a studio output is currently generating."""
    return f"button:has-text('Generating {label}')"


def _wait_for_ready(
    page, output_type: str, timeout_ms: int = STUDIO_GENERATION_TIMEOUT_MS
) -> bool:
    """Poll until studio output is ready. Returns True if ready, False on timeout."""
    info = STUDIO_TYPES[output_type]
    label = info["label"]
    poll_interval = 5  # seconds
    elapsed = 0

    # For audio, use existing specific selectors
    if output_type == "audio":
        while elapsed * 1000 < timeout_ms:
            for selector in SELECTORS["audio_play_button"]:
                try:
                    if page.locator(selector).is_visible():
                        return True
                except Exception:
                    continue
            time.sleep(poll_interval)
            elapsed += poll_interval
        return False

    # Generic: look for any indication the output is ready
    ready_sel = _get_ready_selector(label)
    while elapsed * 1000 < timeout_ms:
        try:
            if page.locator(ready_sel).count() > 0:
                return True
        except Exception:
            pass

        # Also check if generating indicator disappeared after initial appearance
        gen_sel = _get_generating_selector(label)
        try:
            if elapsed > 10 and page.locator(gen_sel).count() == 0:
                return True
        except Exception:
            pass

        time.sleep(poll_interval)
        elapsed += poll_interval

    return False


def generate_studio_output(
    notebook_url: str,
    output_type: str,
    style: str | None = None,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
    timeout_ms: int = STUDIO_GENERATION_TIMEOUT_MS,
) -> dict:
    """Open notebook, configure and generate a studio output."""
    if output_type not in STUDIO_TYPES:
        return {"status": "error", "message": f"Unknown studio type: {output_type}"}

    info = STUDIO_TYPES[output_type]
    label = info["label"]

    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        # Click customize button for this output type
        customize_sel = _get_customize_selector(label)
        try:
            page.click(customize_sel, timeout=5000)
        except Exception:
            # For audio, fall back to known selectors
            if output_type == "audio":
                try:
                    click_with_fallback(page, "audio_customize", timeout=5000)
                except Exception:
                    pass

        # Select style if provided and audio
        if style and output_type == "audio":
            style_key = f"audio_style_{style}"
            if style_key in SELECTORS:
                try:
                    click_with_fallback(page, style_key, timeout=5000)
                except Exception:
                    pass

        # Click Generate
        try:
            page.click('button:has-text("Generate")', timeout=5000)
        except Exception:
            if output_type == "audio":
                click_with_fallback(page, "audio_generate")

        # Wait for output to be ready
        ready = _wait_for_ready(page, output_type, timeout_ms=timeout_ms)

        status = "ready" if ready else "generating"
        result = {
            "status": status,
            "notebook_url": notebook_url,
            "output_type": output_type,
        }
        if style:
            result["style"] = style
        return result
    finally:
        context.close()
        pw.stop()


def check_studio_status(
    notebook_url: str,
    output_type: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Check if a studio output is ready, generating, or not started."""
    if output_type not in STUDIO_TYPES:
        return {"status": "error", "message": f"Unknown studio type: {output_type}"}

    info = STUDIO_TYPES[output_type]
    label = info["label"]

    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        # Check for audio-specific selectors
        if output_type == "audio":
            for selector in SELECTORS["audio_play_button"]:
                try:
                    if page.locator(selector).is_visible():
                        return {"status": "ready", "output_type": output_type}
                except Exception:
                    continue

            for selector in SELECTORS["audio_generating_indicator"]:
                try:
                    if page.locator(selector).is_visible():
                        return {"status": "generating", "output_type": output_type}
                except Exception:
                    continue

        # Generic ready check
        ready_sel = _get_ready_selector(label)
        try:
            if page.locator(ready_sel).count() > 0:
                return {"status": "ready", "output_type": output_type}
        except Exception:
            pass

        # Generic generating check
        gen_sel = _get_generating_selector(label)
        try:
            if page.locator(gen_sel).count() > 0:
                return {"status": "generating", "output_type": output_type}
        except Exception:
            pass

        return {"status": "not_started", "output_type": output_type}
    finally:
        context.close()
        pw.stop()


def download_studio_output(
    notebook_url: str,
    output_type: str,
    output_path: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """Download a generated studio output."""
    if output_type not in STUDIO_TYPES:
        return {"status": "error", "message": f"Unknown studio type: {output_type}"}

    info = STUDIO_TYPES[output_type]
    if not info["downloadable"]:
        return {
            "status": "error",
            "message": f"{info['label']} is not downloadable",
        }

    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        # For audio, use existing specific download flow
        if output_type == "audio":
            try:
                click_with_fallback(page, "audio_more_menu", timeout=5000)
                page.wait_for_timeout(1000)
                with page.expect_download(timeout=30000) as download_info:
                    click_with_fallback(page, "audio_download", timeout=5000)
                download = download_info.value
                download.save_as(output_path)
                return {"status": "downloaded", "output_path": output_path}
            except Exception:
                return {
                    "status": "error",
                    "message": "Could not download audio. Try manual download.",
                }

        # Generic: find More menu near the output type label, then Download
        label = info["label"]
        try:
            more_sel = f"button[aria-label='More']:near(button:has-text('{label}'))"
            page.click(more_sel, timeout=5000)
            page.wait_for_timeout(1000)

            with page.expect_download(timeout=30000) as download_info:
                page.click('button:has-text("Download")', timeout=5000)
            download = download_info.value
            download.save_as(output_path)
            return {"status": "downloaded", "output_path": output_path}
        except Exception:
            return {
                "status": "error",
                "message": f"Could not download {label}. Try manual download.",
            }
    finally:
        context.close()
        pw.stop()


def list_studio_outputs(
    notebook_url: str,
    headless: bool = True,
    state_file: Path | None = None,
    account: str | None = None,
) -> dict:
    """List all studio output types and their current status."""
    pw, _browser, context, page = get_browser_and_page(
        headless=headless, state_file=state_file, account=account
    )

    try:
        page.goto(notebook_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        _close_overlay_dialog(page)

        outputs: list[dict] = []
        for type_key, info in STUDIO_TYPES.items():
            label = info["label"]
            status = "not_started"

            # Check if ready
            ready_sel = _get_ready_selector(label)
            try:
                if page.locator(ready_sel).count() > 0:
                    status = "ready"
            except Exception:
                pass

            # Check if generating
            if status == "not_started":
                gen_sel = _get_generating_selector(label)
                try:
                    if page.locator(gen_sel).count() > 0:
                        status = "generating"
                except Exception:
                    pass

            outputs.append(
                {
                    "type": type_key,
                    "label": label,
                    "status": status,
                    "downloadable": info["downloadable"],
                    "ext": info["ext"],
                }
            )

        return {"outputs": outputs}
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="NotebookLM studio operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    type_choices = list(STUDIO_TYPES.keys())

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate a studio output")
    gen_parser.add_argument("--notebook-url", required=True)
    gen_parser.add_argument("--type", required=True, choices=type_choices)
    gen_parser.add_argument("--style", default=None, help="Style (e.g., deep_dive)")
    gen_parser.add_argument("--headless", action="store_true", default=True)
    gen_parser.add_argument("--no-headless", dest="headless", action="store_false")
    gen_parser.add_argument("--state-file", type=str, default=None)
    gen_parser.add_argument("--account", type=str, default=None, help="Named account")

    # status
    st_parser = subparsers.add_parser("status", help="Check studio output status")
    st_parser.add_argument("--notebook-url", required=True)
    st_parser.add_argument("--type", required=True, choices=type_choices)
    st_parser.add_argument("--headless", action="store_true", default=True)
    st_parser.add_argument("--no-headless", dest="headless", action="store_false")
    st_parser.add_argument("--state-file", type=str, default=None)
    st_parser.add_argument("--account", type=str, default=None, help="Named account")

    # download
    dl_parser = subparsers.add_parser("download", help="Download a studio output")
    dl_parser.add_argument("--notebook-url", required=True)
    dl_parser.add_argument("--type", required=True, choices=type_choices)
    dl_parser.add_argument("--output", required=True, help="Output file path")
    dl_parser.add_argument("--headless", action="store_true", default=True)
    dl_parser.add_argument("--no-headless", dest="headless", action="store_false")
    dl_parser.add_argument("--state-file", type=str, default=None)
    dl_parser.add_argument("--account", type=str, default=None, help="Named account")

    # list
    ls_parser = subparsers.add_parser("list", help="List all studio outputs")
    ls_parser.add_argument("--notebook-url", required=True)
    ls_parser.add_argument("--headless", action="store_true", default=True)
    ls_parser.add_argument("--no-headless", dest="headless", action="store_false")
    ls_parser.add_argument("--state-file", type=str, default=None)
    ls_parser.add_argument("--account", type=str, default=None, help="Named account")

    args = parser.parse_args()
    sf = Path(args.state_file) if args.state_file else None

    if args.command == "generate":
        result = generate_studio_output(
            notebook_url=args.notebook_url,
            output_type=args.type,
            style=args.style,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "status":
        result = check_studio_status(
            notebook_url=args.notebook_url,
            output_type=args.type,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "download":
        result = download_studio_output(
            notebook_url=args.notebook_url,
            output_type=args.type,
            output_path=args.output,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )
    elif args.command == "list":
        result = list_studio_outputs(
            notebook_url=args.notebook_url,
            headless=args.headless,
            state_file=sf,
            account=args.account,
        )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
