"""Tests for draft_beeper_followups.py — Beeper follow-up message drafting."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "managing-outreach"),
)

import draft_beeper_followups as draft_followups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(event_name="AI Summit", rsvp_url="https://rsvp.example.com"):
    return {
        "spreadsheet": {
            "id": "sheet-id",
            "developersTab": "Developers",
            "columns": "A:F",
            "account": "test@example.com",
        },
        "event": {
            "name": event_name,
            "date": "2026-03-15",
            "location": "Phoenix, AZ",
            "rsvpUrl": rsvp_url,
        },
        "followup_rules": {
            "priority_order": ["Interested", "No Response", "Invited"],
        },
    }


# ---------------------------------------------------------------------------
# TestRenderTemplate
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    """render_template() renders follow-up message templates."""

    def test_nudge_template(self):
        # Act
        result = draft_followups.render_template(
            "Invited", "John Smith", _make_config()
        )

        # Assert
        assert "John" in result  # Uses first name
        assert "AI Summit" in result
        assert "https://rsvp.example.com" in result

    def test_interested_template(self):
        # Act
        result = draft_followups.render_template(
            "Interested", "Jane Doe", _make_config()
        )

        # Assert
        assert "Jane" in result
        assert "interested" in result.lower() or "RSVP" in result

    def test_custom_templates_from_config(self):
        # Arrange
        config = _make_config()
        config["templates"] = {
            "nudge": "Hey {name}, custom nudge for {event_name}",
            "interested": "Hi {name}, custom interested for {event_name}",
        }

        # Act
        result = draft_followups.render_template("Invited", "Bob", config)

        # Assert
        assert "custom nudge" in result
        assert "Bob" in result


# ---------------------------------------------------------------------------
# TestGetConversationContext
# ---------------------------------------------------------------------------


class TestGetConversationContext:
    """get_conversation_context() parses Beeper message history."""

    @patch("draft_followups.call_beeper")
    def test_parses_messages(self, mock_beeper):
        # Arrange
        mock_beeper.return_value = json.dumps(
            {
                "items": [
                    {
                        "senderID": "@other:beeper.com",
                        "isSender": False,
                        "text": "Hello!",
                        "timestamp": "2026-02-15T10:00:00Z",
                    },
                    {
                        "senderID": "@aaroneden77:beeper.com",
                        "isSender": True,
                        "text": "Hi there",
                        "timestamp": "2026-02-15T11:00:00Z",
                    },
                ]
            }
        )

        # Act
        result = draft_followups.get_conversation_context("!chat123:beeper.local")

        # Assert
        assert len(result["their_messages"]) == 1
        assert len(result["aaron_messages"]) == 1
        assert result["their_messages"][0] == "Hello!"

    @patch("draft_followups.call_beeper")
    def test_beeper_failure_returns_empty(self, mock_beeper):
        # Arrange
        mock_beeper.return_value = None

        # Act
        result = draft_followups.get_conversation_context("!chat:beeper.local")

        # Assert
        assert result["their_messages"] == []
        assert result["aaron_messages"] == []
        assert result["recent_aaron_message"] is False

    @patch("draft_followups.call_beeper")
    def test_detects_today_message(self, mock_beeper):
        # Arrange
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mock_beeper.return_value = json.dumps(
            {
                "items": [
                    {
                        "isSender": True,
                        "text": "Following up",
                        "timestamp": f"{today}T10:00:00Z",
                    },
                ]
            }
        )

        # Act
        result = draft_followups.get_conversation_context("!chat:beeper.local")

        # Assert
        assert result["recent_aaron_message"] is True


# ---------------------------------------------------------------------------
# TestGetContactsNeedingFollowup
# ---------------------------------------------------------------------------


class TestGetContactsNeedingFollowup:
    """get_contacts_needing_followup() builds priority-ordered contact list."""

    @patch("draft_followups.read_spreadsheet")
    def test_filters_by_priority_statuses(self, mock_read):
        # Arrange
        mock_read.return_value = [
            {
                "Name": "Alice",
                "Status": "Interested",
                "Notes": "!chat1:beeper.local",
                "Channel": "LinkedIn",
            },
            {"Name": "Bob", "Status": "RSVPd", "Notes": "", "Channel": "LinkedIn"},
            {
                "Name": "Carol",
                "Status": "Invited",
                "Notes": "!chat2:beeper.local",
                "Channel": "LinkedIn",
            },
        ]

        # Act
        result = draft_followups.get_contacts_needing_followup(_make_config())

        # Assert — RSVPd is not in priority_order
        names = [c["name"] for c in result]
        assert "Alice" in names
        assert "Carol" in names
        assert "Bob" not in names

    @patch("draft_followups.read_spreadsheet")
    def test_priority_ordering(self, mock_read):
        # Arrange
        mock_read.return_value = [
            {"Name": "Carol", "Status": "Invited", "Notes": "", "Channel": "LinkedIn"},
            {
                "Name": "Alice",
                "Status": "Interested",
                "Notes": "",
                "Channel": "LinkedIn",
            },
        ]

        # Act
        result = draft_followups.get_contacts_needing_followup(_make_config())

        # Assert — Interested before Invited
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Carol"


class TestBuildBeeperCommand:
    """build_beeper_command() generates CLI command strings."""

    def test_includes_chat_id(self):
        result = draft_followups.build_beeper_command("!abc:beeper.local", "Hello")
        assert "!abc:beeper.local" in result
        assert "focus_app" in result
