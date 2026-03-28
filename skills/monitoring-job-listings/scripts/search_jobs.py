#!/usr/bin/env python3
"""
Search job boards for listings matching the configured criteria.

Generates search queries from config.yaml, executes web searches,
deduplicates against seen-listings.json, and outputs new listings as JSON.

Usage:
    python3 search_jobs.py
    python3 search_jobs.py --config /path/to/config.yaml
    python3 search_jobs.py --config config.yaml --seen seen-listings.json
    python3 search_jobs.py --queries-only   # Print queries without searching

Requires:
    PyYAML: pip install pyyaml
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

# Default config paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = (
    SCRIPT_DIR.parent.parent.parent / "maintaining-systems" / "data" / "job-search"
)
DEFAULT_CONFIG = DATA_DIR / "config.yaml"
DEFAULT_SEEN = DATA_DIR / "seen-listings.json"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict[str, Any]:
    """Load YAML search config."""
    try:
        import yaml  # type: ignore
    except ImportError:
        print(
            "Error: PyYAML not installed. Run: pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_seen_listings(seen_path: Path) -> set[str]:
    """Load set of previously seen listing URLs."""
    if not seen_path.exists():
        return set()
    try:
        with open(seen_path) as f:
            data = json.load(f)
            return set(data.get("urls", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen_listings(seen_path: Path, urls: set[str]) -> None:
    """Persist seen listing URLs to disk."""
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    with open(seen_path, "w") as f:
        json.dump(
            {"urls": sorted(urls), "updated": date.today().isoformat()},
            f,
            indent=2,
        )


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


def build_queries(config: dict[str, Any]) -> list[str]:
    """Generate search query strings from config."""
    titles = config.get("search_titles", [])
    locations = config.get("locations", [])
    neg_keywords = config.get("negative_keywords", [])

    neg_part = " ".join(f'-"{kw}"' for kw in neg_keywords[:5])

    queries: list[str] = []
    for title in titles:
        for location in locations:
            q = f'"{title}" {location} jobs'
            if neg_part:
                q += f" {neg_part}"
            queries.append(q)

    return queries


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------


def search_duckduckgo(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """
    Search DuckDuckGo HTML for job listings.

    Returns list of {title, url, snippet} dicts.
    Note: This uses the DuckDuckGo Lite HTML endpoint (no JS required).
    """
    import urllib.parse
    import urllib.request

    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; OpenClaw-JobSearch/1.0; "
            "+https://github.com/openclaw)"
        )
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"Warning: search failed for '{query}': {exc}", file=sys.stderr)
        return []

    # Simple regex extraction of result links and snippets from DDG Lite HTML
    import re

    results: list[dict[str, Any]] = []

    # DDG Lite format: <a class="result-link" href="...">title</a>
    link_pattern = re.compile(
        r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )
    snippet_pattern = re.compile(
        r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )

    links = link_pattern.findall(html)
    snippets = [
        re.sub(r"<[^>]+>", "", s).strip() for s in snippet_pattern.findall(html)
    ]

    for i, (href, title) in enumerate(links[:max_results]):
        snippet = snippets[i] if i < len(snippets) else ""
        results.append(
            {
                "title": title.strip(),
                "url": href,
                "snippet": snippet,
                "source": "duckduckgo",
            }
        )

    return results


def is_job_listing(result: dict[str, Any]) -> bool:
    """Heuristic: is this search result likely a job listing page?"""
    url = result.get("url", "").lower()
    job_domains = [
        "linkedin.com/jobs",
        "indeed.com",
        "glassdoor.com",
        "builtin",
        "wellfound.com",
        "lever.co",
        "greenhouse.io",
        "workable.com",
        "jobs.",
        "/jobs/",
        "/careers/",
        "jobvite.com",
        "smartrecruiters.com",
        "ashbyhq.com",
    ]
    return any(domain in url for domain in job_domains)


# ---------------------------------------------------------------------------
# Main search pipeline
# ---------------------------------------------------------------------------


def search_jobs(
    config: dict[str, Any],
    seen_urls: set[str],
    queries_only: bool = False,
) -> list[dict[str, Any]]:
    """Execute all search queries and return new, deduplicated listings."""
    queries = build_queries(config)

    if queries_only:
        for q in queries:
            print(q)
        return []

    today = date.today().isoformat()
    new_listings: list[dict[str, Any]] = []
    seen_in_run: set[str] = set()

    print(
        f"Running {len(queries)} search queries...",
        file=sys.stderr,
    )

    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {query}", file=sys.stderr)
        results = search_duckduckgo(query)
        time.sleep(1.5)  # Be polite — rate limit

        for result in results:
            url = result.get("url", "")
            if not url or url in seen_urls or url in seen_in_run:
                continue
            if not is_job_listing(result):
                continue

            seen_in_run.add(url)
            new_listings.append(
                {
                    "title": result.get("title", ""),
                    "url": url,
                    "description_snippet": result.get("snippet", ""),
                    "source": result.get("source", "web"),
                    "found_date": today,
                    "search_query": query,
                }
            )

    print(
        f"Found {len(new_listings)} new listings "
        f"(skipped {len(seen_urls)} previously seen)",
        file=sys.stderr,
    )

    return new_listings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search job boards for listings matching the configured criteria."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to config.yaml (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--seen",
        type=Path,
        default=DEFAULT_SEEN,
        help=f"Path to seen-listings.json (default: {DEFAULT_SEEN})",
    )
    parser.add_argument(
        "--queries-only",
        action="store_true",
        help="Print generated search queries and exit without searching",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(
            f"Error: Config file not found: {args.config}\n"
            "Create it at: maintaining-systems/data/job-search/config.yaml",
            file=sys.stderr,
        )
        sys.exit(1)

    config = load_config(args.config)
    seen_urls = load_seen_listings(args.seen)

    listings = search_jobs(config, seen_urls, queries_only=args.queries_only)

    if not args.queries_only:
        output = {
            "new_listings": listings,
            "total_new": len(listings),
            "total_seen_skipped": len(seen_urls),
            "searched_date": date.today().isoformat(),
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
