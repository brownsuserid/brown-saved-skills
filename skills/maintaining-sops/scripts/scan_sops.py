#!/usr/bin/env python3
"""Scan SOPs directory, parse frontmatter, report review status.

Outputs JSON with each SOP's review state: ok, overdue, or missing_frontmatter.
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

# Load vault path from shared config (fallback to default)
_SHARED_CONFIG = Path.home() / ".openclaw" / "skills" / "_shared" / "config.sh"


def _read_config_var(var_name: str, default: str) -> str:
    """Read a variable from the shared shell config."""
    if _SHARED_CONFIG.exists():
        content = _SHARED_CONFIG.read_text()
        # Match VAR="value" or VAR='value' (simple cases)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(f"{var_name}="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                # Expand $HOME
                val = val.replace("$HOME", str(Path.home()))
                return val
    return default


OBSIDIAN_VAULT = _read_config_var(
    "OBSIDIAN_VAULT",
    str(
        Path.home()
        / "Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)"
    ),
)
SOPS_DIR = os.path.join(OBSIDIAN_VAULT, "3-Resources", "SOPs")

# Frontmatter regex: matches YAML between --- delimiters
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key-value pairs from YAML frontmatter (simple parser)."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
    return result


def determine_state(fm: dict[str, str], today: date) -> str:
    """Determine SOP review state from frontmatter."""
    next_review = fm.get("next-review")
    if not next_review:
        return "missing_frontmatter"

    try:
        review_date = date.fromisoformat(next_review)
    except ValueError:
        return "missing_frontmatter"

    return "overdue" if review_date <= today else "ok"


def scan_sops(sops_dir: str | None = None) -> dict:
    """Scan SOPs directory and return structured report."""
    sops_dir = sops_dir or SOPS_DIR
    today = date.today()
    sops: list[dict] = []
    summary: dict[str, int] = {"ok": 0, "overdue": 0, "missing_frontmatter": 0}

    if not os.path.isdir(sops_dir):
        return {
            "total": 0,
            "scanned_at": today.isoformat(),
            "sops": [],
            "summary": summary,
            "error": f"SOPs directory not found: {sops_dir}",
        }

    for root, _, files in os.walk(sops_dir):
        for entry in sorted(files):
            if not entry.endswith(".md") or entry.startswith("_"):
                continue

            filepath = os.path.join(root, entry)
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            fm = parse_frontmatter(content)
            state = determine_state(fm, today)
            summary[state] = summary.get(state, 0) + 1

            # Get relative path from SOPs directory
            rel_path = os.path.relpath(filepath, sops_dir)
            sops.append(
                {
                    "file": rel_path,
                    "title": fm.get("title"),
                    "owner": fm.get("owner"),
                    "status": fm.get("status"),
                    "last_reviewed": fm.get("last-reviewed"),
                    "next_review": fm.get("next-review"),
                    "state": state,
                }
            )

    return {
        "total": len(sops),
        "scanned_at": today.isoformat(),
        "sops": sops,
        "summary": summary,
    }


def main() -> None:
    result = scan_sops()
    print(json.dumps(result, indent=2))

    # Exit with non-zero if there are overdue SOPs (useful for cron alerting)
    if result["summary"].get("overdue", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
