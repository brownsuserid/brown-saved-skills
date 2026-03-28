"""Tests for gather_emails.py — Gmail inbox gathering via gog CLI."""

import base64
import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "airtable-inbox-review"
    ),
)

from gather_emails import (
    BODY_TRUNCATE_CHARS,
    SNIPPET_CHARS,
    _run_gog,
    _parse_json_output,
    _extract_header,
    _extract_body_text,
    _parse_email_address,
    _parse_to_addresses,
    fetch_emails_for_account,
    main,
)


def _b64(text: str) -> str:
    """Encode text as URL-safe base64 (no padding), matching Gmail format."""
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _make_thread(
    thread_id: str = "thread_001",
    message_id: str = "msg_001",
    from_name: str = "John Doe",
    from_email: str = "john@example.com",
    to_email: str = "aaroneden77@gmail.com",
    subject: str = "Test Subject",
    date: str = "Sat, 8 Feb 2026 10:30:00 -0700",
    body_text: str = "Hello, this is the email body.",
    snippet: str = "Hello, this is the email body.",
    labels: list[str] | None = None,
    has_attachment_filename: str = "",
) -> dict:
    """Build a fake gog gmail search thread result."""
    return {
        "id": thread_id,
        "messages": [{"id": message_id}],
    }


def _make_message(
    message_id: str = "msg_001",
    from_name: str = "John Doe",
    from_email: str = "john@example.com",
    to_email: str = "aaroneden77@gmail.com",
    subject: str = "Test Subject",
    date: str = "Sat, 8 Feb 2026 10:30:00 -0700",
    body_text: str = "Hello, this is the email body.",
    snippet: str = "Hello, this is the email body.",
    labels: list[str] | None = None,
    has_attachment_filename: str = "",
) -> dict:
    """Build a fake gog gmail get message result."""
    if labels is None:
        labels = ["INBOX", "UNREAD"]

    parts = [
        {
            "mimeType": "text/plain",
            "body": {"data": _b64(body_text)},
        }
    ]
    if has_attachment_filename:
        parts.append(
            {
                "mimeType": "application/pdf",
                "filename": has_attachment_filename,
                "body": {"size": 12345},
            }
        )

    return {
        "id": message_id,
        "snippet": snippet,
        "labelIds": labels,
        "payload": {
            "headers": [
                {"name": "From", "value": f"{from_name} <{from_email}>"},
                {"name": "To", "value": to_email},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": date},
            ],
            "parts": parts,
        },
    }


def _make_completed_process(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["gog"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestRunGog:
    """_run_gog must build correct gog commands."""

    @patch("gather_emails.subprocess.run")
    def test_builds_correct_command(self, mock_run):
        mock_run.return_value = _make_completed_process()
        _run_gog(["gmail", "search", "in:inbox"], "test@gmail.com")

        mock_run.assert_called_once_with(
            [
                "gog",
                "gmail",
                "search",
                "in:inbox",
                "--account",
                "test@gmail.com",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )


class TestParseJsonOutput:
    """_parse_json_output must handle success, errors, and malformed JSON."""

    def test_parses_valid_json(self):
        result = _make_completed_process(stdout='{"key": "value"}')
        parsed = _parse_json_output(result, "test")
        assert parsed == {"key": "value"}

    def test_parses_json_array(self):
        result = _make_completed_process(stdout='[{"id": 1}]')
        parsed = _parse_json_output(result, "test")
        assert parsed == [{"id": 1}]

    def test_returns_none_on_nonzero_exit(self, capsys):
        result = _make_completed_process(returncode=1, stderr="auth expired")
        parsed = _parse_json_output(result, "test context")
        assert parsed is None
        captured = capsys.readouterr()
        assert "auth expired" in captured.err

    def test_returns_none_on_malformed_json(self, capsys):
        result = _make_completed_process(stdout="not json at all")
        parsed = _parse_json_output(result, "test context")
        assert parsed is None
        captured = capsys.readouterr()
        assert "invalid JSON" in captured.err


class TestExtractHeader:
    """_extract_header must find headers case-insensitively."""

    def test_finds_from_header(self):
        headers = [{"name": "From", "value": "test@example.com"}]
        assert _extract_header(headers, "from") == "test@example.com"

    def test_finds_subject_header(self):
        headers = [{"name": "Subject", "value": "Hello"}]
        assert _extract_header(headers, "Subject") == "Hello"

    def test_returns_empty_when_missing(self):
        headers = [{"name": "From", "value": "test@example.com"}]
        assert _extract_header(headers, "Cc") == ""

    def test_handles_empty_headers_list(self):
        assert _extract_header([], "From") == ""


class TestExtractBodyText:
    """_extract_body_text must handle simple and multipart payloads."""

    def test_extracts_simple_body(self):
        payload = {"body": {"data": _b64("Simple body text")}}
        assert _extract_body_text(payload) == "Simple body text"

    def test_extracts_multipart_text_plain(self):
        payload = {
            "body": {},
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64("Plain text body")}},
                {"mimeType": "text/html", "body": {"data": _b64("<p>HTML</p>")}},
            ],
        }
        assert _extract_body_text(payload) == "Plain text body"

    def test_recurses_nested_multipart(self):
        payload = {
            "body": {},
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": _b64("Nested text")},
                        },
                    ],
                }
            ],
        }
        assert _extract_body_text(payload) == "Nested text"

    def test_returns_empty_when_no_body(self):
        payload = {"body": {}, "parts": []}
        assert _extract_body_text(payload) == ""


