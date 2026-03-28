#!/usr/bin/env python3
"""
Gather unread Beeper messages for inbox review.

Fetches unread chats via the Beeper MCP server (through beeper-read.sh),
then retrieves messages for each chat. Outputs structured JSON for the
AI agent to perform GTD assessment.

Usage:
    python3 gather_beeper.py [--limit 50] [--since 2026-02-01T00:00:00Z]

Output:
    JSON with chats and summary.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BEEPER_READ = os.path.normpath(
    os.path.join(
        SCRIPT_DIR,
        "..",
        "..",
        "..",
        "maintaining-relationships",
        "scripts",
        "using-beeper",
        "beeper-read.sh",
    )
)

# Regex to parse search_chats markdown output
# Format: ## Name (chatID: !xxx:beeper.local)
CHAT_LINE_RE = re.compile(r"^## (.+?) \(chatID: ([^)]+)\)$", re.MULTILINE)

# Regex to extract pagination cursor
CURSOR_RE = re.compile(r"Next page \(older\): cursor='([^']+)', direction='(\w+)'")


def validate_deps() -> None:
    """Check that required dependencies are available."""
    if not os.environ.get("BEEPER_TOKEN"):
        print("Error: BEEPER_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(BEEPER_READ):
        print(f"Error: beeper-read.sh not found at {BEEPER_READ}", file=sys.stderr)
        sys.exit(1)


def call_beeper(tool: str, params: dict) -> str | None:
    """Call beeper-read.sh and return the text output, or None on failure."""
    try:
        result = subprocess.run(
            [BEEPER_READ, tool, json.dumps(params)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(
                f"  Warning: beeper-read.sh {tool} failed: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  Warning: beeper-read.sh {tool} timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Warning: beeper-read.sh {tool} error: {e}", file=sys.stderr)
        return None


def fetch_unread_chats(limit: int = 50, since: str | None = None) -> list[dict]:
    """Fetch unread chats from Beeper, paginating as needed.

    Args:
        limit: Maximum number of chats to return.
        since: ISO timestamp — only include chats with activity after this time.

    Returns:
        List of dicts with 'name' and 'chat_id' keys.
    """
    all_chats: list[dict] = []
    seen_ids: set[str] = set()
    cursor: str | None = None
    page = 0

    while len(all_chats) < limit:
        page += 1
        params: dict = {"unreadOnly": True, "limit": min(limit, 50)}
        if since:
            params["since"] = since
        if cursor:
            params["cursor"] = cursor
            params["direction"] = "before"

        print(f"  Fetching unread chats page {page}...", file=sys.stderr)
        raw = call_beeper("search_chats", params)
        if raw is None:
            break

        matches = CHAT_LINE_RE.findall(raw)
        if not matches:
            break

        for name, chat_id in matches:
            if chat_id in seen_ids:
                continue
            seen_ids.add(chat_id)
            all_chats.append(
                {
                    "name": name.strip(),
                    "chat_id": chat_id.strip(),
                }
            )
            if len(all_chats) >= limit:
                break

        print(
            f"    {len(matches)} chats on page ({len(all_chats)} total)",
            file=sys.stderr,
        )

        # Check for next page
        cursor_match = CURSOR_RE.search(raw)
        if cursor_match:
            next_cursor = cursor_match.group(1)
            if next_cursor != cursor:
                cursor = next_cursor
            else:
                break
        else:
            break

    return all_chats


def fetch_messages_for_chat(chat_id: str) -> list[dict]:
    """Fetch messages for a single chat.

    list_messages returns JSON: {"items": [{"senderID": "...", "isSender": bool,
    "timestamp": "...", "text": "...", ...}, ...]}

    Returns:
        List of message dicts with sender_id, is_sender, timestamp, text.
    """
    raw = call_beeper("list_messages", {"chatID": chat_id})
    if raw is None:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(
            f"  Warning: invalid JSON from list_messages for {chat_id}",
            file=sys.stderr,
        )
        return []

    items = data.get("items", [])
    messages: list[dict] = []
    for item in items:
        text = item.get("text", "").strip()
        if not text:
            continue
        messages.append(
            {
                "sender_id": item.get("senderID", ""),
                "is_sender": item.get("isSender", False),
                "timestamp": item.get("timestamp", ""),
                "text": text,
            }
        )

    return messages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gather unread Beeper messages for inbox review."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max unread chats to fetch (default: 50)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only include chats with activity after this ISO timestamp",
    )
    args = parser.parse_args()

    validate_deps()

    print("Fetching unread Beeper chats...", file=sys.stderr)
    chats = fetch_unread_chats(limit=args.limit, since=args.since)
    print(f"  Found {len(chats)} unread chats", file=sys.stderr)

    results: list[dict] = []
    total_messages = 0

    for chat in chats:
        print(f"  Fetching messages for {chat['name']}...", file=sys.stderr)
        messages = fetch_messages_for_chat(chat["chat_id"])
        total_messages += len(messages)
        results.append(
            {
                "chat_id": chat["chat_id"],
                "name": chat["name"],
                "messages": messages,
                "message_count": len(messages),
            }
        )

    output = {
        "chats": results,
        "summary": {
            "total_unread_chats": len(results),
            "total_messages": total_messages,
        },
    }

    print(json.dumps(output, indent=2))
    print(
        f"\nGather complete: {len(results)} chats, {total_messages} messages",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
