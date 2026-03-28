#!/usr/bin/env python3
"""
Generate a weekly job search digest Obsidian note from scored listings.

Reads scored listings (from score_listing.py --batch output), creates a
dated Obsidian markdown note, and updates seen-listings.json.

Usage:
    # Full pipeline from search → score → digest:
    python3 search_jobs.py | python3 score_listing.py --batch | python3 generate_digest.py

    # From a pre-scored file:
    python3 generate_digest.py --listings scored.json

    # Specify Obsidian output directory explicitly:
    python3 generate_digest.py --listings scored.json --output ~/ObsidianVault/2-Areas/Career

Requires:
    OBSIDIAN_VAULT environment variable (or --output flag)
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = (
    SCRIPT_DIR.parent.parent.parent / "maintaining-systems" / "data" / "job-search"
)
DEFAULT_SEEN = DATA_DIR / "seen-listings.json"


# ---------------------------------------------------------------------------
# Seen listings management
# ---------------------------------------------------------------------------


def load_seen_listings(seen_path: Path) -> set[str]:
    if not seen_path.exists():
        return set()
    try:
        with open(seen_path) as f:
            return set(json.load(f).get("urls", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen_listings(seen_path: Path, urls: set[str]) -> None:
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    with open(seen_path, "w") as f:
        json.dump(
            {"urls": sorted(urls), "updated": date.today().isoformat()},
            f,
            indent=2,
        )


# ---------------------------------------------------------------------------
# Digest generation
# ---------------------------------------------------------------------------


def build_digest(scored_data: dict[str, Any], digest_date: date) -> str:
    """Build Obsidian markdown digest from scored listings data."""
    listings = scored_data.get("surfaced_listings", scored_data.get("new_listings", []))
    total_scored = scored_data.get("total_scored", len(listings))
    total_surfaced = scored_data.get("total_surfaced", len(listings))

    lines: list[str] = []

    # YAML frontmatter
    lines += [
        "---",
        f"date: {digest_date.isoformat()}",
        "type: job-search-digest",
        f"listings_scored: {total_scored}",
        f"listings_surfaced: {total_surfaced}",
        "---",
        "",
        f"# Job Search Weekly — {digest_date.strftime('%B %d, %Y')}",
        "",
    ]

    if not listings:
        lines += [
            "> No new listings above the scoring threshold this week.",
            "",
        ]
        return "\n".join(lines)

    # Summary table
    lines += [
        "## Summary",
        "",
        "| Score | Title | Company | Location | Source |",
        "|-------|-------|---------|----------|--------|",
    ]

    for listing in listings:
        score = listing.get("score", 0)
        title = listing.get("title", "Unknown")
        company = listing.get("company", "Unknown")
        location = listing.get("location", "Unknown")
        url = listing.get("url", "")
        source = listing.get("source", "")

        # Truncate long titles for table
        title_short = title[:50] + "…" if len(title) > 50 else title
        source_link = f"[{source}]({url})" if url else source

        lines.append(
            f"| {score} | {title_short} | {company} | {location} | {source_link} |"
        )

    lines.append("")

    # Detailed sections
    lines += ["## Details", ""]

    for listing in listings:
        title = listing.get("title", "Unknown")
        company = listing.get("company", "Unknown")
        location = listing.get("location", "Unknown")
        url = listing.get("url", "")
        score = listing.get("score", 0)
        snippet = listing.get("description_snippet", "").strip()
        breakdown = listing.get("score_breakdown", {})
        found_date = listing.get("found_date", "")

        lines += [
            f"### {title} — {company} (Score: {score})",
            "",
        ]

        if location:
            lines.append(f"**Location:** {location}")
        if found_date:
            lines.append(f"**Found:** {found_date}")
        if url:
            lines.append(f"**Link:** {url}")

        if breakdown:
            factors = ", ".join(
                f"{k}: {'+' if v > 0 else ''}{v}" for k, v in breakdown.items()
            )
            lines.append(f"**Score factors:** {factors}")

        if snippet:
            lines += ["", snippet]

        lines += [
            "",
            "**Notes:** (add here after reviewing)",
            "",
            "---",
            "",
        ]

    # Application tracker section
    lines += [
        "## Application Tracker",
        "",
        "| Company | Title | Applied | Status | Notes |",
        "|---------|-------|---------|--------|-------|",
        "| | | | | |",
        "",
    ]

    return "\n".join(lines)


def write_obsidian_note(content: str, output_dir: Path, digest_date: date) -> Path:
    """Write digest to Obsidian vault directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"Job Search Weekly - {digest_date.isoformat()}.md"
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        f.write(content)

    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate weekly job search digest Obsidian note."
    )
    parser.add_argument(
        "--listings",
        type=Path,
        help="Path to scored listings JSON (output of score_listing.py --batch). "
        "Reads stdin if not provided.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Obsidian output directory (overrides OBSIDIAN_VAULT env var). "
        "Note is written to {output}/Job Search Weekly - {date}.md",
    )
    parser.add_argument(
        "--seen",
        type=Path,
        default=DEFAULT_SEEN,
        help=f"Path to seen-listings.json (default: {DEFAULT_SEEN})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print digest to stdout without writing to Obsidian or updating seen-listings",
    )
    args = parser.parse_args()

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        vault = os.environ.get("OBSIDIAN_VAULT", "")
        if not vault:
            print(
                "Error: Set OBSIDIAN_VAULT environment variable or use --output flag.",
                file=sys.stderr,
            )
            sys.exit(1)
        output_dir = Path(vault) / "2-Areas" / "Career"

    # Load scored listings
    if args.listings:
        with open(args.listings) as f:
            scored_data = json.load(f)
    else:
        print("Reading scored listings from stdin...", file=sys.stderr)
        scored_data = json.load(sys.stdin)

    today = date.today()
    digest = build_digest(scored_data, today)

    if args.dry_run:
        print(digest)
        print(
            "\n[DRY RUN] Note NOT written. Remove --dry-run to save.", file=sys.stderr
        )
        return

    # Write Obsidian note
    output_path = write_obsidian_note(digest, output_dir, today)
    print(f"Digest written to: {output_path}")

    # Update seen-listings.json with all processed URLs
    all_listings = scored_data.get(
        "surfaced_listings",
        scored_data.get("new_listings", []),
    )
    new_urls = {item.get("url", "") for item in all_listings if item.get("url")}

    if new_urls:
        seen_urls = load_seen_listings(args.seen)
        seen_urls.update(new_urls)
        save_seen_listings(args.seen, seen_urls)
        print(
            f"Updated seen-listings.json: {len(new_urls)} new URLs added "
            f"({len(seen_urls)} total)"
        )


if __name__ == "__main__":
    main()
