"""User management module."""

from datetime import datetime
from typing import Optional

_user_store: dict[int, dict] = {}
_next_id: int = 1


def create_user(username: str, email: str, role: str = "member") -> dict:
    """Create a new user and store in the global store."""
    global _next_id
    user = {
        "id": _next_id,
        "username": username,
        "email": email,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "login_count": 0,
    }
    _user_store[_next_id] = user
    _next_id += 1
    return user


def get_user(user_id: int) -> Optional[dict]:
    """Get user by ID from global store."""
    return _user_store.get(user_id)


def deactivate_user(user_id: int) -> dict:
    """Deactivate a user."""
    user = _user_store[user_id]
    user["is_active"] = False
    return user


def promote_user(user_id: int) -> dict:
    """Promote user to admin role."""
    user = _user_store[user_id]
    user["role"] = "admin"
    return user


def record_login(user_id: int) -> dict:
    """Record a login event for the user."""
    user = _user_store[user_id]
    user["login_count"] += 1
    user["last_login"] = datetime.utcnow()
    return user


def get_active_users() -> list[dict]:
    """Return all active users."""
    return [u for u in _user_store.values() if u["is_active"]]


def reset_store():
    """Reset the global store — for testing."""
    global _next_id
    _user_store.clear()
    _next_id = 1
