#!/usr/bin/env python3
"""
Scan a skill library directory and extract metadata from all SKILL.md files.

Outputs a JSON inventory of all skills with their names, descriptions,
trigger phrases, exclusions, and cross-references.

Usage:
    python3 scan_skills.py <skill-library-path> [--output inventory.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from SKILL.md content."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    frontmatter = {}
    for line in match.group(1).strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def extract_trigger_phrases(description: str) -> list[str]:
    """Extract trigger phrases from a skill description."""
    phrases = []

    # Look for quoted phrases
    quoted = re.findall(r'"([^"]+)"', description)
    phrases.extend(quoted)

    # Look for "triggers for" or "Also triggers" sections
    trigger_match = re.search(
        r"(?:triggers?\s+(?:for|when)|also\s+triggers?\s+(?:for|when))\s+(.+?)(?:\.|$)",
        description,
        re.IGNORECASE,
    )
    if trigger_match:
        # Split on commas and "or"
        segment = trigger_match.group(1)
        parts = re.split(r",\s*|\s+or\s+", segment)
        phrases.extend(p.strip().strip('"').strip("'") for p in parts if p.strip())

    return phrases


def extract_exclusions(content: str) -> list[str]:
    """Extract 'Do NOT use for' exclusions from skill content."""
    exclusions = []

    # Match "Do NOT use for..." or "Do not use for..."
    patterns = [
        r"[Dd]o\s+NOT\s+use\s+(?:for|when)\s+(.+?)(?:\.|$)",
        r"[Dd]on't\s+use\s+(?:for|when)\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        exclusions.extend(m.strip() for m in matches)

    return exclusions


def extract_cross_references(content: str) -> list[str]:
    """Extract references to other skills, ignoring code blocks."""
    # Strip fenced code blocks to avoid matching example/template references
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    refs = []

    # Match ../skill-name/SKILL.md patterns
    path_refs = re.findall(r"\.\./([^/]+)/SKILL\.md", stripped)
    refs.extend(path_refs)

    # Match "use dev-xxx-yyy instead" patterns
    use_instead = re.findall(
        r"use\s+(dev-[\w-]+|infra-[\w-]+|skill-[\w-]+)\s+instead",
        stripped,
        re.IGNORECASE,
    )
    refs.extend(use_instead)

    return list(set(refs))


def extract_key_topics(content: str) -> list[str]:
    """Extract key topics/domains from skill content via headings and keywords."""
    topics = set()

    # Extract from markdown headings
    headings = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)
    for h in headings:
        # Clean up heading text
        clean = re.sub(r"[#*`]", "", h).strip()
        if clean and len(clean) < 60:
            topics.add(clean)

    return sorted(topics)


def scan_skill(skill_dir: Path) -> dict | None:
    """Scan a single skill directory and extract metadata."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text()
    frontmatter = extract_frontmatter(content)

    if not frontmatter.get("name"):
        return None

    description = frontmatter.get("description", "")

    return {
        "name": frontmatter["name"],
        "directory": skill_dir.name,
        "description": description,
        "trigger_phrases": extract_trigger_phrases(description),
        "exclusions": extract_exclusions(content),
        "cross_references": extract_cross_references(content),
        "key_topics": extract_key_topics(content),
        "path": str(skill_md),
    }


def scan_library(library_path: Path) -> list[dict]:
    """Scan all skills in a library directory."""
    skills = []

    for item in sorted(library_path.iterdir()):
        if item.is_dir() and (item / "SKILL.md").exists():
            skill = scan_skill(item)
            if skill:
                skills.append(skill)

    return skills


def find_keyword_overlaps(skills: list[dict]) -> list[dict]:
    """Find pairs of skills with overlapping description keywords."""
    overlaps = []

    # Extract significant keywords from each description
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "ought",
        "and",
        "or",
        "but",
        "if",
        "when",
        "while",
        "for",
        "to",
        "from",
        "in",
        "on",
        "at",
        "by",
        "with",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "of",
        "not",
        "no",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "use",
        "using",
        "used",
        "also",
        "skill",
        "whenever",
        "wants",
        "user",
        "asks",
        "new",
        "existing",
        "code",
        "project",
        "based",
    }

    def get_keywords(desc: str) -> set[str]:
        words = re.findall(r"[a-z]+", desc.lower())
        return {w for w in words if w not in stop_words and len(w) > 3}

    skill_keywords = [(s, get_keywords(s["description"])) for s in skills]

    for i in range(len(skill_keywords)):
        for j in range(i + 1, len(skill_keywords)):
            s1, kw1 = skill_keywords[i]
            s2, kw2 = skill_keywords[j]

            shared = kw1 & kw2
            if len(shared) >= 3:
                union = kw1 | kw2
                overlap_ratio = len(shared) / len(union) if union else 0
                overlaps.append(
                    {
                        "skill_a": s1["name"],
                        "skill_b": s2["name"],
                        "shared_keywords": sorted(shared),
                        "overlap_ratio": round(overlap_ratio, 3),
                        "keyword_count": len(shared),
                    }
                )

    # Sort by overlap ratio descending
    overlaps.sort(key=lambda x: x["overlap_ratio"], reverse=True)
    return overlaps


def check_cross_references(skills: list[dict]) -> list[dict]:
    """Check that all cross-references point to existing skills."""
    skill_dirs = {s["directory"] for s in skills}
    issues = []

    for skill in skills:
        for ref in skill["cross_references"]:
            if ref not in skill_dirs:
                issues.append(
                    {
                        "source_skill": skill["name"],
                        "reference": ref,
                        "status": "BROKEN",
                        "message": f"Referenced skill directory '{ref}' not found",
                    }
                )

    return issues


def main():
    parser = argparse.ArgumentParser(description="Scan skill library for metadata")
    parser.add_argument("library_path", help="Path to skill library directory")
    parser.add_argument("--output", "-o", default=None, help="Output file path (default: stdout)")
    parser.add_argument("--overlaps", action="store_true", help="Include keyword overlap analysis")
    args = parser.parse_args()

    library_path = Path(args.library_path)
    if not library_path.is_dir():
        print(f"Error: {library_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    skills = scan_library(library_path)

    result = {
        "library_path": str(library_path),
        "skill_count": len(skills),
        "skills": skills,
    }

    if args.overlaps:
        result["keyword_overlaps"] = find_keyword_overlaps(skills)
        result["cross_reference_issues"] = check_cross_references(skills)

    output = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Inventory written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
