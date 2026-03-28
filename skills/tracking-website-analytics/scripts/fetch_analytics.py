#!/usr/bin/env python3
"""
Fetch GA4 analytics data for aaroneden.com.

Queries the Google Analytics Data API for traffic overview, top pages,
and traffic sources for a configurable date range.

Usage:
    python3 fetch_analytics.py
    python3 fetch_analytics.py --date-range last_7_days
    python3 fetch_analytics.py --date-range last_28_days --json
    python3 fetch_analytics.py --config /path/to/config.yaml

Requires:
    uv pip install google-analytics-data google-auth pyyaml
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
    days = DATE_RANGE_DAYS.get(range_name, 28)
    end = date.today() - timedelta(days=1)  # GA4 data lags ~1 day
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# GA4 API queries
# ---------------------------------------------------------------------------


def build_client(credentials_path: Path) -> Any:
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient  # type: ignore
        from google.oauth2 import service_account  # type: ignore
    except ImportError:
        print(
            "Error: google-analytics-data not installed.\n"
            "Run: uv pip install google-analytics-data google-auth",
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
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def fetch_overview(
    client: Any,
    property_id: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Fetch traffic overview metrics."""
    from google.analytics.data_v1beta.types import (  # type: ignore
        DateRange,
        Metric,
        RunReportRequest,
    )

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
        ],
    )
    response = client.run_report(request)

    row = response.rows[0] if response.rows else None
    if not row:
        return {"sessions": 0, "users": 0, "pageviews": 0, "bounce_rate": 0.0}

    values = [v.value for v in row.metric_values]
    return {
        "sessions": int(values[0]),
        "users": int(values[1]),
        "pageviews": int(values[2]),
        "bounce_rate": round(float(values[3]), 4),
    }


def fetch_top_pages(
    client: Any,
    property_id: str,
    start_date: str,
    end_date: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch top pages by sessions."""
    from google.analytics.data_v1beta.types import (  # type: ignore
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)
        ],
        limit=limit,
    )
    response = client.run_report(request)

    pages = []
    for row in response.rows:
        pages.append(
            {
                "page": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "pageviews": int(row.metric_values[1].value),
                "avg_session_duration": round(float(row.metric_values[2].value), 1),
            }
        )
    return pages


def fetch_top_sources(
    client: Any,
    property_id: str,
    start_date: str,
    end_date: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch top traffic sources by sessions."""
    from google.analytics.data_v1beta.types import (  # type: ignore
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[Metric(name="sessions")],
        order_bys=[
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)
        ],
        limit=limit,
    )
    response = client.run_report(request)

    sources = []
    for row in response.rows:
        sources.append(
            {
                "source": row.dimension_values[0].value,
                "medium": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
            }
        )
    return sources


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch GA4 analytics for aaroneden.com."
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

    # Resolve date range
    range_name = args.date_range or config.get("defaults", {}).get(
        "date_range", "last_28_days"
    )
    start_date, end_date = resolve_date_range(range_name)

    # Resolve limits
    limits = config.get("limits", {})
    top_pages_limit = int(limits.get("top_pages", 10))
    top_sources_limit = int(limits.get("top_sources", 10))

    property_id = config.get("property_id", "")
    if not property_id or property_id == "properties/XXXXXXXXX":
        print(
            "Error: property_id not configured in config.yaml.\n"
            "Set it to your GA4 property ID (e.g. properties/123456789).",
            file=sys.stderr,
        )
        sys.exit(1)

    credentials_path = resolve_credentials(config)
    client = build_client(credentials_path)

    print(f"Fetching GA4 data: {start_date} → {end_date} ...", file=sys.stderr)

    overview = fetch_overview(client, property_id, start_date, end_date)
    top_pages = fetch_top_pages(
        client, property_id, start_date, end_date, top_pages_limit
    )
    top_sources = fetch_top_sources(
        client, property_id, start_date, end_date, top_sources_limit
    )

    result = {
        "period": {"start": start_date, "end": end_date, "range": range_name},
        "overview": overview,
        "top_pages": top_pages,
        "top_sources": top_sources,
    }

    indent = None if args.json else 2
    print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
