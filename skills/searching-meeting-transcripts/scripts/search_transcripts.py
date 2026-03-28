#!/usr/bin/env python3
"""
Search Google Meet transcripts across AITB and BB Google Drives.

Usage:
    python3 search_transcripts.py --query "search terms" [--account aitb|bb|both] [--max 10]

Output:
    JSON array of matching transcripts with id, title, date, account, url.

Requires gog CLI with configured accounts for:
    - aaron@aitrailblazers.org (AITB)
    - aaron@brainbridge.app (BB)
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Transcript folder IDs and account emails
ACCOUNTS = {
    "aitb": {
        "email": "aaron@aitrailblazers.org",
        "folder_id": "1symBd73ztllc7i9s0BOsq80HVhAp1WD9",
        "label": "AITB",
    },
    "bb": {
        "email": "aaron@brainbridge.app",
        "folder_id": "1DEgcy3ygv9-tkbgTByQPH5VvB-WrLyar",
        "label": "BB",
    },
}

# Pattern to extract date from transcript file names
# Matches: "Transcript- 2026-02-12", "Transcript-2025-12-11", "2026-01-09"
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_PATTERN_US = re.compile(r"(\d{2}/\d{2}/\d{4})")


def _extract_date(title: str) -> str:
    """Extract date from transcript title. Returns ISO date or empty string."""
    match = DATE_PATTERN.search(title)
    if match:
        return match.group(1)
    match = DATE_PATTERN_US.search(title)
    if match:
        parts = match.group(1).split("/")
        return f"{parts[2]}-{parts[0]}-{parts[1]}"
    return ""


def _extract_meeting_name(title: str) -> str:
    """Extract meeting name from transcript title (before /Transcript or date)."""
    # Remove "Transcript- DATE" suffix
    name = re.sub(r"/Transcript-?\s*\d{4}-\d{2}-\d{2}.*$", "", title)
    name = re.sub(r"/Transcript-?\s*\d{2}/\d{2}/\d{4}.*$", "", name)
    name = re.sub(r"/Recording\s*-?\s*\d{4}-\d{2}-\d{2}.*$", "", name)
    # Remove "- YYYY/MM/DD ... - Notes by Gemini" suffix
    name = re.sub(r"\s*-\s*\d{4}/\d{2}/\d{2}.*$", "", name)
    return name.strip()


def search_drive(account_key: str, query: str, max_results: int) -> list[dict]:
    """Search a single Google Drive for transcripts matching the query.

    gog drive search does full-text search with a plain text query (not
    Drive API query syntax). Results are filtered client-side to only
    include Google Docs in the transcript folder.
    """
    config = ACCOUNTS[account_key]

    # Request extra results since we filter client-side by folder
    fetch_max = max_results * 3

    cmd = [
        "gog",
        "drive",
        "search",
        query,
        "--account",
        config["email"],
        "--max",
        str(fetch_max),
        "--json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(
                f"Warning: gog drive search failed for {config['label']}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return []

        files = json.loads(result.stdout) if result.stdout.strip() else []
        if isinstance(files, dict):
            files = files.get("files", [])

        transcripts = []
        for f in files:
            # Filter: must be a transcript-type file in the transcript folder
            allowed_types = {
                "application/vnd.google-apps.document",
                "text/markdown",
                "text/plain",
            }
            if f.get("mimeType") not in allowed_types:
                continue
            parents = f.get("parents", [])
            if config["folder_id"] not in parents:
                continue

            file_id = f.get("id", "")
            title = f.get("name", "")
            mime = f.get("mimeType", "")
            if mime == "application/vnd.google-apps.document":
                url = f"https://docs.google.com/document/d/{file_id}"
            else:
                url = f"https://drive.google.com/file/d/{file_id}"
            transcripts.append(
                {
                    "id": file_id,
                    "title": title,
                    "meeting_name": _extract_meeting_name(title),
                    "date": _extract_date(title),
                    "account": account_key,
                    "account_label": config["label"],
                    "url": url,
                }
            )

        # Sort by date descending (most recent first)
        transcripts.sort(key=lambda t: t["date"], reverse=True)
        return transcripts[:max_results]

    except subprocess.TimeoutExpired:
        print(
            f"Warning: Search timed out for {config['label']}",
            file=sys.stderr,
        )
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(
            f"Warning: Failed to parse results for {config['label']}: {e}",
            file=sys.stderr,
        )
        return []


def search_all(
    query: str,
    account: str = "both",
    max_results: int = 10,
) -> dict:
    """Search one or both drives for transcripts."""
    accounts_to_search = list(ACCOUNTS.keys()) if account == "both" else [account]

    all_results = []

    # Search accounts in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(search_drive, key, query, max_results): key
            for key in accounts_to_search
        }
        for future in as_completed(futures):
            results = future.result()
            all_results.extend(results)

    # Sort combined results by date descending
    all_results.sort(key=lambda t: t["date"], reverse=True)

    # Limit total results
    all_results = all_results[:max_results]

    return {
        "query": query,
        "accounts_searched": accounts_to_search,
        "total_results": len(all_results),
        "transcripts": all_results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search meeting transcripts in Google Drive"
    )
    parser.add_argument(
        "--query", required=True, help="Search terms (person, topic, date)"
    )
    parser.add_argument(
        "--account",
        default="both",
        choices=["aitb", "bb", "both"],
        help="Which account to search (default: both)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Max results per account (default: 10)",
    )

    args = parser.parse_args()

    result = search_all(
        query=args.query,
        account=args.account,
        max_results=args.max,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
