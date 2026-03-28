#!/usr/bin/env python3
"""
Generate a formatted deal review report.

Reads JSON output from gather_deals.py and formats it as a markdown report.
Groups BB deals by type (New Customer, Existing Customer, Partner) and
shows AITB sponsor deals in a separate section.
"""

import json
import sys
from datetime import datetime


def _deal_section(deals: list[dict], section_title: str) -> list[str]:
    """Format a group of deals as a report section."""
    needing_action = [d for d in deals if not d["has_active_tasks"]]
    with_action = [d for d in deals if d["has_active_tasks"]]

    lines = []

    if needing_action:
        lines.extend(
            [
                f"NEEDS NEXT ACTION ({len(needing_action)})",
                "",
            ]
        )
        lines.extend(["| Company | Contact | Stage |", "|---------|---------|-------|"])
        for deal in needing_action:
            company = deal["organization_name"][:30]
            contact = deal["primary_contact_name"][:25]
            stage = deal["status"][:20]
            lines.append(f"| {company} | {contact} | {stage} |")

        lines.extend(["", "Details:", ""])
        for deal in needing_action:
            lines.extend(
                [
                    f"  {deal['organization_name']} ({deal['status']})",
                    f"  Contact: {deal['primary_contact_name']}",
                    f"  {deal['airtable_url']}",
                    "",
                ]
            )

    if with_action:
        lines.extend([f"HAS ACTIVE TASKS ({len(with_action)})", ""])
        for deal in with_action:
            task_list = ", ".join(deal["task_names"][:3])
            if len(deal["task_names"]) > 3:
                task_list += f" (+{len(deal['task_names']) - 3} more)"
            lines.append(
                f"  {deal['organization_name']} ({deal['status']}): {task_list}"
            )
        lines.append("")

    if not deals:
        lines.append("No open deals.")
        lines.append("")

    return lines


def format_report(data: dict) -> str:
    """Format the deal data as a Telegram-friendly markdown report."""
    deals = data.get("deals", [])
    summary = data.get("summary", {})

    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S MST")

    bb_deals = [d for d in deals if d["base"] == "bb"]
    aitb_deals = [d for d in deals if d["base"] == "aitb"]

    # Group BB deals by type
    bb_new = [d for d in bb_deals if d["type"] == "New Customer"]
    bb_existing = [d for d in bb_deals if d["type"] == "Existing Customer"]
    bb_partner = [d for d in bb_deals if d["type"] == "Partner"]

    lines = [
        f"Deal Review - {date_str}",
        "",
        "SUMMARY",
        "---",
        f"Total open deals: {summary['total_deals']}",
        f"  BB: {summary.get('bb', {}).get('total', 0)} "
        f"(needing action: {summary.get('bb', {}).get('without_tasks', 0)})",
        f"  AITB: {summary.get('aitb', {}).get('total', 0)} "
        f"(needing action: {summary.get('aitb', {}).get('without_tasks', 0)})",
        "",
    ]

    # BB by type breakdown
    bb_by_type = summary.get("bb", {}).get("by_type", {})
    if bb_by_type:
        lines.append("BB breakdown:")
        for type_name, counts in bb_by_type.items():
            lines.append(
                f"  {type_name}: {counts['total']} "
                f"(needing action: {counts['without_tasks']})"
            )
        lines.append("")

    # BB sections by type
    lines.extend(["=" * 40, "BRAIN BRIDGE", "=" * 40, ""])

    if bb_new:
        lines.extend([f"-- New Customer ({len(bb_new)}) --", ""])
        lines.extend(_deal_section(bb_new, "New Customer"))

    if bb_existing:
        lines.extend([f"-- Existing Customer ({len(bb_existing)}) --", ""])
        lines.extend(_deal_section(bb_existing, "Existing Customer"))

    if bb_partner:
        lines.extend([f"-- Partner ({len(bb_partner)}) --", ""])
        lines.extend(_deal_section(bb_partner, "Partner"))

    if not bb_deals:
        lines.extend(["No open BB deals.", ""])

    # AITB section
    lines.extend(["=" * 40, "AI TRAILBLAZERS (Sponsors)", "=" * 40, ""])
    lines.extend(_deal_section(aitb_deals, "Sponsor Deals"))

    lines.extend(["---", f"Generated {timestamp}"])

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    report = format_report(data)
    print(report)


if __name__ == "__main__":
    main()
