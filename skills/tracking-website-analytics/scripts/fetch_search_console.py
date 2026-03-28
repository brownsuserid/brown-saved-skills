#!/usr/bin/env python3
"""
Fetch Google Search Console data for aaroneden.com.

Queries the Search Console API for top queries and top pages
(clicks, impressions, CTR, average position) for a configurable date range.

Usage:
    python3 fetch_search_console.py
    python3 fetch_search_console.py --date-range last_7_days
    python3 fetch_search_console.py --date-range last_28_days --json
    python3 fetch_search_console.py --config /path/to/config.yaml --rows 30

Requires:
    uv pip install google-api-python-client google-auth pyyaml
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "website-analytics"
DEFAULT_CONFIG = DATA_DIR / "config.yaml"

DATE_RANGE_DAYS: dict[str, int] = {
    "last_7_days": 7,
    "last_28_days": 28,
    "last_90_days": 90,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        print(
            "Error: PyYAML not installed. Run: uv pip install pyyaml", file=sys.stderr
        )
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def resolve_credentials(config: dict[str, Any]) -> Path:
    raw = config.get("credentials_file", "~/.openclaw/secrets/ga4-service-account.json")
    return Path(raw).expanduser()


def resolve_date_range(range_name: str) -> tuple[str, str]:
    # Search Console data lags ~2-3 days
    days = DATE_RANGE_DAYS.get(range_name, 28)
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# Search Console API
# ---------------------------------------------------------------------------


def build_service(credentials_path: Path) -> Any:
    try:
        from googleapiclient.discovery import build  # type: ignore
        from google.oauth2 import service_account  # type: ignore
    except ImportError:
        print(
            "Error: google-api-python-client not installed.\n"
            "Run: uv pip install google-api-python-client google-auth",
            file=sys.stderr,
        )
        sys.exit(1)

    if not credentials_path.exists():
        print(
            f"Error: Credentials file not found: {credentials_path}\n"
            "See tracking-website-analytics.md for one-time setup instructions.",
            file=sys.stderr,
        )
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return build("searchconsole", "v1", credentials=credentials)


def fetch_top_queries(
    service: Any,
    site_url: str,
    start_date: str,
    end_date: str,
    row_limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch top search queries by clicks."""
    response = (
        service.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": row_limit,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            },
        )
        .execute()
    )

    queries = []
    for row in response.get("rows", []):
        queries.append(
            {
                "query": row["keys"][0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0.0)), 4),
                "position": round(float(row.get("position", 0.0)), 1),
            }
        )
    return queries


def fetch_top_pages(
    service: Any,
    site_url: str,
    start_date: str,
    end_date: str,
    row_limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch top pages by clicks."""
    response = (
        service.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": row_limit,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            },
        )
        .execute()
    )

    pages = []
    for row in response.get("rows", []):
        pages.append(
            {
                "page": row["keys"][0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0.0)), 4),
                "position": round(float(row.get("position", 0.0)), 1),
            }
        )
    return pages


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Search Console data for aaroneden.com."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to config.yaml (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--date-range",
        choices=list(DATE_RANGE_DAYS.keys()),
        default=None,
        help="Date range to query (overrides config default)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Number of rows to fetch (overrides config limits.top_queries)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON (default: pretty-printed JSON)",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(
            f"Error: Config file not found: {args.config}\n"
            f"Expected at: {DEFAULT_CONFIG}",
            file=sys.stderr,
        )
        sys.exit(1)

    config = load_config(args.config)

    range_name = args.date_range or config.get("defaults", {}).get(
        "date_range", "last_28_days"
    )
    start_date, end_date = resolve_date_range(range_name)

    limits = config.get("limits", {})
    row_limit = args.rows or int(limits.get("top_queries", 20))

    site_url = config.get("site_url", "")
    if not site_url:
        print(
            "Error: site_url not configured in config.yaml.\n"
            "Set it to your Search Console property (e.g. sc-domain:aaroneden.com).",
            file=sys.stderr,
        )
        sys.exit(1)

    credentials_path = resolve_credentials(config)
    service = build_service(credentials_path)

    print(
        f"Fetching Search Console data: {start_date} → {end_date} ...", file=sys.stderr
    )

    top_queries = fetch_top_queries(service, site_url, start_date, end_date, row_limit)
    top_pages = fetch_top_pages(service, site_url, start_date, end_date, row_limit)

    result = {
        "period": {"start": start_date, "end": end_date, "range": range_name},
        "top_queries": top_queries,
        "top_pages": top_pages,
    }

    indent = None if args.json else 2
    print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
