#!/usr/bin/env python3
"""
Fetch incomplete reminders from a macOS Reminders list via remindctl.

Usage:
    python3 gather_reminders.py [--list Intuit]

Output:
    JSON with reminders array and count.
"""

import argparse
import json
import re
import subprocess


def fetch_reminders(list_name: str) -> dict:
    """Run remindctl and parse incomplete reminders."""
    try:
        result = subprocess.run(
            ["remindctl", "list", list_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return {"reminders": [], "count": 0, "error": "remindctl not found"}
    except subprocess.TimeoutExpired:
        return {"reminders": [], "count": 0, "error": "remindctl timed out"}

    if result.returncode != 0:
        return {
            "reminders": [],
            "count": 0,
            "error": f"remindctl failed: {result.stderr.strip()}",
        }

    # Parse lines like: [1] [ ] Reminder title [Intuit]
    reminders = []
    for line in result.stdout.splitlines():
        # Match incomplete reminders: [ ] marker (not [x] or [X])
        match = re.match(r"^\[\d+\]\s+\[ \]\s+(.+?)\s+\[.+\]\s*$", line)
        if match:
            reminders.append(
                {
                    "title": match.group(1),
                    "list": list_name,
                    "completed": False,
                }
            )

    return {"reminders": reminders, "count": len(reminders)}


def main():
    parser = argparse.ArgumentParser(
        description="Gather reminders for morning briefing"
    )
    parser.add_argument(
        "--list",
        default="Intuit",
        help="Reminders list name (default: Intuit)",
    )
    args = parser.parse_args()

    result = fetch_reminders(args.list)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
