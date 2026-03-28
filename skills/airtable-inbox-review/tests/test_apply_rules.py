"""Tests for apply_rules.py — auto-rule application against gathered emails."""

import json
import os
import subprocess
import sys
from unittest.mock import patch


sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "airtable-inbox-review"
    ),
)

from apply_rules import (
    load_rules,
    match_email,
    apply_rules,
    archive_email,
)


# --- Fixtures ---


def _make_email(
    from_addr: str = "john@example.com",
    thread_id: str = "thread_001",
    message_id: str = "msg_001",
    account: str = "personal",
    email_address: str = "aaroneden77@gmail.com",
    subject: str = "Test Subject",
) -> dict:
    return {
        "thread_id": thread_id,
        "message_id": message_id,
        "account": account,
        "email_address": email_address,
        "from": from_addr,
        "from_name": "Test Sender",
        "to": [email_address],
        "subject": subject,
        "date": "Fri, 27 Mar 2026 13:00:00 +0000",
        "snippet": "Test snippet",
        "body_text": "Test body",
        "labels": ["UNREAD", "INBOX"],
        "has_attachments": False,
    }


SAMPLE_RULES = [
    {
        "pattern": "(receipts?|invoice.*?)@.*anthropic\\.com",
        "action": "log_to_sheet",
        "sheet_key": "bb_financial_spreadsheet",
        "category": "AI API Credits",
        "auto_archive": True,
    },
    {
        "pattern": "receipts?@.*openrouter\\.ai",
        "action": "log_to_sheet",
        "sheet_key": "bb_financial_spreadsheet",
        "category": "AI API Credits",
        "auto_archive": True,
    },
]


# --- load_rules ---


