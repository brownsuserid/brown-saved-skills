#!/usr/bin/env python3
"""
Apply auto-rules from learned_mappings.json against gathered email JSON.

Reads gathered email JSON (output of gather_emails.py) from stdin,
matches each email's `from` address against rules, archives matches
via gog CLI, and outputs remaining emails as JSON to stdout.

Auto-processed summary is included in the output JSON under `auto_processed`.
Progress and errors are printed to stderr.

Usage:
    python3 gather_emails.py | python3 apply_rules.py
    python3 apply_rules.py < gathered_emails.json
    python3 apply_rules.py --dry-run < gathered_emails.json
"""

import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEARNED_MAPPINGS_PATH = os.path.join(SCRIPT_DIR, "learned_mappings.json")


def load_rules(path: str = LEARNED_MAPPINGS_PATH) -> list[dict]:
    """Load email_rules from learned_mappings.json."""
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("email_rules", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load rules from {path}: {e}", file=sys.stderr)
        return []


def match_email(email: dict, rules: list[dict]) -> dict | None:
    """Check if an email's from address matches any auto-archive rule.

    Returns the first matching rule, or None.
    Only matches rules with auto_archive=True.
    """
    from_addr = email.get("from", "")
    for rule in rules:
        if not rule.get("auto_archive", False):
            continue
        pattern = rule.get("pattern", "")
        try:
            if re.search(pattern, from_addr):
                return rule
        except re.error as e:
            print(f"Warning: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
    return None


def apply_rules(emails: list[dict], rules: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate emails into matched (auto-archive) and remaining.

    Returns:
        (matched, remaining) where matched is a list of
        {"email": ..., "rule": ...} dicts.
    """
    matched = []
    remaining = []
    for email in emails:
        rule = match_email(email, rules)
        if rule:
            matched.append({"email": email, "rule": rule})
        else:
            remaining.append(email)
    return matched, remaining


def archive_email(
    thread_id: str, account_email: str, add_labels: list[str] | None = None
) -> bool:
    """Archive an email by removing INBOX label via gog CLI. Optionally add labels."""
    cmd = [
        "gog",
        "gmail",
        "labels",
        "modify",
        thread_id,
        "--remove",
        "INBOX",
        "--account",
        account_email,
        "--force",
    ]
    if add_labels:
        cmd.extend(["--add", ",".join(add_labels)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(
                f"Warning: Failed to archive {thread_id}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"Warning: Timeout archiving {thread_id}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply auto-rules to gathered email JSON."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without executing",
    )
    parser.add_argument(
        "--rules-path",
        type=str,
        default=LEARNED_MAPPINGS_PATH,
        help=f"Path to learned_mappings.json (default: {LEARNED_MAPPINGS_PATH})",
    )
    args = parser.parse_args()

    # Read gathered emails from stdin
    gathered = json.loads(sys.stdin.read())
    accounts = gathered.get("accounts", {})
    rules = load_rules(args.rules_path)

    auto_processed = []
    archive_failures = []

    # Process each account
    for account_alias, emails in accounts.items():
        matched, remaining = apply_rules(emails, rules)
        accounts[account_alias] = remaining

        for item in matched:
            email = item["email"]
            rule = item["rule"]
            thread_id = email["thread_id"]
            email_address = email["email_address"]
            entry = {
                "thread_id": thread_id,
                "account": account_alias,
                "from": email["from"],
                "subject": email["subject"],
                "rule_category": rule.get("category", ""),
                "action": rule.get("action", "auto_archive"),
            }

            add_labels = rule.get("add_labels", [])

            if args.dry_run:
                label_note = f" +labels:{','.join(add_labels)}" if add_labels else ""
                print(
                    f"[DRY RUN] Would archive{label_note}: {account_alias} | {email['from']} | {email['subject']}",
                    file=sys.stderr,
                )
                entry["status"] = "dry_run"
            else:
                success = archive_email(thread_id, email_address, add_labels=add_labels)
                entry["status"] = "archived" if success else "failed"
                if not success:
                    archive_failures.append(entry)
                    # Put failed emails back into remaining so they show up in triage
                    accounts[account_alias].append(email)
                else:
                    print(
                        f"Auto-archived: {account_alias} | {email['from']} | {email['subject']}",
                        file=sys.stderr,
                    )

            auto_processed.append(entry)

    # Rebuild summary
    total = sum(len(v) for v in accounts.values())
    unread = sum(
        1
        for emails in accounts.values()
        for e in emails
        if "UNREAD" in e.get("labels", [])
    )

    result = {
        "accounts": accounts,
        "summary": {
            "total_emails": total,
            "per_account": {k: len(v) for k, v in accounts.items()},
            "unread_count": unread,
        },
        "auto_processed": {
            "count": len(auto_processed),
            "failures": len(archive_failures),
            "items": auto_processed,
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
