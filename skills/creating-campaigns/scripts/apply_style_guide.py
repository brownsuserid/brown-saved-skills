#!/usr/bin/env python3
"""
Apply Brain Bridge email style guide rules to campaign records.

Reads the Campaign Plan and Message Guardrails fields for each matching
campaign and patches any missing style guide requirements. Existing content
is preserved — only additions are made.

Style guide source: .claude/skills/email-style-guide/reference.md

Rules applied:
  Tone & Style  — ensures Aaron Eden's voice is referenced if not already present
  Disallowed Patterns — adds em dash / en dash prohibition
  Required Elements   — adds warm opener, value-before-ask, permission to decline,
                        and Calendly link requirements

Usage:
    # Dry run — show what would change, no writes
    python apply_style_guide.py --assignee aaron --dry-run

    # Apply to all of Aaron's active campaigns
    python apply_style_guide.py --assignee aaron

    # Include archived/done campaigns too
    python apply_style_guide.py --assignee aaron --status all

    # Any assignee
    python apply_style_guide.py --assignee josh
"""

import argparse
import json
import os
import sys
import urllib.request
from typing import Any

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "airtable-config"),
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airtable_config import api_headers  # noqa: E402
from fetch_campaigns import fetch_campaigns, _bb, _ensure_config  # noqa: E402

# ---------------------------------------------------------------------------
# Style guide rules to enforce
# ---------------------------------------------------------------------------

# Phrases/substrings that indicate each rule is already documented in the plan.
# Match is case-insensitive against the full campaign plan text.
RULE_SENTINELS = {
    "em_dash": ["em dash", "en dash", "no em", "no dashes", "\u2014", "\u2013"],
    "warm_opener": ["warm opener", "well-wish", "hope you're doing", "genuine well-wish", "opens with genuine"],
    "value_before_ask": ["value before ask", "leads with value", "value-forward", "lead with", "value first"],
    "permission_to_decline": ["just say the word", "permission to decline", "explicit permission"],
    "calendly": ["calendly", "calendar link", "grab a spot"],
    "aaron_voice": ["aaron eden", "aaron's voice", "relationship-first", "warm and enthusiastic"],
}

# Text added when each rule is missing (appended to the style guide block)
RULE_ADDITIONS = {
    "em_dash": "- No em dashes (—) or en dashes (–). Use commas, periods, or new sentences instead.",
    "warm_opener": "- Open every email with a genuine well-wish (e.g., \"I hope you're doing great!\").",
    "value_before_ask": "- Lead with something useful (case study, resource, insight) before making any ask.",
    "permission_to_decline": "- Include explicit permission to decline in the final ask (e.g., \"If not, just say the word\").",
    "calendly": "- Every email CTA includes a Calendly link with a flexible alternative.",
    "aaron_voice": "Warm, direct, relationship-first (Aaron Eden's voice). Opens with genuine well-wishes. Relationship-centered references. Empathetically aware.",
}

SKIP_STATUSES = {"archived", "done", "cancelled", "closed"}

# ---------------------------------------------------------------------------
# Style guide logic
# ---------------------------------------------------------------------------


def _has_rule(plan_text: str, rule_key: str) -> bool:
    """Return True if any sentinel for the rule is found in the plan text."""
    lower = plan_text.lower()
    return any(s in lower for s in RULE_SENTINELS[rule_key])


def compute_missing_rules(plan_text: str) -> list[str]:
    """Return a list of rule keys that are not yet covered in the plan."""
    if not plan_text:
        return list(RULE_SENTINELS.keys())
    return [key for key in RULE_SENTINELS if not _has_rule(plan_text, key)]


def _build_style_block(missing_rules: list[str]) -> str:
    """Build the text block to append, grouped by section target."""
    tone_rules = [k for k in missing_rules if k == "aaron_voice"]
    guardrail_rules = [k for k in missing_rules if k != "aaron_voice"]

    parts = []

    if tone_rules:
        parts.append("**Aaron Eden Voice (Style Guide):**")
        parts.append(RULE_ADDITIONS["aaron_voice"])

    if guardrail_rules:
        if tone_rules:
            parts.append("")
        parts.append("**Style Guide Additions:**")
        for key in guardrail_rules:
            parts.append(RULE_ADDITIONS[key])

    return "\n".join(parts)


