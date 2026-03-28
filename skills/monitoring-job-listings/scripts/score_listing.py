#!/usr/bin/env python3
"""
Score job listings against Aaron's configured criteria.

Accepts a single listing (--listing JSON) or a batch from stdin (from search_jobs.py).
Outputs scored listings filtered by min_score.

Usage:
    # Score a single listing:
    python3 score_listing.py --listing '{"title": "AI Engineer", "description_snippet": "..."}'

    # Batch score from search_jobs.py output:
    python3 search_jobs.py | python3 score_listing.py --batch

    # Batch with explicit config:
    python3 score_listing.py --batch --config /path/to/config.yaml < listings.json

Requires: PyYAML
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = (
    SCRIPT_DIR.parent.parent.parent / "maintaining-systems" / "data" / "job-search"
)
DEFAULT_CONFIG = DATA_DIR / "config.yaml"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("Error: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------

# Keywords mapped to scoring dimensions
AI_AUTOMATION_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "automation",
    "llm",
    "machine learning",
    "workflow automation",
    "process automation",
    "robotic process",
    "rpa",
    "agentic",
    "ai agent",
    "prompt engineer",
    "ai strategy",
    "ai operations",
]

LEADERSHIP_KEYWORDS = [
    "lead",
    "manager",
    "director",
    "head of",
    "senior",
    "principal",
    "staff",
    "vp ",
    "vice president",
    "architect",
    "strategist",
]

STARTUP_SIGNALS = [
    "startup",
    "early stage",
    "series a",
    "series b",
    "seed stage",
    "small team",
    "growing team",
    "founded in 20",
]

CONSULTING_KEYWORDS = [
    "consulting",
    "advisory",
    "client-facing",
    "client facing",
    "engagement",
    "professional services",
    "management consulting",
]

DEGREE_MISMATCH_PHRASES = [
    "bachelor's required",
    "bachelor's degree required",
    "bs required",
    "master's required",
    "master's degree required",
    "ms required",
    "requires a degree",
    "degree is required",
]


def score_listing(listing: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Score a single listing against config criteria.

    Returns the listing dict augmented with 'score' and 'score_breakdown'.
    """
    weights = config.get("scoring_weights", {})
    neg_weights = config.get("negative_weights", {})
    locations = [loc.lower() for loc in config.get("locations", [])]
    neg_keywords = [kw.lower() for kw in config.get("negative_keywords", [])]
    salary_min = config.get("salary_min", 0)

    title = listing.get("title", "").lower()
    snippet = listing.get("description_snippet", "").lower()
    location = listing.get("location", "").lower()
    combined = f"{title} {snippet}"

    breakdown: dict[str, int] = {}
    score = 0

    # AI/automation focus
    if any(kw in combined for kw in AI_AUTOMATION_KEYWORDS):
        pts = weights.get("ai_automation", 3)
        score += pts
        breakdown["ai_automation"] = pts

    # Leadership role
    if any(kw in title for kw in LEADERSHIP_KEYWORDS):
        pts = weights.get("leadership", 2)
        score += pts
        breakdown["leadership"] = pts

    # Location match
    loc_check = location or combined
    if any(loc in loc_check for loc in locations) or "remote" in combined:
        pts = weights.get("location_match", 2)
        score += pts
        breakdown["location_match"] = pts

    # Startup signal
    if any(sig in combined for sig in STARTUP_SIGNALS):
        pts = weights.get("startup", 1)
        score += pts
        breakdown["startup"] = pts

    # Consulting/advisory
    if any(kw in combined for kw in CONSULTING_KEYWORDS):
        pts = weights.get("consulting", 1)
        score += pts
        breakdown["consulting"] = pts

    # Salary match (if salary disclosed in snippet)
    if salary_min > 0:
        import re

        salary_pattern = re.compile(r"\$(\d{1,3}),?(\d{3})")
        matches = salary_pattern.findall(combined)
        for major, minor in matches:
            salary_val = int(f"{major}{minor}")
            if salary_val >= salary_min:
                pts = weights.get("salary_match", 1)
                score += pts
                breakdown["salary_match"] = pts
                break

    # Negative: junior/entry-level
    if any(kw in combined for kw in neg_keywords):
        pts = neg_weights.get("junior_role", -3)
        score += pts
        breakdown["junior_role"] = pts

    # Negative: degree mismatch
    if any(phrase in combined for phrase in DEGREE_MISMATCH_PHRASES):
        # Only penalize if no "or equivalent" escape hatch
        if "or equivalent" not in combined and "equivalent experience" not in combined:
            pts = neg_weights.get("degree_mismatch", -2)
            score += pts
            breakdown["degree_mismatch"] = pts

    return {**listing, "score": score, "score_breakdown": breakdown}


def filter_and_sort(
    listings: list[dict[str, Any]], min_score: int
) -> list[dict[str, Any]]:
    """Filter by min_score and sort descending."""
    scored = [listing for listing in listings if listing.get("score", 0) >= min_score]
    return sorted(scored, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score job listings against configured criteria."
    )
    parser.add_argument(
        "--listing",
        help="JSON string of a single listing to score",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Read search_jobs.py output from stdin and score all listings",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to config.yaml (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Override min_score from config",
    )
    args = parser.parse_args()

    if not args.listing and not args.batch:
        parser.error("Provide --listing JSON or --batch (reads stdin).")

    if not args.config.exists():
        print(f"Error: config not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    config = load_config(args.config)
    min_score = (
        args.min_score if args.min_score is not None else config.get("min_score", 4)
    )

    if args.batch:
        raw = json.load(sys.stdin)
        listings = raw.get("new_listings", raw) if isinstance(raw, dict) else raw
        scored = [score_listing(listing, config) for listing in listings]
        surfaced = filter_and_sort(scored, min_score)

        print(
            json.dumps(
                {
                    "surfaced_listings": surfaced,
                    "total_scored": len(scored),
                    "total_surfaced": len(surfaced),
                    "min_score": min_score,
                },
                indent=2,
            )
        )

    else:
        listing = json.loads(args.listing)
        result = score_listing(listing, config)
        passed = result["score"] >= min_score
        result["passes_threshold"] = passed
        print(json.dumps(result, indent=2))
        if not passed:
            print(
                f"\nScore {result['score']} is below min_score {min_score}.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
