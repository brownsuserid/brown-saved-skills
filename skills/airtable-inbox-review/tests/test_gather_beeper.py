"""Tests for gather_beeper.py — Beeper unread message gathering."""

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

from gather_beeper import (
    call_beeper,
    fetch_messages_for_chat,
    fetch_unread_chats,
    main,
)


def _make_completed_process(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["beeper-read.sh"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _make_search_chats_output(
    chats: list[tuple[str, str]], cursor: str | None = None
) -> str:
    """Build fake search_chats markdown output.

    Args:
        chats: List of (name, chat_id) tuples.
        cursor: Optional pagination cursor to include.
    """
    lines = []
    for name, chat_id in chats:
        lines.append(f"## {name} (chatID: {chat_id})")
        lines.append("Last message preview here")
        lines.append("")
    if cursor:
        lines.append(f"Next page (older): cursor='{cursor}', direction='before'")
    return "\n".join(lines)


def _make_list_messages_output(messages: list[dict]) -> str:
    """Build fake list_messages JSON output."""
    return json.dumps({"items": messages})


class TestCallBeeper:
    """call_beeper must wrap subprocess correctly."""

    @patch("gather_beeper.subprocess.run")
    def test_builds_correct_command(self, mock_run):
        mock_run.return_value = _make_completed_process(stdout="output")
        result = call_beeper("search_chats", {"unreadOnly": True})

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[1] == "search_chats"
        assert json.loads(call_args[2]) == {"unreadOnly": True}
        assert result == "output"

    @patch("gather_beeper.subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        mock_run.return_value = _make_completed_process(
            returncode=1, stderr="connection refused"
        )
        result = call_beeper("search_chats", {})
        assert result is None

    @patch("gather_beeper.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="beeper-read.sh", timeout=60
        )
        result = call_beeper("list_messages", {"chatID": "abc"})
        assert result is None

    @patch("gather_beeper.subprocess.run")
    def test_returns_stdout_on_success(self, mock_run):
        mock_run.return_value = _make_completed_process(stdout="  hello world  ")
        result = call_beeper("search_chats", {})
        assert result == "hello world"


class TestFetchUnreadChats:
    """fetch_unread_chats must parse markdown and handle pagination."""

    @patch("gather_beeper.call_beeper")
    def test_parses_chat_entries(self, mock_beeper):
        mock_beeper.return_value = _make_search_chats_output(
            [
                ("Alice Smith", "!abc:beeper.local"),
                ("Bob Jones", "!def:beeper.local"),
            ]
        )

        chats = fetch_unread_chats(limit=50)

        assert len(chats) == 2
        assert chats[0]["name"] == "Alice Smith"
        assert chats[0]["chat_id"] == "!abc:beeper.local"
        assert chats[1]["name"] == "Bob Jones"

    @patch("gather_beeper.call_beeper")
    def test_handles_pagination_with_cursor(self, mock_beeper):
        page1 = _make_search_chats_output(
            [("Alice", "!a:beeper.local")], cursor="cursor123"
        )
        page2 = _make_search_chats_output([("Bob", "!b:beeper.local")])
        mock_beeper.side_effect = [page1, page2]

        chats = fetch_unread_chats(limit=50)

        assert len(chats) == 2
        assert chats[0]["name"] == "Alice"
        assert chats[1]["name"] == "Bob"
        assert mock_beeper.call_count == 2

    @patch("gather_beeper.call_beeper")
    def test_deduplicates_by_chat_id(self, mock_beeper):
        page1 = _make_search_chats_output(
            [("Alice", "!a:beeper.local")], cursor="cursor1"
        )
        # Page 2 returns the same chat
        page2 = _make_search_chats_output([("Alice", "!a:beeper.local")])
        mock_beeper.side_effect = [page1, page2]

        chats = fetch_unread_chats(limit=50)

        assert len(chats) == 1

    @patch("gather_beeper.call_beeper")
    def test_returns_empty_on_beeper_failure(self, mock_beeper):
        mock_beeper.return_value = None

        chats = fetch_unread_chats()

        assert chats == []

    @patch("gather_beeper.call_beeper")
    def test_respects_limit(self, mock_beeper):
        mock_beeper.return_value = _make_search_chats_output(
            [
                ("Alice", "!a:beeper.local"),
                ("Bob", "!b:beeper.local"),
                ("Carol", "!c:beeper.local"),
            ]
        )

        chats = fetch_unread_chats(limit=2)

        assert len(chats) == 2

    @patch("gather_beeper.call_beeper")
    def test_since_param_forwarded(self, mock_beeper):
        mock_beeper.return_value = _make_search_chats_output([])

        fetch_unread_chats(since="2026-02-01T00:00:00Z")

        call_args = mock_beeper.call_args[0]
        params = call_args[1]
        assert params["since"] == "2026-02-01T00:00:00Z"


class TestFetchMessagesForChat:
    """fetch_messages_for_chat must parse JSON items list."""

    @patch("gather_beeper.call_beeper")
    def test_parses_json_items(self, mock_beeper):
        mock_beeper.return_value = _make_list_messages_output(
            [
                {
                    "senderID": "@alice:beeper.local",
                    "isSender": False,
                    "timestamp": "2026-02-20T10:00:00Z",
                    "text": "Hey, are you free?",
                },
                {
                    "senderID": "@me:beeper.local",
                    "isSender": True,
                    "timestamp": "2026-02-20T10:05:00Z",
                    "text": "Yes, what's up?",
                },
            ]
        )

        messages = fetch_messages_for_chat("!abc:beeper.local")

        assert len(messages) == 2
        assert messages[0]["sender_id"] == "@alice:beeper.local"
        assert messages[0]["is_sender"] is False
        assert messages[0]["timestamp"] == "2026-02-20T10:00:00Z"
        assert messages[0]["text"] == "Hey, are you free?"
        assert messages[1]["is_sender"] is True

    @patch("gather_beeper.call_beeper")
    def test_returns_empty_on_failure(self, mock_beeper):
        mock_beeper.return_value = None

        messages = fetch_messages_for_chat("!abc:beeper.local")

        assert messages == []

    @patch("gather_beeper.call_beeper")
    def test_returns_empty_on_invalid_json(self, mock_beeper):
        mock_beeper.return_value = "not valid json at all"

        messages = fetch_messages_for_chat("!abc:beeper.local")

        assert messages == []

    @patch("gather_beeper.call_beeper")
    def test_skips_empty_text_messages(self, mock_beeper):
        mock_beeper.return_value = _make_list_messages_output(
            [
                {
                    "senderID": "@a:b",
                    "isSender": False,
                    "timestamp": "t1",
                    "text": "Hello",
                },
                {"senderID": "@a:b", "isSender": False, "timestamp": "t2", "text": ""},
                {
                    "senderID": "@a:b",
                    "isSender": False,
                    "timestamp": "t3",
                    "text": "  ",
                },
            ]
        )

        messages = fetch_messages_for_chat("!abc:beeper.local")

        assert len(messages) == 1
        assert messages[0]["text"] == "Hello"


class TestMain:
    """main() must wire up CLI args and produce valid JSON."""

    @patch("gather_beeper.fetch_messages_for_chat")
    @patch("gather_beeper.fetch_unread_chats")
    @patch("gather_beeper.validate_deps")
    def test_default_args(self, mock_validate, mock_chats, mock_msgs, capsys):
        mock_chats.return_value = [
            {"name": "Alice", "chat_id": "!a:beeper.local"},
        ]
        mock_msgs.return_value = [
            {
                "sender_id": "@alice:b",
                "is_sender": False,
                "timestamp": "t",
                "text": "Hi",
            },
        ]

        with patch("sys.argv", ["gather_beeper.py"]):
            main()

        mock_chats.assert_called_once_with(limit=50, since=None)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total_unread_chats"] == 1
        assert output["summary"]["total_messages"] == 1

    @patch("gather_beeper.fetch_messages_for_chat")
    @patch("gather_beeper.fetch_unread_chats")
    @patch("gather_beeper.validate_deps")
    def test_limit_flag_forwarded(self, mock_validate, mock_chats, mock_msgs):
        mock_chats.return_value = []

        with patch("sys.argv", ["gather_beeper.py", "--limit", "10"]):
            main()

        mock_chats.assert_called_once_with(limit=10, since=None)

    @patch("gather_beeper.fetch_messages_for_chat")
    @patch("gather_beeper.fetch_unread_chats")
    @patch("gather_beeper.validate_deps")
    def test_since_flag_forwarded(self, mock_validate, mock_chats, mock_msgs):
        mock_chats.return_value = []

        with patch(
            "sys.argv",
            ["gather_beeper.py", "--since", "2026-02-01T00:00:00Z"],
        ):
            main()

        mock_chats.assert_called_once_with(limit=50, since="2026-02-01T00:00:00Z")

    @patch("gather_beeper.fetch_messages_for_chat")
    @patch("gather_beeper.fetch_unread_chats")
    @patch("gather_beeper.validate_deps")
    def test_output_json_structure(self, mock_validate, mock_chats, mock_msgs, capsys):
        mock_chats.return_value = [
            {"name": "Alice", "chat_id": "!a:beeper.local"},
            {"name": "Bob", "chat_id": "!b:beeper.local"},
        ]
        mock_msgs.side_effect = [
            [
                {
                    "sender_id": "@alice:b",
                    "is_sender": False,
                    "timestamp": "t",
                    "text": "Hi",
                },
                {
                    "sender_id": "@alice:b",
                    "is_sender": False,
                    "timestamp": "t",
                    "text": "Hey",
                },
            ],
            [
                {
                    "sender_id": "@bob:b",
                    "is_sender": False,
                    "timestamp": "t",
                    "text": "Yo",
                },
            ],
        ]

        with patch("sys.argv", ["gather_beeper.py"]):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "chats" in output
        assert "summary" in output
        assert len(output["chats"]) == 2
        assert output["chats"][0]["chat_id"] == "!a:beeper.local"
        assert output["chats"][0]["name"] == "Alice"
        assert output["chats"][0]["message_count"] == 2
        assert output["chats"][1]["message_count"] == 1
        assert output["summary"]["total_unread_chats"] == 2
        assert output["summary"]["total_messages"] == 3

    def test_missing_beeper_token_exits(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.argv", ["gather_beeper.py"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
