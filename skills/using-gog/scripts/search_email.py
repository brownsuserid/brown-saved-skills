#!/usr/bin/env python3
"""
Search Gmail across all accounts or a specific one.

Supports plain text search, Gmail query syntax, date filtering, and
label filtering. By default searches threads; use --messages for individual emails.

Usage:
    # Search all 3 inboxes for "TUSD"
    python3 search_email.py "TUSD"

    # Search only Brain Bridge account
    python3 search_email.py "invoice" --account bb

    # Raw Gmail query syntax (from:, subject:, has:attachment, in:, etc.)
    python3 search_email.py "from:jon subject:symposium" --raw

    # Only emails newer than N days
    python3 search_email.py "proposal" --recent 7

    # Search individual messages instead of threads
    python3 search_email.py "contract" --messages

    # Limit results per account
    python3 search_email.py "follow up" --max 5

    # Combine filters (adds newer_than and wraps text in subject/body search)
    python3 search_email.py "meeting notes" --recent 14 --account aitb

Output:
    JSON with results grouped by account, plus a combined flat list.

After finding threads/messages, fetch full content with gog:
    gog gmail thread get <threadId> --account <email>
    gog gmail get <messageId> --account <email>
    See: skills/using-gog/SKILL.md and references/full-command-reference.md
"""

import argparse
import json
import subprocess
import sys

from gog_config import get_account_labels, get_accounts, load_config


def build_query(query: str, recent_days: int | None, raw: bool) -> str:
    """Build the Gmail search query string."""
    if raw:
        return query

    parts = [query]

    if recent_days:
        parts.append(f"newer_than:{recent_days}d")

    return " ".join(parts)


def search_account_threads(
    email: str,
    query: str,
    max_results: int,
    account_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Search threads in a single Gmail account via gog."""
    cmd = [
        "gog",
        "gmail",
        "search",
        query,
        "--account",
        email,
        "--max",
        str(max_results),
        "--json",
    ]

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

    # gog returns threads as a list or under a key
    threads = (
        data if isinstance(data, list) else data.get("threads", data.get("results", []))
    )

    labels = account_labels or {}
    for t in threads:
        t["_account"] = email
        t["_account_label"] = labels.get(email, email)

    return threads


def search_account_messages(
    email: str,
    query: str,
    max_results: int,
    account_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Search individual messages in a single Gmail account via gog."""
    cmd = [
        "gog",
        "gmail",
        "messages",
        "search",
        query,
        "--account",
        email,
        "--max",
        str(max_results),
        "--json",
    ]

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

    messages = (
        data
        if isinstance(data, list)
        else data.get("messages", data.get("results", []))
    )

    labels = account_labels or {}
    for m in messages:
        m["_account"] = email
        m["_account_label"] = labels.get(email, email)

    return messages


def main():
    # Pre-parse --config to load accounts for dynamic choices
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default=None)
    pre_args, _ = pre_parser.parse_known_args()

    config = load_config(pre_args.config)
    accounts = get_accounts(config)
    account_labels = get_account_labels(config)

    parser = argparse.ArgumentParser(description="Search Gmail across accounts")
    parser.add_argument(
        "query",
        help="Search query (plain text or Gmail query syntax with --raw)",
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
        "--recent",
        "-r",
        type=int,
        metavar="DAYS",
        help="Only emails newer than N days (appends newer_than:Nd to query)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Treat query as raw Gmail query syntax (skips auto-wrapping)",
    )
    parser.add_argument(
        "--messages",
        action="store_true",
        help="Search individual messages instead of threads",
    )
    parser.add_argument(
        "--max",
        "-m",
        type=int,
        default=10,
        help="Max results per account (default: 10)",
    )

    args = parser.parse_args()

    # Determine which accounts to search
    if args.account:
        email = accounts.get(args.account, args.account)
        accounts_to_search = [email]
    else:
        accounts_to_search = list(accounts.values())

    query = build_query(args.query, args.recent, args.raw)
    mode = "messages" if args.messages else "threads"

    by_account = {}
    all_results = []

    for email in accounts_to_search:
        label = account_labels.get(email, email)
        if args.messages:
            results = search_account_messages(email, query, args.max, account_labels)
            key = "messages"
        else:
            results = search_account_threads(email, query, args.max, account_labels)
            key = "threads"

        by_account[label] = {
            "account": email,
            "count": len(results),
            key: results,
        }
        all_results.extend(results)

    total = len(all_results)

    if args.messages:
        hint = (
            "To read a message: gog gmail get <messageId> --account <email>. "
            "See skills/using-gog/SKILL.md for full reference."
        )
        all_key = "all_messages"
    else:
        hint = (
            "To read a full thread: gog gmail thread get <threadId> --account <email>. "
            "To read a single message: gog gmail get <messageId> --account <email>. "
            "See skills/using-gog/SKILL.md for full reference."
        )
        all_key = "all_threads"

    output = {
        "query": query,
        "mode": mode,
        "total_results": total,
        "by_account": by_account,
        all_key: all_results,
    }

    if total > 0:
        output["hint"] = hint

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
