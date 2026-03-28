#!/usr/bin/env python3
"""
Create an Obsidian daily note from template and populate the %%meetings%% placeholder.

Usage:
    python3 create_daily_note.py --briefing-file /path/to/briefing.md [--date 2026-02-06]

Output:
    JSON with daily_note_path, obsidian_uri, created, and meetings_populated.
"""

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime


VAULT = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)"
)
DAILY_NOTES_DIR = os.path.join(VAULT, "3-Resources", "Daily Notes")
TEMPLATE_PATH = os.path.join(VAULT, "Extras", "Templates", "Daily Note Template.md")


def create_note_from_template(date_str: str, daily_note_path: str) -> bool:
    """Create daily note from template if it doesn't already exist.

    Returns True if a new note was created, False if it already existed.
    """
    if os.path.exists(daily_note_path):
        return False

    os.makedirs(os.path.dirname(daily_note_path), exist_ok=True)

    try:
        with open(TEMPLATE_PATH, encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Warning: Template not found at {TEMPLATE_PATH}", file=sys.stderr)
        return False

    # Replace Templater date placeholders with actual date
    content = template.replace('<%tp.file.creation_date("YYYY-MM-DD")%>', date_str)

    with open(daily_note_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def populate_meetings(daily_note_path: str, briefing_content: str) -> bool:
    """Replace %%meetings%% placeholder with briefing content.

    Returns True if the placeholder was found and replaced, False otherwise.
    """
    try:
        with open(daily_note_path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Warning: Daily note not found at {daily_note_path}", file=sys.stderr)
        return False

    if "%%meetings%%" not in content:
        return False

    content = content.replace("%%meetings%%", briefing_content)

    with open(daily_note_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def build_obsidian_uri(date_str: str) -> str:
    """Build an obsidian:// URI for the daily note."""
    file_path = f"3-Resources/Daily Notes/{date_str}"
    encoded = urllib.parse.quote(file_path)
    return f"obsidian://open?vault=2nd%20Brain&file={encoded}"


def main():
    parser = argparse.ArgumentParser(
        description="Create Obsidian daily note for morning briefing"
    )
    parser.add_argument(
        "--briefing-file",
        help="Path to the briefing markdown file to insert into %%meetings%%",
    )
    parser.add_argument(
        "--briefing-content",
        help="Briefing markdown content to insert (alternative to --briefing-file)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date for the daily note (YYYY-MM-DD, default: today)",
    )
    args = parser.parse_args()

    if not args.briefing_file and not args.briefing_content:
        parser.error("Either --briefing-file or --briefing-content is required")

    daily_note_path = os.path.join(DAILY_NOTES_DIR, f"{args.date}.md")

    created = create_note_from_template(args.date, daily_note_path)

    # Get briefing content
    if args.briefing_content:
        briefing_content = args.briefing_content
    elif args.briefing_file:
        try:
            with open(args.briefing_file, encoding="utf-8") as f:
                briefing_content = f.read()
        except FileNotFoundError:
            print(
                f"Error: Briefing file not found: {args.briefing_file}", file=sys.stderr
            )
            briefing_content = ""

    meetings_populated = populate_meetings(daily_note_path, briefing_content)

    result = {
        "daily_note_path": daily_note_path,
        "obsidian_uri": build_obsidian_uri(args.date),
        "created": created,
        "meetings_populated": meetings_populated,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
