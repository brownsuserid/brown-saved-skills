"""NotebookLM automation — one-time login setup and state validation.

Usage:
    python3 notebooklm_auth.py                # Interactive login (headed)
    python3 notebooklm_auth.py --validate-only # Check if session is still valid
"""

from __future__ import annotations

import argparse
import json
import sys

from notebooklm_browser import (
    get_browser_and_page,
    save_state,
    wait_for_any,
)
from notebooklm_config import BASE_URL, SELECTORS, STATE_FILE


def is_signed_in(page) -> bool:
    """Check whether the current page shows a signed-in state."""
    for selector in SELECTORS["signed_in_indicator"]:
        if page.locator(selector).count() > 0:
            return True
    return False


def run_login(state_file=None, account: str | None = None):
    """Open headed Chrome, navigate to NotebookLM, wait for manual login."""
    state_file = state_file or STATE_FILE

    pw, _browser, context, page = get_browser_and_page(
        headless=False, state_file=state_file, account=account
    )

    try:
        page.goto(BASE_URL)
        print("Please sign in to your Google account in the browser window.")
        print("Waiting for sign-in to complete...")

        # Wait up to 5 minutes for user to complete login
        wait_for_any(page, "signed_in_indicator", timeout=300_000)

        save_state(context, path=state_file)
        print(json.dumps({"status": "authenticated", "state_file": str(state_file)}))
    finally:
        context.close()
        pw.stop()


def run_validate(state_file=None, account: str | None = None):
    """Load saved state and check if still signed in."""
    state_file = state_file or STATE_FILE

    if not state_file.exists():
        print(
            json.dumps(
                {
                    "status": "no_state",
                    "message": "No saved state found. Run auth first.",
                }
            )
        )
        sys.exit(1)

    pw, _browser, context, page = get_browser_and_page(
        headless=True, state_file=state_file, account=account
    )

    try:
        page.goto(BASE_URL)
        signed_in = is_signed_in(page)

        if signed_in:
            print(json.dumps({"status": "valid", "message": "Session is active."}))
        else:
            print(
                json.dumps(
                    {"status": "expired", "message": "Session expired. Re-run auth."}
                )
            )
            sys.exit(1)
    finally:
        context.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="NotebookLM authentication setup")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing session, don't open browser for login",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=None,
        help="Path to state file (default: ~/.openclaw/notebooklm-state.json)",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="Named account from ACCOUNTS registry",
    )
    args = parser.parse_args()

    from pathlib import Path

    state_file = Path(args.state_file) if args.state_file else None

    if args.validate_only:
        run_validate(state_file=state_file, account=args.account)
    else:
        run_login(state_file=state_file, account=args.account)


if __name__ == "__main__":
    main()