class TestLoadRules:
    def test_loads_email_rules_from_json(self, tmp_path):
        mappings = {"email_rules": SAMPLE_RULES, "other_key": "ignored"}
        path = tmp_path / "mappings.json"
        path.write_text(json.dumps(mappings))
        rules = load_rules(str(path))
        assert len(rules) == 2
        assert rules[0]["pattern"] == "(receipts?|invoice.*?)@.*anthropic\\.com"

    def test_returns_empty_when_no_email_rules(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text(json.dumps({"other_key": "value"}))
        rules = load_rules(str(path))
        assert rules == []

    def test_returns_empty_on_missing_file(self):
        rules = load_rules("/nonexistent/path.json")
        assert rules == []


# --- match_email ---


class TestMatchEmail:
    def test_matches_anthropic_invoice(self):
        email = _make_email(from_addr="invoice+statements@mail.anthropic.com")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is not None
        assert rule["category"] == "AI API Credits"

    def test_matches_anthropic_receipt(self):
        email = _make_email(from_addr="receipt@anthropic.com")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is not None

    def test_matches_anthropic_receipts_plural(self):
        email = _make_email(from_addr="receipts@billing.anthropic.com")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is not None

    def test_matches_openrouter(self):
        email = _make_email(from_addr="receipt@openrouter.ai")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is not None

    def test_no_match_random_sender(self):
        email = _make_email(from_addr="hello@example.com")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is None

    def test_no_match_partial(self):
        email = _make_email(from_addr="anthropic@fake.com")
        rule = match_email(email, SAMPLE_RULES)
        assert rule is None

    def test_returns_first_matching_rule(self):
        """If multiple rules match, return the first one."""
        rules = [
            {"pattern": ".*@anthropic\\.com", "action": "first", "auto_archive": True},
            {
                "pattern": "invoice.*@.*anthropic\\.com",
                "action": "second",
                "auto_archive": True,
            },
        ]
        email = _make_email(from_addr="invoice@anthropic.com")
        rule = match_email(email, rules)
        assert rule["action"] == "first"


# --- apply_rules ---


class TestApplyRules:
    def test_separates_matched_and_remaining(self):
        emails = [
            _make_email(
                from_addr="invoice+statements@mail.anthropic.com", thread_id="t1"
            ),
            _make_email(from_addr="hello@example.com", thread_id="t2"),
            _make_email(from_addr="receipt@openrouter.ai", thread_id="t3"),
        ]
        matched, remaining = apply_rules(emails, SAMPLE_RULES)
        assert len(matched) == 2
        assert len(remaining) == 1
        assert remaining[0]["thread_id"] == "t2"

    def test_matched_includes_rule(self):
        emails = [
            _make_email(
                from_addr="invoice+statements@mail.anthropic.com", thread_id="t1"
            ),
        ]
        matched, remaining = apply_rules(emails, SAMPLE_RULES)
        assert matched[0]["email"]["thread_id"] == "t1"
        assert matched[0]["rule"]["category"] == "AI API Credits"

    def test_no_rules_returns_all_as_remaining(self):
        emails = [_make_email(), _make_email(thread_id="t2")]
        matched, remaining = apply_rules(emails, [])
        assert len(matched) == 0
        assert len(remaining) == 2

    def test_empty_emails(self):
        matched, remaining = apply_rules([], SAMPLE_RULES)
        assert matched == []
        assert remaining == []

    def test_only_auto_archive_rules_trigger(self):
        rules = [
            {
                "pattern": ".*@example\\.com",
                "action": "label_only",
                "auto_archive": False,
            },
        ]
        emails = [_make_email(from_addr="test@example.com")]
        matched, remaining = apply_rules(emails, rules)
        assert len(matched) == 0
        assert len(remaining) == 1


# --- archive_email ---


class TestArchiveEmail:
    @patch("apply_rules.subprocess.run")
    def test_calls_gog_with_correct_args(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = archive_email("thread_abc", "aaroneden77@gmail.com")
        assert result is True
        mock_run.assert_called_once_with(
            [
                "gog",
                "gmail",
                "labels",
                "modify",
                "thread_abc",
                "--remove",
                "INBOX",
                "--account",
                "aaroneden77@gmail.com",
                "--force",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("apply_rules.subprocess.run")
    def test_adds_labels_when_specified(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = archive_email(
            "thread_abc", "aaroneden77@gmail.com", add_labels=["Digest"]
        )
        assert result is True
        mock_run.assert_called_once_with(
            [
                "gog",
                "gmail",
                "labels",
                "modify",
                "thread_abc",
                "--remove",
                "INBOX",
                "--account",
                "aaroneden77@gmail.com",
                "--force",
                "--add",
                "Digest",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("apply_rules.subprocess.run")
    def test_returns_false_on_failure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        result = archive_email("thread_abc", "aaroneden77@gmail.com")
        assert result is False

    @patch("apply_rules.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gog", timeout=30)
        result = archive_email("thread_abc", "aaroneden77@gmail.com")
        assert result is False


# --- main (integration-style with mocks) ---


class TestMain:
    def _make_gathered_json(self, emails_by_account: dict) -> str:
        total = sum(len(v) for v in emails_by_account.values())
        return json.dumps(
            {
                "accounts": emails_by_account,
                "summary": {
                    "total_emails": total,
                    "per_account": {k: len(v) for k, v in emails_by_account.items()},
                    "unread_count": 0,
                },
            }
        )

    @patch("sys.argv", ["apply_rules"])
    @patch("apply_rules.archive_email", return_value=True)
    @patch("apply_rules.load_rules", return_value=SAMPLE_RULES)
    def test_filters_and_archives_matched_emails(
        self, mock_rules, mock_archive, capsys
    ):
        gathered = self._make_gathered_json(
            {
                "personal": [
                    _make_email(
                        from_addr="invoice+statements@mail.anthropic.com",
                        thread_id="t1",
                    ),
                    _make_email(from_addr="hello@example.com", thread_id="t2"),
                ],
                "bb": [
                    _make_email(
                        from_addr="receipt@openrouter.ai",
                        thread_id="t3",
                        account="bb",
                        email_address="aaron@brainbridge.app",
                    ),
                ],
            }
        )

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = gathered
            from apply_rules import main

            main()

        out = json.loads(capsys.readouterr().out)

        # Only unmatched email remains
        assert out["summary"]["total_emails"] == 1
        assert len(out["accounts"]["personal"]) == 1
        assert out["accounts"]["personal"][0]["thread_id"] == "t2"
        assert len(out["accounts"]["bb"]) == 0

        # Auto-processed summary
        assert out["auto_processed"]["count"] == 2

        # Archive was called for both matched
        assert mock_archive.call_count == 2