class TestParseEmailAddress:
    """_parse_email_address must handle various From header formats."""

    def test_parses_name_and_email(self):
        name, email = _parse_email_address("John Doe <john@example.com>")
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_parses_quoted_name(self):
        name, email = _parse_email_address('"John Doe" <john@example.com>')
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_parses_email_only(self):
        name, email = _parse_email_address("john@example.com")
        assert name == ""
        assert email == "john@example.com"

    def test_parses_empty_string(self):
        name, email = _parse_email_address("")
        assert name == ""
        assert email == ""


class TestParseToAddresses:
    """_parse_to_addresses must handle comma-separated To headers."""

    def test_parses_single_address(self):
        result = _parse_to_addresses("test@example.com")
        assert result == ["test@example.com"]

    def test_parses_multiple_addresses(self):
        result = _parse_to_addresses("a@b.com, c@d.com")
        assert result == ["a@b.com", "c@d.com"]

    def test_parses_named_addresses(self):
        result = _parse_to_addresses("John <john@b.com>, Jane <jane@b.com>")
        assert result == ["john@b.com", "jane@b.com"]

    def test_returns_empty_for_empty_string(self):
        assert _parse_to_addresses("") == []


class TestFetchEmailsForAccount:
    """fetch_emails_for_account must orchestrate search + get calls."""

    @patch("gather_emails._run_gog")
    def test_happy_path_returns_emails(self, mock_gog):
        thread = _make_thread(thread_id="t1", message_id="m1")
        message = _make_message(
            message_id="m1",
            from_name="Alice",
            from_email="alice@example.com",
            subject="Hello Aaron",
            body_text="Please review the doc.",
        )
        thread_get_response = {"thread": {"messages": [message]}}

        mock_gog.side_effect = [
            # Search returns threads
            _make_completed_process(stdout=json.dumps([thread])),
            # threads get returns thread with messages
            _make_completed_process(stdout=json.dumps(thread_get_response)),
        ]

        emails = fetch_emails_for_account("personal", max_results=10)

        assert len(emails) == 1
        e = emails[0]
        assert e["thread_id"] == "t1"
        assert e["message_id"] == "m1"
        assert e["account"] == "personal"
        assert e["email_address"] == "aaroneden77@gmail.com"
        assert e["from"] == "alice@example.com"
        assert e["from_name"] == "Alice"
        assert e["subject"] == "Hello Aaron"
        assert "review the doc" in e["body_text"]
        assert e["labels"] == ["INBOX", "UNREAD"]
        assert e["has_attachments"] is False

    @patch("gather_emails._run_gog")
    def test_multiple_threads(self, mock_gog):
        t1 = _make_thread(thread_id="t1", message_id="m1")
        t2 = _make_thread(thread_id="t2", message_id="m2")
        msg1 = _make_message(message_id="m1", subject="Email 1")
        msg2 = _make_message(message_id="m2", subject="Email 2")

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([t1, t2])),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [msg1]}})
            ),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [msg2]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 2
        assert emails[0]["subject"] == "Email 1"
        assert emails[1]["subject"] == "Email 2"

    @patch("gather_emails._run_gog")
    def test_empty_inbox_returns_empty_list(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="[]")

        emails = fetch_emails_for_account("personal")

        assert emails == []

    @patch("gather_emails._run_gog")
    def test_search_failure_returns_empty_list(self, mock_gog):
        mock_gog.return_value = _make_completed_process(
            returncode=1, stderr="OAuth token expired"
        )

        emails = fetch_emails_for_account("personal")

        assert emails == []

    @patch("gather_emails._run_gog")
    def test_get_failure_skips_that_email(self, mock_gog):
        t1 = _make_thread(thread_id="t1", message_id="m1")
        t2 = _make_thread(thread_id="t2", message_id="m2")
        msg2 = _make_message(message_id="m2", subject="Good Email")

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([t1, t2])),
            # t1 thread get fails
            _make_completed_process(returncode=1, stderr="not found"),
            # t2 thread get succeeds
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [msg2]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        assert emails[0]["subject"] == "Good Email"

    @patch("gather_emails._run_gog")
    def test_malformed_json_from_search_returns_empty(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="not valid json")

        emails = fetch_emails_for_account("bb")

        assert emails == []

    @patch("gather_emails._run_gog")
    def test_body_truncation_at_2000_chars(self, mock_gog):
        long_body = "x" * 3000
        thread = _make_thread()
        message = _make_message(body_text=long_body)

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([thread])),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [message]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        assert len(emails[0]["body_text"]) == BODY_TRUNCATE_CHARS

    @patch("gather_emails._run_gog")
    def test_snippet_truncation_at_200_chars(self, mock_gog):
        long_snippet = "y" * 500
        thread = _make_thread()
        message = _make_message(snippet=long_snippet)

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([thread])),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [message]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        assert len(emails[0]["snippet"]) == SNIPPET_CHARS

    @patch("gather_emails._run_gog")
    def test_max_flag_passed_to_search(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="[]")

        fetch_emails_for_account("personal", max_results=5)

        search_call = mock_gog.call_args_list[0]
        args_passed = search_call[0][0]
        assert "--max" in args_passed
        assert "5" in args_passed

    @patch("gather_emails._run_gog")
    def test_since_flag_adds_newer_than_to_query(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="[]")

        fetch_emails_for_account("personal", since="2d")

        search_call = mock_gog.call_args_list[0]
        args_passed = search_call[0][0]
        # The search query should include newer_than:2d
        assert any("newer_than:2d" in str(a) for a in args_passed)

    @patch("gather_emails._run_gog")
    def test_no_since_flag_omits_newer_than(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="[]")

        fetch_emails_for_account("personal", since=None)

        search_call = mock_gog.call_args_list[0]
        args_passed = search_call[0][0]
        assert not any("newer_than" in str(a) for a in args_passed)

    @patch("gather_emails._run_gog")
    def test_uses_correct_account_email(self, mock_gog):
        mock_gog.return_value = _make_completed_process(stdout="[]")

        fetch_emails_for_account("bb")

        search_call = mock_gog.call_args_list[0]
        account_email = search_call[0][1]
        assert account_email == "aaron@brainbridge.app"

    @patch("gather_emails._run_gog")
    def test_detects_attachments(self, mock_gog):
        thread = _make_thread()
        message = _make_message(has_attachment_filename="report.pdf")

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([thread])),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [message]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        assert emails[0]["has_attachments"] is True

    @patch("gather_emails._run_gog")
    def test_oauth_expired_surfaces_in_stderr(self, mock_gog, capsys):
        mock_gog.return_value = _make_completed_process(
            returncode=1,
            stderr="Error: OAuth2 token expired. Run 'gog auth login' to re-authenticate.",
        )

        emails = fetch_emails_for_account("aitb")

        assert emails == []
        captured = capsys.readouterr()
        assert "OAuth2 token expired" in captured.err

    @patch("gather_emails._run_gog")
    def test_thread_without_messages_is_skipped(self, mock_gog):
        """Thread with empty messages list is skipped."""
        thread_no_msgs = {"id": "t_empty"}
        thread_ok = _make_thread(thread_id="t_ok", message_id="m_ok")
        msg_ok = _make_message(message_id="m_ok", subject="Valid")

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([thread_no_msgs, thread_ok])),
            # t_empty thread get returns thread with no messages
            _make_completed_process(stdout=json.dumps({"thread": {"messages": []}})),
            # t_ok thread get returns thread with message
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [msg_ok]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        assert emails[0]["subject"] == "Valid"

    @patch("gather_emails._run_gog")
    def test_search_returns_dict_with_threads_key(self, mock_gog):
        """gog might return {"threads": [...]} instead of a bare list."""
        thread = _make_thread()
        message = _make_message()

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps({"threads": [thread]})),
            _make_completed_process(
                stdout=json.dumps({"thread": {"messages": [message]}})
            ),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1

    @patch("gather_emails._run_gog")
    def test_real_gog_search_format_no_messages_key(self, mock_gog):
        """Real gog search returns threads without a 'messages' list.

        gog gmail search returns:
        {"threads": [{"id": "...", "date": "...", "from": "...",
                       "subject": "...", "labels": [...], "messageCount": 1}]}
        The thread has an 'id' field but NO 'messages' array.
        """
        real_search = {
            "nextPageToken": "07653952532036321374",
            "threads": [
                {
                    "id": "19c7c364e58e61f6",
                    "date": "2026-02-20 11:00",
                    "from": "Nest Home Report <account@nest.com>",
                    "subject": "Nest January Home Report",
                    "labels": ["UNREAD", "CATEGORY_UPDATES", "INBOX"],
                    "messageCount": 1,
                }
            ],
        }
        # threads get returns data under "thread" key with "messages" array
        real_thread_get = {
            "thread": {
                "messages": [
                    {
                        "id": "19c7c364e58e61f6",
                        "historyId": "123",
                        "internalDate": "1740081600000",
                        "labelIds": ["UNREAD", "CATEGORY_UPDATES", "INBOX"],
                        "payload": {
                            "headers": [
                                {
                                    "name": "From",
                                    "value": "Nest Home Report <account@nest.com>",
                                },
                                {"name": "To", "value": "aaroneden77@gmail.com"},
                                {
                                    "name": "Subject",
                                    "value": "Nest January Home Report",
                                },
                                {
                                    "name": "Date",
                                    "value": "Thu, 20 Feb 2026 11:00:00 -0700",
                                },
                            ],
                            "parts": [
                                {
                                    "mimeType": "text/plain",
                                    "body": {"data": _b64("Your Nest report")},
                                }
                            ],
                        },
                        "sizeEstimate": 5000,
                        "snippet": "Here is your Nest home report",
                        "threadId": "19c7c364e58e61f6",
                    }
                ]
            }
        }

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps(real_search)),
            _make_completed_process(stdout=json.dumps(real_thread_get)),
        ]

        emails = fetch_emails_for_account("personal", max_results=1)

        assert len(emails) == 1
        e = emails[0]
        assert e["from"] == "account@nest.com"
        assert e["subject"] == "Nest January Home Report"
        assert "UNREAD" in e["labels"]
        assert "Nest report" in e["body_text"]
        assert e["snippet"] == "Here is your Nest home report"

    @patch("gather_emails._run_gog")
    def test_real_gog_threads_get_wraps_in_thread_key(self, mock_gog):
        """Real gog threads get wraps messages under a 'thread' key.

        gog gmail threads get returns:
        {"thread": {"messages": [{payload, labelIds, snippet, ...}, ...]}}
        """
        thread = _make_thread(thread_id="t1", message_id="m1")
        thread_get = {
            "thread": {
                "messages": [
                    _make_message(
                        message_id="m1",
                        from_name="Alice",
                        from_email="alice@example.com",
                        subject="Thread Message",
                        labels=["INBOX", "UNREAD"],
                    )
                ]
            }
        }

        mock_gog.side_effect = [
            _make_completed_process(stdout=json.dumps([thread])),
            _make_completed_process(stdout=json.dumps(thread_get)),
        ]

        emails = fetch_emails_for_account("personal")

        assert len(emails) == 1
        e = emails[0]
        assert e["subject"] == "Thread Message"
        assert e["labels"] == ["INBOX", "UNREAD"]


