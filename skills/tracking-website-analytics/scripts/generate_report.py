#!/usr/bin/env python3
"""
Generate a human-readable analytics report from GA4 and Search Console data.

Combines output from fetch_analytics.py and fetch_search_console.py into
a formatted Markdown report. Prints to console and/or writes to Obsidian.

Usage:
    # Full pipeline (recommended):
    python3 fetch_analytics.py > /tmp/ga4.json
    python3 fetch_search_console.py > /tmp/sc.json
    python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json

    # Pipe both outputs in sequence (GA4 first, SC second via file):
    python3 fetch_analytics.py > /tmp/ga4.json && \\
    python3 fetch_search_console.py | \\
    python3 generate_report.py --ga4-file /tmp/ga4.json

    # Save to Obsidian:
    python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json --output obsidian

    # Both console and Obsidian:
    python3 generate_report.py --ga4-file /tmp/ga4.json --sc-file /tmp/sc.json --output both

Requires:
    OBSIDIAN_VAULT environment variable (only when using --output obsidian or both)
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------


def format_date_range(period: dict[str, Any]) -> str:
    """Format period dict into 'Jan 21 – Feb 17, 2026 (28 days)'."""
    from datetime import datetime

    start_str = period.get("start", "")
    end_str = period.get("end", "")

    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        days = (end - start).days + 1

        start_fmt = start.strftime("%b %-d")
        end_fmt = end.strftime("%b %-d, %Y")
        return f"{start_fmt} – {end_fmt} ({days} days)"
    except ValueError:
        return f"{start_str} – {end_str}"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def pct(value: float, total: float) -> str:
    if total == 0:
        return "—"
    return f"{value / total * 100:.1f}%"


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_pct_val(v: float) -> str:
    return f"{v * 100:.1f}%"


def fmt_ctr(v: float) -> str:
    return f"{v * 100:.1f}%"


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


def section_overview(overview: dict[str, Any]) -> list[str]:
    sessions = overview.get("sessions", 0)
    users = overview.get("users", 0)
    pageviews = overview.get("pageviews", 0)
    bounce_rate = overview.get("bounce_rate", 0.0)

    return [
        "### Traffic Overview",
        "",
        f"Sessions:    {fmt_num(sessions)}",
        f"Users:       {fmt_num(users)}",
        f"Pageviews:   {fmt_num(pageviews)}",
        f"Bounce rate: {fmt_pct_val(bounce_rate)}",
        "",
    ]


def section_top_pages_ga4(
    top_pages: list[dict[str, Any]], total_sessions: int
) -> list[str]:
    lines = ["### Top Pages (GA4)", ""]

    if not top_pages:
        lines += ["> No page data available.", ""]
        return lines

    for i, page in enumerate(top_pages, 1):
        path = page.get("page", "/")
        sessions = page.get("sessions", 0)
        share = pct(sessions, total_sessions)
        lines.append(f"{i:2}. {path:<55} {fmt_num(sessions)} sessions  ({share})")

    lines.append("")
    return lines


def section_top_sources(
    top_sources: list[dict[str, Any]], total_sessions: int
) -> list[str]:
    lines = ["### Traffic Sources", ""]

    if not top_sources:
        lines += ["> No source data available.", ""]
        return lines

    for i, src in enumerate(top_sources, 1):
        source = src.get("source", "unknown")
        medium = src.get("medium", "")
        sessions = src.get("sessions", 0)
        share = pct(sessions, total_sessions)
        label = f"{source} / {medium}" if medium and medium != "(none)" else source
        lines.append(f"{i:2}. {label:<35} {fmt_num(sessions):>6}  ({share})")

    lines.append("")
    return lines


def section_top_queries(top_queries: list[dict[str, Any]]) -> list[str]:
    lines = ["### Top Search Queries (Search Console)", ""]

    if not top_queries:
        lines += ["> No query data available.", ""]
        return lines

    header = f"{'Query':<50}  {'Clicks':>6}  {'Impr':>6}  {'Pos':>5}"
    sep = "-" * len(header)
    lines += [header, sep]

    for q in top_queries:
        query = q.get("query", "")
        clicks = q.get("clicks", 0)
        impressions = q.get("impressions", 0)
        position = q.get("position", 0.0)

        # Truncate long queries
        query_disp = query[:48] + "…" if len(query) > 48 else query
        lines.append(
            f"{query_disp:<50}  {clicks:>6,}  {impressions:>6,}  {position:>5.1f}"
        )

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def build_report(ga4_data: dict[str, Any], sc_data: dict[str, Any]) -> str:
    # Use GA4 period for header (it's the primary source)
    period = ga4_data.get("period", sc_data.get("period", {}))
    date_range_str = format_date_range(period)

    overview = ga4_data.get("overview", {})
    top_pages = ga4_data.get("top_pages", [])
    top_sources = ga4_data.get("top_sources", [])
    top_queries = sc_data.get("top_queries", [])

    total_sessions = overview.get("sessions", 0)

    lines: list[str] = [
        f"## aaroneden.com Analytics — {date_range_str}",
        "",
    ]
    lines += section_overview(overview)
    lines += section_top_pages_ga4(top_pages, total_sessions)
    lines += section_top_sources(top_sources, total_sessions)
    lines += section_top_queries(top_queries)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Obsidian output
# ---------------------------------------------------------------------------


def write_obsidian_note(report: str, report_date: date, period_str: str) -> Path:
    vault = os.environ.get("OBSIDIAN_VAULT", "")
    if not vault:
        print(
            "Error: OBSIDIAN_VAULT environment variable not set.\n"
            "Set it or use --output console.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(vault) / "2-Areas" / "Personal Site"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"Analytics - {report_date.isoformat()}.md"
    output_path = output_dir / filename

    frontmatter = "\n".join(
        [
            "---",
            f"date: {report_date.isoformat()}",
            "type: website-analytics",
            f"period: {period_str}",
            "---",
            "",
        ]
    )

    with open(output_path, "w") as f:
        f.write(frontmatter + report + "\n")

    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate aaroneden.com analytics report from GA4 + Search Console data."
    )
    parser.add_argument(
        "--ga4-file",
        type=Path,
        help="Path to GA4 JSON output (from fetch_analytics.py). Reads stdin if not provided.",
    )
    parser.add_argument(
        "--sc-file",
        type=Path,
        help="Path to Search Console JSON output (from fetch_search_console.py). "
        "Omit to generate report with GA4 data only.",
    )
    parser.add_argument(
        "--output",
        choices=["console", "obsidian", "both"],
        default="console",
        help="Where to write the report (default: console)",
    )
    args = parser.parse_args()

    # Load GA4 data
    if args.ga4_file:
        with open(args.ga4_file) as f:
            ga4_data = json.load(f)
    else:
        print("Reading GA4 data from stdin...", file=sys.stderr)
        ga4_data = json.load(sys.stdin)

    # Load Search Console data (optional)
    if args.sc_file:
        with open(args.sc_file) as f:
            sc_data = json.load(f)
    else:
        sc_data = {"top_queries": [], "top_pages": []}

    report = build_report(ga4_data, sc_data)
    today = date.today()
    period_str = format_date_range(ga4_data.get("period", {}))

    if args.output in ("console", "both"):
        print(report)

    if args.output in ("obsidian", "both"):
        output_path = write_obsidian_note(report, today, period_str)
        print(f"\nReport saved to: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
