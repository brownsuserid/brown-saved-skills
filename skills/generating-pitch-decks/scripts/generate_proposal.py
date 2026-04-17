#!/usr/bin/env python3
"""
Generate a Google Docs proposal or scope of work from deal context and a template.

Reads deal context (from gather_deal_context.py output) and a template file,
generates the proposal content using Claude, then creates a Google Doc via gog.

Usage:
    # From context file:
    python3 generate_proposal.py --context context.json --template scope-of-work

    # Pipeline from gather:
    python3 gather_deal_context.py --deal "Radiant Nuclear" | \
      python3 generate_proposal.py --template pricing-proposal --dry-run

    # Preview without creating Doc:
    python3 generate_proposal.py --context context.json --template scope-of-work --dry-run

Available templates: scope-of-work, pricing-proposal

Requires:
    ANTHROPIC_API_KEY
    gog CLI (for Google Docs creation, unless --dry-run)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR.parent.parent / "templates" / "pitch-decks"

GOG_ACCOUNT = "aaron@brainbridge.app"


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def load_template(template_name: str) -> str:
    """Load template markdown from templates/pitch-decks/ directory."""
    template_path = TEMPLATES_DIR / f"{template_name}.md"
    if not template_path.exists():
        # Fall back to inline templates
        return get_inline_template(template_name)
    with open(template_path) as f:
        return f.read()


def get_inline_template(template_name: str) -> str:
    """Built-in fallback templates when file-based templates are not present."""
    templates = {
        "scope-of-work": """
## Executive Summary
{executive_summary}

## Scope of Work

### Objectives
{objectives}

### Deliverables
{deliverables}

### Out of Scope
{out_of_scope}

## Timeline
{timeline}

## Pricing
| Item | Description | Price |
|------|-------------|-------|
| [TO BE FILLED BY AARON] | | |

**Total Investment:** [TO BE FILLED BY AARON]

## Terms and Conditions
- Payment: 50% upfront, 50% upon completion
- Revisions: Up to 2 rounds included
- Confidentiality: All work product is confidential
- Intellectual Property: Client owns all deliverables upon full payment

## Next Steps
{next_steps}

---
*DRAFT — For Review Only*
""",
        "pricing-proposal": """
## Proposed Solution
{proposed_solution}

## Pricing Options

### Option A — [Package Name]
- **Investment:** $[AMOUNT]
- **Includes:** {option_a_includes}
- **Timeline:** {timeline}

### Option B — [Package Name]
- **Investment:** $[AMOUNT]
- **Includes:** {option_b_includes}
- **Timeline:** {timeline}

## What's Included
{whats_included}

## About BrainBridge
BrainBridge is an AI systems integrator helping organizations automate
workflows, reduce manual overhead, and deploy AI agents that actually work.

## Next Steps
{next_steps}

---
*DRAFT — For Review Only*
""",
    }
    template = templates.get(template_name)
    if not template:
        available = list(templates.keys())
        print(
            f"Error: Unknown template '{template_name}'. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return template


# ---------------------------------------------------------------------------
# Content generation via Claude
# ---------------------------------------------------------------------------


def build_generation_prompt(
    context: dict[str, Any], template: str, template_name: str
) -> str:
    """Build Claude prompt to fill in the proposal template."""
    deal = context.get("deal") or {}
    contact = context.get("contact") or {}
    org = context.get("organization") or {}
    notes = context.get("airtable_notes", [])

    deal_name = deal.get("name", "the client")
    org_name = org.get("name") or deal_name
    contact_name = contact.get("name") or "the primary contact"
    contact_title = contact.get("title", "")
    pain_points = deal.get("pain_points", "")
    description = deal.get("description", "")
    stakeholders = deal.get("stakeholder_map", "")
    notes_titles = [n.get("title", "") for n in notes if n.get("title")]
    notes_str = (
        "\n".join(f"- {t}" for t in notes_titles[:5]) if notes_titles else "None"
    )

    return f"""You are drafting a professional {template_name.replace("-", " ")} for BrainBridge.

