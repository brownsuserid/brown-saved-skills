#!/usr/bin/env python3
"""Build a JSON catalog of all available skills and their capabilities.

Scans ~/.openclaw/skills/ for SKILL.md files and their references,
producing a structured catalog for task-to-skill matching.

Usage:
    python3 build_skills_catalog.py [--verbose]
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILLS_ROOT = Path.home() / ".openclaw" / "skills"


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    list_fields = {"domain", "depends_on"}
    fm = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("[]").strip()
            if key in list_fields and "," in val:
                val = [v.strip() for v in val.split(",")]
            fm[key] = val
    return fm


def extract_decision_tree(content: str) -> list[dict]:
    """Extract request patterns and references from a meta-skill decision tree."""
    entries = []
    for match in re.finditer(
        r'\|\s*"([^"]+)"[^|]*\|\s*\[([^\]]+)\]\(([^)]+)\)', content
    ):
        entries.append(
            {
                "trigger_patterns": match.group(1),
                "reference_name": match.group(2),
                "reference_path": match.group(3),
            }
        )
    return entries


def extract_references(skill_dir: Path) -> list[dict]:
    """List all reference files in a skill's references/ directory."""
    refs_dir = skill_dir / "references"
    if not refs_dir.exists():
        return []
    refs = []
    for ref_file in sorted(refs_dir.glob("*.md")):
        content = ref_file.read_text()
        # Extract first heading as description
        heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        # Extract overview section
        overview_match = re.search(
            r"## Overview\s*\n\s*\n(.+?)(?:\n\n|\n##)", content, re.DOTALL
        )
        refs.append(
            {
                "name": ref_file.stem,
                "title": heading_match.group(1) if heading_match else ref_file.stem,
                "overview": overview_match.group(1).strip() if overview_match else None,
                "path": str(ref_file),
            }
        )
    return refs


def build_catalog(verbose: bool = False) -> dict:
    """Build the full skills catalog."""
    catalog = {"skills": [], "meta": {"skills_root": str(SKILLS_ROOT)}}

    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
            continue
        if skill_dir.name == "plans":
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            if verbose:
                print(f"Skipping {skill_dir.name}: no SKILL.md", file=sys.stderr)
            continue

        content = skill_md.read_text()
        frontmatter = parse_frontmatter(content)
        decision_tree = extract_decision_tree(content)
        references = extract_references(skill_dir)

        skill_entry = {
            "name": frontmatter.get("name", skill_dir.name),
            "description": frontmatter.get("description", ""),
            "layer": frontmatter.get("layer"),
            "cadence": frontmatter.get("cadence"),
            "domain": frontmatter.get("domain"),
            "depends_on": frontmatter.get("depends_on"),
            "decision_tree": decision_tree if decision_tree else None,
            "references": references if references else None,
        }
        catalog["skills"].append(skill_entry)

    catalog["meta"]["skill_count"] = len(catalog["skills"])
    catalog["meta"]["total_references"] = sum(
        len(s.get("references") or []) for s in catalog["skills"]
    )
    return catalog


def main():
    parser = argparse.ArgumentParser(description="Build skills catalog JSON")
    parser.add_argument("--verbose", action="store_true", help="Show debug info")
    args = parser.parse_args()

    catalog = build_catalog(verbose=args.verbose)
    print(json.dumps(catalog, indent=2))


if __name__ == "__main__":
    main()
