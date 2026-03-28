#!/usr/bin/env python3
"""
Search Google Drive across all accounts or a specific one.

Supports full-text search, file type filtering, folder scoping, and
Drive query language for advanced queries.

Usage:
    # Search all 3 drives for "Q1 report"
    python3 search_drive.py "Q1 report"

    # Search only Brain Bridge drive
    python3 search_drive.py "invoice" --account bb

    # Search for spreadsheets only
    python3 search_drive.py "budget" --type spreadsheet

    # Search for recent files modified in the last 7 days
    python3 search_drive.py "notes" --recent 7

    # Raw Drive query language
    python3 search_drive.py "mimeType='application/pdf' and name contains 'contract'" --raw

    # Limit results per account
    python3 search_drive.py "proposal" --max 5

    # Search only My Drive (exclude shared drives)
    python3 search_drive.py "deck" --no-shared

Output:
    JSON with results grouped by account, plus a combined flat list.

After finding files, use gog to fetch contents:
    gog drive download <fileId> --account <email>
    gog docs export <fileId> --account <email> --format txt
    gog sheets get <fileId> --account <email>
    See: skills/using-gog/SKILL.md and references/full-command-reference.md
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta

from gog_config import get_account_labels, get_accounts, load_config

# Common MIME type shortcuts
MIME_TYPES = {
    "doc": "application/vnd.google-apps.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "spreadsheet": "application/vnd.google-apps.spreadsheet",
    "slides": "application/vnd.google-apps.presentation",
    "presentation": "application/vnd.google-apps.presentation",
    "pdf": "application/pdf",
    "folder": "application/vnd.google-apps.folder",
    "form": "application/vnd.google-apps.form",
    "image": "image/",
    "video": "video/",
}


def build_query(
    query: str, file_type: str | None, recent_days: int | None, raw: bool
) -> tuple[str, bool]:
    """Build the search query string. Returns (query, is_raw)."""
    if raw:
        return query, True

    parts = []

    if file_type and file_type in MIME_TYPES:
        mime = MIME_TYPES[file_type]
        if mime.endswith("/"):
            parts.append(f"mimeType contains '{mime}'")
        else:
            parts.append(f"mimeType='{mime}'")

    if recent_days:
        cutoff = (datetime.now() - timedelta(days=recent_days)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        parts.append(f"modifiedTime > '{cutoff}'")

    if parts:
        # Combine type/date filters with the text query using raw query mode
        parts.append(f"fullText contains '{query}'")
        return " and ".join(parts), True

    return query, False


def search_account(
    email: str,
    query: str,
    is_raw: bool,
    max_results: int,
    include_shared: bool,
    account_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Search a single Drive account via gog."""
    cmd = [
        "gog",
        "drive",
        "search",
        query,
        "--account",
        email,
        "--max",
        str(max_results),
        "--json",
        "--results-only",
    ]
    if is_raw:
        cmd.append("--raw-query")
    if not include_shared:
        cmd.append("--no-all-drives")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Warning: gog failed for {email}: {e}", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "no results" in stderr.lower() or not stderr:
            return []
        print(f"Warning: gog failed for {email}: {stderr}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        if not result.stdout.strip():
            return []
        print(f"Warning: Invalid JSON from gog for {email}", file=sys.stderr)
        return []

    # gog returns files as a list or under a key
    files = (
        data if isinstance(data, list) else data.get("files", data.get("results", []))
    )

    for f in files:
        f["_account"] = email
        f["_account_label"] = account_labels.get(email, email)

    return files


def main():
    # Pre-parse --config to load accounts for dynamic choices
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default=None)
    pre_args, _ = pre_parser.parse_known_args()

    config = load_config(pre_args.config)
    accounts = get_accounts(config)
    account_labels = get_account_labels(config)

    parser = argparse.ArgumentParser(description="Search Google Drive across accounts")
    parser.add_argument(
        "query", help="Search query (text or Drive query language with --raw)"
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: GOG_ACCOUNTS_CONFIG env var or configs/personal.yaml)",
    )
    parser.add_argument(
        "--account",
        "-a",
        choices=list(accounts.keys()) + list(accounts.values()),
        help="Search a specific account by label or email. Default: all.",
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=list(MIME_TYPES.keys()),
        help="Filter by file type: doc, sheet, slides, pdf, folder, form, image, video",
    )
    parser.add_argument(
        "--recent",
        "-r",
        type=int,
        metavar="DAYS",
        help="Only files modified in the last N days",
    )
    parser.add_argument(
        "--raw", action="store_true", help="Treat query as Drive query language"
    )
    parser.add_argument(
        "--max",
        "-m",
        type=int,
        default=10,
        help="Max results per account (default: 10)",
    )
    parser.add_argument(
        "--no-shared", action="store_true", help="Exclude shared drives (My Drive only)"
    )

    args = parser.parse_args()

    # Determine which accounts to search
    if args.account:
        email = accounts.get(args.account, args.account)
        accounts_to_search = [email]
    else:
        accounts_to_search = list(accounts.values())

    query, is_raw = build_query(args.query, args.type, args.recent, args.raw)

    by_account = {}
    all_files = []

    for email in accounts_to_search:
        label = account_labels.get(email, email)
        files = search_account(
            email, query, is_raw, args.max, not args.no_shared, account_labels
        )
        by_account[label] = {"account": email, "count": len(files), "files": files}
        all_files.extend(files)

    total = len(all_files)

    output = {
        "query": args.query,
        "total_results": total,
        "by_account": by_account,
        "all_files": all_files,
    }

    if total > 0:
        output["hint"] = (
            "To fetch file contents, use: "
            "gog drive download <fileId> --account <email> | "
            "gog docs export <fileId> --account <email> --format txt | "
            "gog sheets get <fileId> --account <email>. "
            "See skills/using-gog/SKILL.md for full reference."
        )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
