"""Tests for search_jobs.py query generation, dedup, and heuristic logic."""

import json
import sys
from pathlib import Path

import pytest

# Add scripts to path
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent / "scripts" / "monitoring-job-listings"
)
sys.path.insert(0, str(SCRIPTS_DIR))

from search_jobs import (  # noqa: E402
    build_queries,
    is_job_listing,
    load_seen_listings,
    save_seen_listings,
)


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


class TestBuildQueries:
    def test_generates_queries_from_titles_and_locations(self):
        config = {
            "search_titles": ["AI Engineer", "Automation Lead"],
            "locations": ["Tucson, AZ", "Remote"],
            "negative_keywords": ["junior"],
        }
        queries = build_queries(config)
        assert len(queries) == 4  # 2 titles x 2 locations
        assert all(isinstance(q, str) for q in queries)

    def test_includes_negative_keywords(self):
        config = {
            "search_titles": ["AI Engineer"],
            "locations": ["Remote"],
            "negative_keywords": ["junior", "intern"],
        }
        queries = build_queries(config)
        assert len(queries) == 1
        assert '-"junior"' in queries[0]
        assert '-"intern"' in queries[0]

    def test_limits_negative_keywords_to_five(self):
        config = {
            "search_titles": ["Engineer"],
            "locations": ["Remote"],
            "negative_keywords": ["a", "b", "c", "d", "e", "f", "g"],
        }
        queries = build_queries(config)
        # Should only include first 5 negative keywords
        neg_count = queries[0].count('-"')
        assert neg_count == 5

    def test_empty_titles_returns_empty(self):
        config = {"search_titles": [], "locations": ["Remote"], "negative_keywords": []}
        queries = build_queries(config)
        assert queries == []

    def test_empty_locations_returns_empty(self):
        config = {
            "search_titles": ["Engineer"],
            "locations": [],
            "negative_keywords": [],
        }
        queries = build_queries(config)
        assert queries == []

    def test_no_negative_keywords(self):
        config = {
            "search_titles": ["Engineer"],
            "locations": ["Remote"],
            "negative_keywords": [],
        }
        queries = build_queries(config)
        assert len(queries) == 1
        assert "-" not in queries[0]


# ---------------------------------------------------------------------------
# Job listing heuristic
# ---------------------------------------------------------------------------


class TestIsJobListing:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.linkedin.com/jobs/view/12345",
            "https://www.indeed.com/viewjob?jk=abc123",
            "https://www.glassdoor.com/job-listing/ai-engineer",
            "https://jobs.lever.co/company/position-id",
            "https://boards.greenhouse.io/company/jobs/123",
            "https://company.com/careers/ai-engineer",
            "https://company.com/jobs/12345",
            "https://wellfound.com/jobs",
        ],
    )
    def test_recognizes_job_urls(self, url):
        assert is_job_listing({"url": url}) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://en.wikipedia.org/wiki/Job",
            "https://www.google.com/search?q=ai+engineer",
            "https://www.nytimes.com/article/ai-jobs",
            "https://twitter.com/someone/status/123",
            "https://company.com/blog/hiring-update",
        ],
    )
    def test_rejects_non_job_urls(self, url):
        assert is_job_listing({"url": url}) is False

    def test_handles_empty_url(self):
        assert is_job_listing({"url": ""}) is False

    def test_handles_missing_url(self):
        assert is_job_listing({}) is False


# ---------------------------------------------------------------------------
# Seen listings persistence
# ---------------------------------------------------------------------------


class TestSeenListings:
    def test_load_returns_empty_set_for_missing_file(self, tmp_path):
        result = load_seen_listings(tmp_path / "nonexistent.json")
        assert result == set()

    def test_load_returns_empty_set_for_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        result = load_seen_listings(bad_file)
        assert result == set()

    def test_roundtrip_save_and_load(self, tmp_path):
        seen_file = tmp_path / "seen.json"
        urls = {"https://example.com/job/1", "https://example.com/job/2"}

        save_seen_listings(seen_file, urls)
        loaded = load_seen_listings(seen_file)

        assert loaded == urls

    def test_save_creates_parent_dirs(self, tmp_path):
        seen_file = tmp_path / "nested" / "dir" / "seen.json"
        save_seen_listings(seen_file, {"https://example.com/job/1"})
        assert seen_file.exists()

    def test_save_includes_sorted_urls(self, tmp_path):
        seen_file = tmp_path / "seen.json"
        urls = {"https://z.com", "https://a.com", "https://m.com"}
        save_seen_listings(seen_file, urls)

        data = json.loads(seen_file.read_text())
        assert data["urls"] == ["https://a.com", "https://m.com", "https://z.com"]

    def test_save_includes_date(self, tmp_path):
        seen_file = tmp_path / "seen.json"
        save_seen_listings(seen_file, set())

        data = json.loads(seen_file.read_text())
        assert "updated" in data