class TestMain:
    """main() must wire up CLI args and produce valid JSON."""

    @patch("gather_emails.fetch_emails_for_account")
    def test_default_args_queries_all_accounts(self, mock_fetch):
        mock_fetch.return_value = []

        with patch("sys.argv", ["gather_emails.py"]):
            main()

        called_aliases = [c[0][0] for c in mock_fetch.call_args_list]
        assert "personal" in called_aliases
        assert "bb" in called_aliases
        assert "aitb" in called_aliases

    @patch("gather_emails.fetch_emails_for_account")
    def test_accounts_filter(self, mock_fetch):
        mock_fetch.return_value = []

        with patch("sys.argv", ["gather_emails.py", "--accounts", "bb"]):
            main()

        assert mock_fetch.call_count == 1
        assert mock_fetch.call_args_list[0][0][0] == "bb"

    @patch("gather_emails.fetch_emails_for_account")
    def test_max_flag_forwarded(self, mock_fetch):
        mock_fetch.return_value = []

        with patch(
            "sys.argv", ["gather_emails.py", "--max", "5", "--accounts", "personal"]
        ):
            main()

        assert mock_fetch.call_args_list[0][1]["max_results"] == 5

    @patch("gather_emails.fetch_emails_for_account")
    def test_since_flag_forwarded(self, mock_fetch):
        mock_fetch.return_value = []

        with patch(
            "sys.argv", ["gather_emails.py", "--since", "2d", "--accounts", "personal"]
        ):
            main()

        assert mock_fetch.call_args_list[0][1]["since"] == "2d"

    @patch("gather_emails.fetch_emails_for_account")
    def test_output_json_structure(self, mock_fetch, capsys):
        mock_fetch.return_value = [
            {
                "thread_id": "t1",
                "message_id": "m1",
                "account": "personal",
                "email_address": "aaroneden77@gmail.com",
                "from": "alice@example.com",
                "from_name": "Alice",
                "to": ["aaroneden77@gmail.com"],
                "subject": "Hello",
                "date": "Sat, 8 Feb 2026 10:30:00",
                "snippet": "Hi there",
                "body_text": "Hi there, full body",
                "labels": ["INBOX", "UNREAD"],
                "has_attachments": False,
            }
        ]

        with patch("sys.argv", ["gather_emails.py", "--accounts", "personal"]):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "accounts" in output
        assert "summary" in output
        assert output["summary"]["total_emails"] == 1
        assert output["summary"]["per_account"]["personal"] == 1
        assert output["summary"]["unread_count"] == 1
        assert len(output["accounts"]["personal"]) == 1

    @patch("gather_emails.fetch_emails_for_account")
    def test_unread_count_calculated(self, mock_fetch, capsys):
        mock_fetch.side_effect = [
            [
                {"labels": ["INBOX", "UNREAD"], "thread_id": "t1"},
                {"labels": ["INBOX"], "thread_id": "t2"},
            ],
            [{"labels": ["INBOX", "UNREAD"], "thread_id": "t3"}],
        ]

        with patch("sys.argv", ["gather_emails.py", "--accounts", "personal,bb"]):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["summary"]["unread_count"] == 2
        assert output["summary"]["total_emails"] == 3

    def test_invalid_account_exits(self):
        with patch("sys.argv", ["gather_emails.py", "--accounts", "bogus"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
