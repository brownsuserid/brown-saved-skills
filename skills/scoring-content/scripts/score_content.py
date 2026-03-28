#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Score a content item against the AI interest profile.

Usage:
    uv run score_content.py --profile /path/to/profile.md --item /path/to/item.md

Output:
    JSON object with score breakdown and final score.

The script computes deterministic components (creator_boost, recency_boost)
and outputs the item metadata needed for LLM-assessed components
(topic_relevance, format_match, negative_penalty). Pablo handles the
LLM assessment and calls this script for the deterministic parts.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML required. Install with: uv pip install pyyaml", file=sys.stderr
    )
    sys.exit(1)


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        print(
            f"Warning: Failed to parse frontmatter in {filepath}: {e}", file=sys.stderr
        )
        return {}


def compute_creator_boost(creator: str, preferred_creators: list[dict]) -> float:
    """Check if creator matches a preferred creator and return boost."""
    if not creator or not preferred_creators:
        return 0.0
    creator_lower = creator.lower()
    for pc in preferred_creators:
        name = pc.get("name", "").lower()
        if name and (name in creator_lower or creator_lower in name):
            return float(pc.get("weight_boost", 0.0))
    return 0.0


def compute_recency_boost(
    published: str, boost_under_days: int = 3, decay_after_days: int = 14
) -> float:
    """Compute recency boost based on publish date."""
    if not published:
        return 0.0
    try:
        pub_date = datetime.strptime(str(published)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0

    age_days = (datetime.now() - pub_date).days
    if age_days < 0:
        age_days = 0

    if age_days <= boost_under_days:
        return 0.1
    elif age_days >= decay_after_days:
        return 0.0
    else:
        # Linear decay from 0.1 to 0.0
        remaining = decay_after_days - boost_under_days
        return 0.1 * (1.0 - (age_days - boost_under_days) / remaining)


def compute_final_score(
    topic_relevance: float,
    creator_boost: float,
    format_match: float,
    recency_boost: float,
    negative_penalty: float,
) -> float:
    """Compute final score, clamped to 0.0-1.0."""
    raw = (
        topic_relevance
        + creator_boost
        + format_match
        + recency_boost
        - negative_penalty
    )
    return max(0.0, min(1.0, raw))


def score_item(profile_path: str, item_path: str) -> dict:
    """Score a single content item against the profile.

    Returns deterministic components and item metadata for LLM assessment.
    """
    profile_file = Path(profile_path)
    item_file = Path(item_path)

    if not profile_file.exists():
        return {"error": f"Profile not found: {profile_path}"}
    if not item_file.exists():
        return {"error": f"Item not found: {item_path}"}

    profile = parse_frontmatter(profile_file)
    item = parse_frontmatter(item_file)

    creator = item.get("creator", "")
    published = item.get("published", "")

    # Deterministic components
    preferred_creators = profile.get("preferred_creators", [])
    creator_boost = compute_creator_boost(creator, preferred_creators)

    content_prefs = profile.get("content_preferences", {})
    recency_cfg = content_prefs.get("recency_bias", {})
    recency_boost = compute_recency_boost(
        published,
        boost_under_days=recency_cfg.get("boost_under_days", 3),
        decay_after_days=recency_cfg.get("decay_after_days", 14),
    )

    # Collect profile data for LLM assessment
    all_interests = []
    for section in ["core_interests", "active_interests", "background_interests"]:
        for topic in profile.get(section, []):
            all_interests.append(
                {
                    "topic": topic.get("topic", ""),
                    "weight": topic.get("weight", 0.0),
                    "keywords": topic.get("keywords", []),
                }
            )

    negative_signals = []
    for sig in profile.get("negative_signals", []):
        negative_signals.append(
            {
                "topic": sig.get("topic", ""),
                "weight": sig.get("weight", 0.0),
                "keywords": sig.get("keywords", []),
            }
        )

    format_prefs = {
        "preferred": content_prefs.get("preferred_formats", []),
        "penalized": content_prefs.get("penalized_formats", []),
    }

    return {
        "item": {
            "title": item.get("title", ""),
            "creator": creator,
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published": str(published),
            "summary": "",  # Read from markdown body if needed
        },
        "deterministic_scores": {
            "creator_boost": round(creator_boost, 3),
            "recency_boost": round(recency_boost, 3),
        },
        "llm_assessment_needed": {
            "interests": all_interests,
            "negative_signals": negative_signals,
            "format_preferences": format_prefs,
        },
        "instructions": (
            "Assess topic_relevance (0.0-1.0): match item against interests, "
            "use highest matching topic's weight. "
            "Assess format_match (-0.2 to +0.2): classify content format. "
            "Assess negative_penalty (0.0-0.8): check against negative signals. "
            "Then call compute_final_score() with all components."
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Score a content item against the AI interest profile"
    )
    parser.add_argument(
        "--profile", required=True, help="Path to the interest profile markdown file"
    )
    parser.add_argument(
        "--item", required=True, help="Path to the content item markdown file"
    )

    args = parser.parse_args()
    result = score_item(args.profile, args.item)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