def apply_style_guide(plan_text: str, guardrails_text: str, missing_rules: list[str]) -> tuple[str, str]:
    """Return updated (campaign_plan, message_guardrails) with missing rules added.

    Appends a clearly labelled style guide block to:
      - The Message Guardrails section of the Campaign Plan
      - The standalone Message Guardrails field

    Original content is never removed or modified.
    """
    style_block = _build_style_block(missing_rules)
    if not style_block:
        return plan_text, guardrails_text

    separator = "\n\n---\n\n"
    addition = f"{separator}## Style Guide Compliance\n\n{style_block}"

    # Append to Campaign Plan: insert before Section 8 if found, otherwise append.
    # Even if plan_text is empty, still create the style guide block.
    new_plan = plan_text
    section8_markers = ["## Section 8", "**Section 8", "Section 8 —", "Section 8--"]
    insert_idx = -1
    for marker in section8_markers:
        pos = plan_text.find(marker)
        if pos != -1:
            insert_idx = pos
            break
    if insert_idx != -1:
        new_plan = plan_text[:insert_idx].rstrip() + addition + "\n\n" + plan_text[insert_idx:]
    else:
        new_plan = plan_text.rstrip() + addition

    # Append to standalone Message Guardrails field
    new_guardrails = (guardrails_text or "").rstrip() + addition

    return new_plan, new_guardrails


# ---------------------------------------------------------------------------
# Airtable PATCH
# ---------------------------------------------------------------------------


def patch_campaign(base_id: str, table_id: str, record_id: str, fields: dict) -> dict:
    """PATCH a campaign record with the given fields."""
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(url, data=payload, headers=api_headers(), method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def process_campaigns(
    assignee: str | None,
    status_filter: str | None,
    dry_run: bool,
    config_path: str | None,
) -> None:
    config = _ensure_config(config_path)
    bb = _bb(config)
    base_id = bb["base_id"]
    table_id = bb["tables"]["campaigns"]

    print(f"Fetching campaigns{' for ' + assignee if assignee else ''}...", file=sys.stderr)
    records = fetch_campaigns(
        assignee=assignee,
        status=status_filter,
        config_path=config_path,
    )
    print(f"  {len(records)} record(s) fetched.", file=sys.stderr)

    updated = 0
    skipped = 0
    already_ok = 0

    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "(unnamed)")
        status = fields.get("Status", "")
        record_id = record["id"]

        # Skip terminal statuses unless --status all was passed
        if status_filter != "all" and status.lower() in SKIP_STATUSES:
            print(f"  SKIP  {name} [{status}]")
            skipped += 1
            continue

        plan_text = fields.get("Campaign Plan", "") or ""
        guardrails_text = fields.get("Message Guardrails", "") or ""

        # Check if style guide block already applied (may be in plan or guardrails)
        if "Style Guide Compliance" in plan_text or "Style Guide Compliance" in guardrails_text:
            print(f"  OK    {name} [{status}] — style guide already applied")
            already_ok += 1
            continue

        missing = compute_missing_rules(plan_text)
        if not missing:
            print(f"  OK    {name} [{status}] — all rules already present")
            already_ok += 1
            continue

        print(f"  {'DRY'if dry_run else 'UPD'}  {name} [{status}]")
        print(f"         Missing: {', '.join(missing)}")

        if not dry_run:
            new_plan, new_guardrails = apply_style_guide(plan_text, guardrails_text, missing)
            patch_fields: dict[str, Any] = {}
            if new_plan != plan_text:
                patch_fields["Campaign Plan"] = new_plan
            if new_guardrails != guardrails_text:
                patch_fields["Message Guardrails"] = new_guardrails
            if patch_fields:
                patch_campaign(base_id, table_id, record_id, patch_fields)
                updated += 1
        else:
            # Show preview of what would be added
            style_block = _build_style_block(missing)
            preview_lines = style_block.split("\n")
            for line in preview_lines:
                print(f"         + {line}")
            updated += 1  # count as "would update"

    print()
    if dry_run:
        print(f"Dry run complete: {updated} would be updated, {already_ok} already compliant, {skipped} skipped.")
    else:
        print(f"Done: {updated} updated, {already_ok} already compliant, {skipped} skipped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply email style guide rules to BB campaign records.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--assignee", "-a",
        help="Filter by assignee name key (aaron, josh, pablo, ...) or 'all'. Default: all.",
    )
    parser.add_argument(
        "--status", "-s",
        default=None,
        help="Filter by Status. Use 'all' to include archived/done. Default: active only.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without writing to Airtable.",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file.",
    )
    args = parser.parse_args()

    process_campaigns(
        assignee=args.assignee,
        status_filter=args.status,
        dry_run=args.dry_run,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