Deal context:
- Client: {org_name}
- Contact: {contact_name}{f" ({contact_title})" if contact_title else ""}
- Deal stage: {deal.get("status", "Unknown")}
- Deal description: {description[:500] if description else "Not provided"}
- Pain points: {pain_points[:500] if pain_points else "Not provided"}
- Stakeholders: {stakeholders[:300] if stakeholders else "Not provided"}
- Recent meeting notes: {notes_str}

Template to fill in:
{template}

Instructions:
1. Fill in each placeholder section with professional, client-specific content
2. Use the pain points and context to make the proposal relevant to {org_name}
3. Keep dollar amounts and specific pricing as [TO BE FILLED BY AARON] placeholders
4. Write in a confident, professional tone appropriate for a services proposal
5. Keep sections concise but substantive
6. For any section where you lack context, write a helpful placeholder noting what Aaron should add
7. Do NOT invent specific technical requirements, pricing, or timelines — use placeholders

Filled proposal:"""


def generate_with_claude(prompt: str) -> str:
    """Call Claude API to fill in the proposal template."""
    import urllib.request

    if not CLAUDE_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Export it before running this script."
        )

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        return data["content"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Google Docs creation via gog
# ---------------------------------------------------------------------------


def create_google_doc(
    title: str, content: str, account: str = GOG_ACCOUNT
) -> str | None:
    """Create a Google Doc via gog CLI. Returns Doc URL or None."""
    try:
        result = subprocess.run(
            [
                "gog",
                "docs",
                "create",
                "--account",
                account,
                "--title",
                title,
                "--body",
                content,
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        data = json.loads(result.stdout)
        return data.get("url") or data.get("webViewLink")
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        FileNotFoundError,
    ) as exc:
        print(f"Warning: could not create Google Doc: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(context: dict[str, Any], template_name: str, dry_run: bool = True) -> None:
    deal = context.get("deal") or {}
    org = context.get("organization") or {}

    deal_name = deal.get("name", "Deal")
    org_name = org.get("name") or deal_name
    print(f"Loading template: {template_name}", file=sys.stderr)
    template = load_template(template_name)

    print("Generating proposal content with Claude...", file=sys.stderr)
    prompt = build_generation_prompt(context, template, template_name)
    content = generate_with_claude(prompt)

    doc_title = f"DRAFT — {template_name.replace('-', ' ').title()} — {org_name}"

    print(f"\n{'=' * 60}")
    print(f"PROPOSAL: {doc_title}")
    print("=" * 60)
    print(content[:1000] + ("..." if len(content) > 1000 else ""))
    print(f"{'=' * 60}\n")

    if dry_run:
        print("[DRY RUN] Google Doc NOT created. Remove --dry-run to create.")
        return

    print(f"Creating Google Doc: '{doc_title}'...", file=sys.stderr)
    doc_url = create_google_doc(doc_title, content)

    if doc_url:
        print(f"Google Doc created: {doc_url}")
    else:
        print(
            "Google Doc creation failed. "
            "Full content printed above — copy manually if needed."
        )
        # Print full content on failure
        print("\nFull content:\n")
        print(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Google Docs proposal from deal context and a template."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--context",
        type=Path,
        help="Path to deal context JSON (output of gather_deal_context.py)",
    )
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read deal context JSON from stdin",
    )
    parser.add_argument(
        "--template",
        required=True,
        choices=["scope-of-work", "pricing-proposal"],
        help="Proposal template to use",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without creating Google Doc",
    )
    args = parser.parse_args()

    if args.context:
        with open(args.context) as f:
            context = json.load(f)
    else:
        print("Reading deal context from stdin...", file=sys.stderr)
        context = json.load(sys.stdin)

    try:
        run(context, args.template, dry_run=args.dry_run)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
