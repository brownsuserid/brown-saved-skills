"""Tests for user_processor module."""

from src.user_processor import process_user_batch, summarize_users


def make_api_response(users: list[dict]) -> dict:
    """Helper to create a well-formed API response."""
    return {"data": {"users": users}}


def make_user(
    first: str = "Jane",
    last: str = "Doe",
    email: str = "jane@example.com",
    role: str = "Engineer",
) -> dict:
    """Helper to create a well-formed user record."""
    return {
        "first_name": first,
        "last_name": last,
        "contact": {"email": email},
        "role": {"title": role},
    }


class TestProcessUserBatch:
    def test_single_user(self):
        response = make_api_response([make_user()])
        result = process_user_batch(response)
        assert len(result) == 1
        assert result[0]["name"] == "Jane Doe"
        assert result[0]["email"] == "jane@example.com"
        assert result[0]["role"] == "Engineer"

    def test_multiple_users(self):
        users = [
            make_user("Alice", "Smith", "alice@co.com", "Manager"),
            make_user("Bob", "Jones", "bob@co.com", "Engineer"),
        ]
        result = process_user_batch(make_api_response(users))
        assert len(result) == 2

    def test_empty_users(self):
        result = process_user_batch(make_api_response([]))
        assert result == []


class TestSummarizeUsers:
    def test_role_breakdown(self):
        users = [
            {"name": "A", "email": "a@x.com", "role": "Engineer"},
            {"name": "B", "email": "b@x.com", "role": "Engineer"},
            {"name": "C", "email": "c@x.com", "role": "Manager"},
        ]
        summary = summarize_users(users)
        assert summary["total_users"] == 3
        assert summary["roles"]["Engineer"] == 2
        assert summary["roles"]["Manager"] == 1
