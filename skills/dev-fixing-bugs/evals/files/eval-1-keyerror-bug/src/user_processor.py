"""Process user records from external API responses."""

from typing import Any


def process_user_batch(api_response: dict[str, Any]) -> list[dict[str, str]]:
    """Extract and normalize user records from an API response.

    Args:
        api_response: Raw API response containing user data.

    Returns:
        List of normalized user records with 'name', 'email', and 'role' fields.
    """
    users = api_response["data"]["users"]
    results = []

    for user in users:
        normalized = {
            "name": f"{user['first_name']} {user['last_name']}",
            "email": user["contact"]["email"],
            "role": user["role"]["title"],
        }
        results.append(normalized)

    return results


def summarize_users(users: list[dict[str, str]]) -> dict[str, Any]:
    """Create a summary of processed users.

    Args:
        users: List of normalized user records.

    Returns:
        Summary dict with count and role breakdown.
    """
    role_counts: dict[str, int] = {}
    for user in users:
        role = user["role"]
        role_counts[role] = role_counts.get(role, 0) + 1

    return {
        "total_users": len(users),
        "roles": role_counts,
    }
