#!/usr/bin/env python3
"""
Draft or send an email via gog, with automatic per-account signature.

Default mode: creates a Gmail draft (NEVER sends). The draft appears in the
account's Gmail Drafts folder, ready for the user to review and send manually.

Send mode (--send): sends the email directly via gog gmail send, with open
tracking enabled (--track). This mode MUST ONLY be used after explicit human
approval. The calling agent must show the full email (to, subject, body) to
the user and receive a clear "yes" / "send it" / equivalent before invoking
--send. Automated pipelines must NEVER use --send.

Accounts are loaded from a YAML config file (--config flag, GOG_ACCOUNTS_CONFIG
env var, or configs/personal.yaml default).

Usage:
    # New draft (default, safe)
    python3 draft_email.py \\
        --account bb \\
        --to "recipient@example.com" \\
        --subject "Following up on our conversation" \\
        --body "Hi Sarah,\\n\\nJust wanted to follow up..."

    # Send with tracking (ONLY after human approval)
    python3 draft_email.py \\
        --account bb \\
        --to "recipient@example.com" \\
        --subject "Following up on our conversation" \\
        --body "Hi Sarah,\\n\\nJust wanted to follow up..." \\
        --send --i-have-human-approval

    # With a specific config
    python3 draft_email.py --config configs/aitb.yaml \\
        --account aitb \\
        --to "member@example.com" \\
        --subject "Update" \\
        --body "Hi..."

    # Reply to an existing thread
    python3 draft_email.py \\
        --account bb \\
        --to "recipient@example.com" \\
        --subject "Re: Our conversation" \\
        --body "Hi Sarah,\\n\\nThanks for your note..." \\
        --reply-to-message-id "18abc123def"

    # Skip auto-signature (body already includes one)
    python3 draft_email.py \\
        --account bb \\
        --to "recipient@example.com" \\
        --subject "Quick note" \\
        --body "Full email including signature here..." \\
        --no-signature

    # Body from stdin (useful for piping)
    echo "Hi there..." | python3 draft_email.py \\
        --account aitb \\
        --to "member@example.com" \\
        --subject "AI Trailblazers Update" \\
        --body-stdin

    # Body from a file (avoids shell-quoting issues with multiline strings)
    python3 draft_email.py \\
        --account bb \\
        --to "jon@expo.dev" \\
        --subject "Following up" \\
        --body-file /tmp/email.txt

    # Send without tracking (rare, e.g. tracking not set up)
    python3 draft_email.py \\
        --account bb \\
        --to "recipient@example.com" \\
        --subject "Quick note" \\
        --body "..." \\
        --send --i-have-human-approval --no-track

Output:
    JSON to stdout with draft/message ID and URL.
    Status messages to stderr.

Rules:
    - Default is DRAFT. Never sends unless --send AND --i-have-human-approval.
    - --send without --i-have-human-approval is a fatal error.
    - Signature is appended automatically unless --no-signature is set.
    - Body must be plain text. No HTML.
    - When --send is used, open tracking (--track) is enabled by default.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

from gog_config import get_account_details, load_config

# Accounts that support contact activity logging
SALES_ACCOUNTS = {"bb", "aitb"}


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def build_body(
    body: str, account_key: str, accounts: dict, include_signature: bool
) -> str:
    """Append the account signature to the body unless suppressed."""
    if not include_signature:
        return body
    sig = accounts[account_key].get("signature", "")
    if not sig:
        return body
    # Avoid double-signature if body already ends with "Best,"
    if body.rstrip().endswith("Best,"):
        return body
    return body + sig


def run_gog(args: list[str], body_text: str | None = None) -> dict:
    """
    Execute a gog command. If body_text is provided, writes it to a temp file
    and passes --body-file to avoid shell quoting issues.

    Returns the parsed JSON output dict.
    Raises SystemExit on failure.
    """
    cmd = ["gog"] + args

    if body_text is not None:
        # Write body to a temp file; pass via --body-file to gog
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(body_text)
            tmp_path = f.name
        try:
            cmd += ["--body-file", tmp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(tmp_path)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        print(
            f"Error: gog command failed:\n{result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(1)

    stdout = result.stdout.strip()
    if not stdout:
        # gog may return empty on success for some subcommands; treat as ok
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Return raw output if not JSON (some gog versions return plain text)
        return {"raw": stdout}


def create_draft(
    account_key: str,
    accounts: dict,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    reply_to_message_id: str | None = None,
) -> dict:
    """Create a Gmail draft via gog. Returns the parsed gog response."""
    account_config = accounts[account_key]
    email = account_config["email"]

    args = [
        "gmail",
        "drafts",
        "create",
        "--to",
        to,
        "--subject",
        subject,
        "--account",
        email,
        "--json",
    ]

    if cc:
        args += ["--cc", cc]
    if bcc:
        args += ["--bcc", bcc]
    if reply_to_message_id:
        args += ["--reply-to-message-id", reply_to_message_id]

    return run_gog(args, body_text=body)


def send_email(
    account_key: str,
    accounts: dict,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    reply_to_message_id: str | None = None,
    track: bool = True,
) -> dict:
    """Send an email via gog gmail send. Returns the parsed gog response.

    CALLER IS RESPONSIBLE for obtaining explicit human approval before calling.
    """
    account_config = accounts[account_key]
    email = account_config["email"]

    args = [
        "gmail",
        "send",
        "--to",
        to,
        "--subject",
        subject,
        "--account",
        email,
        "--json",
    ]

    if cc:
        args += ["--cc", cc]
    if bcc:
        args += ["--bcc", bcc]
    if reply_to_message_id:
        args += ["--reply-to-message-id", reply_to_message_id]
    if track:
        args += ["--track"]

    return run_gog(args, body_text=body)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    # Pre-parse --config so we can load accounts for --account choices
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default=None)
    pre_args, _ = pre_parser.parse_known_args()

    config = load_config(pre_args.config)
    accounts = get_account_details(config)

    parser = argparse.ArgumentParser(
        description="Draft a Gmail email via gog. NEVER sends automatically.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: GOG_ACCOUNTS_CONFIG env var or configs/personal.yaml)",
    )
    parser.add_argument(
        "--account",
        required=True,
        choices=list(accounts.keys()),
        help="Which Gmail account to draft from",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Recipient email address",
    )
    parser.add_argument(
        "--subject",
        required=True,
        help="Email subject line",
    )

    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument(
        "--body",
        help="Email body text (plain text). Signature will be appended automatically.",
    )
    body_group.add_argument(
        "--body-stdin",
        action="store_true",
        help="Read email body from stdin",
    )
    body_group.add_argument(
        "--body-file",
        metavar="PATH",
        help="Path to a plain-text file whose contents become the email body",
    )

    parser.add_argument("--cc", help="CC recipient(s), comma-separated")
    parser.add_argument("--bcc", help="BCC recipient(s), comma-separated")
    parser.add_argument(
        "--reply-to-message-id",
        help="Gmail message ID to reply to (creates reply draft in same thread)",
    )
    parser.add_argument(
        "--no-signature",
        action="store_true",
        help="Do not append the account signature (use when body already includes one)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the email instead of drafting. REQUIRES --i-have-human-approval.",
    )
    parser.add_argument(
        "--i-have-human-approval",
        action="store_true",
        help="Confirms that a human has explicitly approved sending this email. "
        "Required when using --send. Automated pipelines must NEVER set this flag.",
    )
    parser.add_argument(
        "--no-track",
        action="store_true",
        help="Disable open tracking when sending (tracking is on by default with --send).",
    )

    # Activity logging flags
    parser.add_argument(
        "--not-sales",
        action="store_true",
        help="Skip contact activity logging (for non-sales emails from BB/AITB accounts).",
    )
    parser.add_argument(
        "--contact-id",
        help="Airtable contact record ID (skips auto-lookup by email). "
        "Required if recipient not found in Airtable and --not-sales is not set.",
    )
    parser.add_argument(
        "--deal-id",
        help="Airtable deal record ID to link in the activity log (BB only).",
    )

    args = parser.parse_args()

    # Guard: --send requires --i-have-human-approval
    if args.send and not args.i_have_human_approval:
        print(
            "FATAL: --send requires --i-have-human-approval.\n"
            "A human must explicitly approve every sent email.\n"
            "If you are an AI agent: show the full email to the user, "
            "get a clear 'yes', then re-run with both flags.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read body
    if args.body_stdin:
        body_raw = sys.stdin.read()
    elif args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body_raw = f.read()
    else:
        body_raw = args.body

    # Agents often pass literal \n in --body values; convert to real newlines.
    if body_raw and "\\n" in body_raw:
        body_raw = body_raw.replace("\\n", "\n")

    if not body_raw or not body_raw.strip():
        print("Error: email body cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # Build body with signature
    body = build_body(
        body_raw, args.account, accounts, include_signature=not args.no_signature
    )

    account_config = accounts[args.account]

    # Resolve contact for activity logging (before draft/send so we fail early)
    should_log = args.account in SALES_ACCOUNTS and not args.not_sales
    contact_id = None
    _activity_mod = None
    if should_log:
        import contact_activity as _activity_mod

        _lookup = _activity_mod.lookup_contact_by_email

        if args.contact_id:
            contact_id = args.contact_id
        else:
            print(
                f"Looking up contact for {args.to} in {args.account}...",
                file=sys.stderr,
            )
            contact_id = _lookup(args.to, args.account)
            if contact_id:
                print(
                    f"Found contact: {contact_id}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Error: Contact not found for {args.to} in {args.account}. "
                    "Pass --contact-id <record_id> or --not-sales to skip logging.",
                    file=sys.stderr,
                )
                sys.exit(1)

    if args.send:
        print(
            f"SENDING email from {account_config['email']} to {args.to} "
            f"(tracking={'off' if args.no_track else 'on'})...",
            file=sys.stderr,
        )
        result = send_email(
            account_key=args.account,
            accounts=accounts,
            to=args.to,
            subject=args.subject,
            body=body,
            cc=args.cc,
            bcc=args.bcc,
            reply_to_message_id=args.reply_to_message_id,
            track=not args.no_track,
        )
        msg_id = result.get("id", "")
        tracking_id = result.get("trackingId", "")
        output = {
            "status": "sent",
            "account": account_config["email"],
            "to": args.to,
            "subject": args.subject,
            "message_id": msg_id,
            "tracking_id": tracking_id,
            "tracking_enabled": not args.no_track,
            "reply_to_message_id": args.reply_to_message_id or "",
            "signature_appended": not args.no_signature,
        }
        print(json.dumps(output, indent=2))
        print(
            f"\nEmail sent from {account_config['email']}.",
            file=sys.stderr,
        )
    else:
        print(
            f"Drafting email from {account_config['email']} to {args.to}...",
            file=sys.stderr,
        )
        result = create_draft(
            account_key=args.account,
            accounts=accounts,
            to=args.to,
            subject=args.subject,
            body=body,
            cc=args.cc,
            bcc=args.bcc,
            reply_to_message_id=args.reply_to_message_id,
        )
        draft_id = result.get("id", "")
        output = {
            "status": "drafted",
            "account": account_config["email"],
            "to": args.to,
            "subject": args.subject,
            "draft_id": draft_id,
            "gmail_drafts_url": "https://mail.google.com/mail/u/0/#drafts",
            "reply_to_message_id": args.reply_to_message_id or "",
            "signature_appended": not args.no_signature,
            "note": "DRAFT ONLY — not sent. Review and send from Gmail.",
        }
        print(json.dumps(output, indent=2))
        print(
            f"\nDraft created successfully for {account_config['email']}.\n"
            "Review and send from Gmail Drafts.",
            file=sys.stderr,
        )

    # Log contact activity for BB/AITB accounts
    if should_log and contact_id and _activity_mod is not None:
        thread_id = result.get("threadId", result.get("thread_id", ""))
        message_id = result.get("id", "")
        log_result = _activity_mod.log_email_activity(
            base=args.account,
            contact_id=contact_id,
            subject=args.subject,
            to=args.to,
            account_email=account_config["email"],
            deal_id=args.deal_id,
            thread_id=thread_id or None,
            message_id=message_id or None,
        )
        if log_result:
            log_id = log_result.get("id", "")
            print(
                f"Activity logged in {args.account}: {log_id}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
