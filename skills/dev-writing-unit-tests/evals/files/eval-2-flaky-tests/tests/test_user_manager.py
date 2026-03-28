"""Tests for user manager — these are flaky and order-dependent."""

from src.user_manager import (
    create_user,
    deactivate_user,
    get_active_users,
    get_user,
    promote_user,
    record_login,
)

# ---------- These tests share global state and depend on execution order ----------

created_user_id = None


def test_create_user():
    """Creates a user and stores the ID globally for later tests."""
    global created_user_id
    user = create_user("alice", "alice@example.com")
    created_user_id = user["id"]
    assert user["username"] == "alice"


def test_get_user():
    """Depends on test_create_user having run first."""
    user = get_user(created_user_id)
    assert user is not None
    assert user["username"] == "alice"


def test_promote_user():
    """Depends on test_create_user having run first."""
    user = promote_user(created_user_id)
    assert user["role"] == "admin"


def test_deactivate_user():
    """Depends on test_create_user having run first."""
    user = deactivate_user(created_user_id)
    assert user["is_active"] is False


def test_get_active_users():
    """Depends on all previous tests and their side effects."""
    # This will fail if test_deactivate_user ran (alice is inactive)
    # but pass if only test_create_user ran
    users = get_active_users()
    # Fragile: depends on how many users were created across ALL tests
    assert len(users) >= 0  # Meaningless assertion


def test_record_login():
    """Uses hardcoded ID that may not exist."""
    user = record_login(1)  # Assumes user ID 1 exists
    assert user["login_count"] > 0


def test_create_another_user():
    """ID depends on how many users were created before this test."""
    user = create_user("bob", "bob@example.com")
    # This assertion is fragile — depends on execution order
    assert user["id"] == 2
