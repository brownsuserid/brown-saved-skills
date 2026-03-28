#!/usr/bin/env python3
"""
Fetch inbox emails from Gmail accounts via the gog CLI.

Retrieves inbox emails from up to 3 Gmail accounts (personal, bb, aitb),
fetches message details, and outputs structured JSON for the AI agent
to perform GTD assessment.

Usage:
    python3 gather_emails.py [--max 50] [--accounts personal,bb,aitb] [--since 2d]

Output:
    JSON with accounts (personal, bb, aitb) and summary.
"""

import argparse
import json
import subprocess
import sys

# Account config: alias -> email address
ACCOUNTS: dict[str, str] = {
    "personal": "aaroneden77@gmail.com",
    "bb": "aaron@brainbridge.app",
    "aitb": "aaron@aitrailblazers.org",
}

BODY_TRUNCATE_CHARS = 2000
SNIPPET_CHARS = 200


def _run_gog(args: list[str], account_email: str) -> subprocess.CompletedProcess:
    """Run a gog CLI command with --account and --json flags."""
    cmd = ["gog"] + args + ["--account", account_email, "--json"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _parse_json_output(
    result: subprocess.CompletedProcess, context: str
) -> dict | list | None:
    """Parse JSON from gog stdout. Returns None on failure."""
    if result.returncode != 0:
        print(
            f"Warning: gog {context} failed (exit {result.returncode}): {result.stderr.strip()}",
            file=sys.stderr,
        )
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(
            f"Warning: gog {context} returned invalid JSON: {e}",
            file=sys.stderr,
        )
        return None


def _extract_header(headers: list[dict], name: str) -> str:
    """Extract a header value from Gmail message headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_body_text(payload: dict) -> str:
    """Extract plain text body from a Gmail message payload.

    Handles both simple messages (body directly on payload) and
    multipart messages (body in parts).
    """
    # Simple message with direct body
    if payload.get("body", {}).get("data"):
        import base64

        data = payload["body"]["data"]
        # Gmail uses URL-safe base64
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    # Multipart: look for text/plain part
    for part in payload.get("parts", []):
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            import base64

            data = part["body"]["data"]
            return base64.urlsafe_b64decode(data + "==").decode(
                "utf-8", errors="replace"
            )
        # Recurse into nested multipart
        if mime_type.startswith("multipart/"):
            result = _extract_body_text(part)
            if result:
                return result

    return ""


def _parse_email_address(from_header: str) -> tuple[str, str]:
    """Parse 'Name <email>' format. Returns (name, email)."""
    if "<" in from_header and ">" in from_header:
        name = from_header[: from_header.index("<")].strip().strip('"')
        email = from_header[from_header.index("<") + 1 : from_header.index(">")]
        return name, email
    return "", from_header.strip()


def _parse_to_addresses(to_header: str) -> list[str]:
    """Parse To header into list of email addresses."""
    if not to_header:
        return []
    addresses = []
    for part in to_header.split(","):
        _, email = _parse_email_address(part.strip())
        if email:
            addresses.append(email)
    return addresses


def fetch_emails_for_account(
    account_alias: str,
    max_results: int = 50,
    since: str | None = None,
) -> list[dict]:
    """Fetch inbox emails for a single account.

    Returns a list of email dicts, or empty list on failure.
    """
    email_address = ACCOUNTS[account_alias]

    # Build search query
    query = "in:inbox"
    if since:
        query += f" newer_than:{since}"

    # Search for threads
    result = _run_gog(
        ["gmail", "search", query, "--max", str(max_results)],
        email_address,
    )
    search_data = _parse_json_output(result, f"search for {account_alias}")
    if search_data is None:
        return []

    # gog gmail search returns threads — either as a bare list or {"threads": [...]}
    threads = (
        search_data if isinstance(search_data, list) else search_data.get("threads", [])
    )
    if not threads:
        return []

    emails: list[dict] = []
    for thread in threads:
        thread_id = thread.get("id", "")
        if not thread_id:
            continue

        # Fetch the full thread to get all messages and find the latest inbox message.
        # Using thread fetch avoids 404s when thread ID != message ID (multi-message threads).
        thread_result = _run_gog(
            ["gmail", "threads", "get", thread_id],
            email_address,
        )
        thread_data = _parse_json_output(
            thread_result, f"get thread {thread_id} for {account_alias}"
        )
        if thread_data is None:
            continue

        # Thread data is under "thread" key
        thread_obj = thread_data.get("thread", thread_data)
        thread_messages = thread_obj.get("messages", [])
        if not thread_messages:
            continue

        # Find the most recent message that has the INBOX label.
        # Fall back to the last message in the thread if none have INBOX.
        msg_data = None
        for m in reversed(thread_messages):
            if "INBOX" in m.get("labelIds", []):
                msg_data = m
                break
        if msg_data is None:
            msg_data = thread_messages[-1]

        payload = msg_data.get("payload", {})
        headers = payload.get("headers", [])

        from_header = _extract_header(headers, "From")
        from_name, from_email = _parse_email_address(from_header)
        to_header = _extract_header(headers, "To")
        subject = _extract_header(headers, "Subject")
        date_str = _extract_header(headers, "Date")

        # Extract body text
        body_text = _extract_body_text(payload)
        if len(body_text) > BODY_TRUNCATE_CHARS:
            body_text = body_text[:BODY_TRUNCATE_CHARS]

        # Build snippet from body
        snippet_text = msg_data.get("snippet", body_text[:SNIPPET_CHARS])

        # Labels
        labels = msg_data.get("labelIds", [])

        # Attachments detection
        has_attachments = False
        for part in payload.get("parts", []):
            if part.get("filename"):
                has_attachments = True
                break

        email_dict = {
            "thread_id": thread_id,
            "message_id": msg_data.get("id", thread_id),
            "account": account_alias,
            "email_address": email_address,
            "from": from_email,
            "from_name": from_name,
            "to": _parse_to_addresses(to_header),
            "subject": subject,
            "date": date_str,
            "snippet": snippet_text[:SNIPPET_CHARS],
            "body_text": body_text,
            "labels": labels,
            "has_attachments": has_attachments,
        }
        emails.append(email_dict)

    return emails


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch inbox emails from Gmail accounts via gog CLI."
    )
    parser.add_argument(
        "--max", type=int, default=50, help="Max emails per account (default: 50)"
    )
    parser.add_argument(
        "--accounts",
        type=str,
        default=",".join(ACCOUNTS.keys()),
        help=f"Comma-separated account aliases (default: {','.join(ACCOUNTS.keys())})",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only fetch emails newer than this (e.g., 2d, 7d, 1m)",
    )
    args = parser.parse_args()

    requested_accounts = [a.strip() for a in args.accounts.split(",")]
    for alias in requested_accounts:
        if alias not in ACCOUNTS:
            print(
                f"Error: Unknown account alias '{alias}'. Valid: {', '.join(ACCOUNTS.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

    accounts_result: dict[str, list] = {}
    total = 0
    unread = 0

    for alias in requested_accounts:
        emails = fetch_emails_for_account(alias, max_results=args.max, since=args.since)
        accounts_result[alias] = emails
        total += len(emails)
        unread += sum(1 for e in emails if "UNREAD" in e.get("labels", []))

    per_account = {k: len(v) for k, v in accounts_result.items()}

    result = {
        "accounts": accounts_result,
        "summary": {
            "total_emails": total,
            "per_account": per_account,
            "unread_count": unread,
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
