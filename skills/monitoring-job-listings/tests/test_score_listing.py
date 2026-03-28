"""Tests for score_listing.py scoring logic."""

import sys
from pathlib import Path

import pytest

# Add scripts to path
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent / "scripts" / "monitoring-job-listings"
)
sys.path.insert(0, str(SCRIPTS_DIR))

from score_listing import filter_and_sort, score_listing  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    """Standard config matching production config.yaml."""
    return {
        "locations": ["Tucson, AZ", "Phoenix, AZ", "Arizona", "Remote"],
        "negative_keywords": [
            "junior",
            "intern",
            "entry-level",
            "associate",
            "coordinator",
        ],
        "salary_min": 120000,
        "scoring_weights": {
            "ai_automation": 3,
            "leadership": 2,
            "location_match": 2,
            "startup": 1,
            "consulting": 1,
            "salary_match": 1,
        },
        "negative_weights": {
            "junior_role": -3,
            "degree_mismatch": -2,
        },
    }


def make_listing(title="", snippet="", location=""):
    return {
        "title": title,
        "url": "https://example.com/job/1",
        "description_snippet": snippet,
        "location": location,
    }


# ---------------------------------------------------------------------------
# AI/Automation scoring
# ---------------------------------------------------------------------------


class TestAIAutomationScoring:
    def test_ai_keyword_in_title(self, config):
        listing = make_listing(title="AI Operations Lead")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("ai_automation") == 3

    def test_llm_keyword_in_snippet(self, config):
        listing = make_listing(title="Engineer", snippet="building llm-powered tools")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("ai_automation") == 3

    def test_no_ai_keywords(self, config):
        listing = make_listing(title="Marketing Manager")
        result = score_listing(listing, config)
        assert "ai_automation" not in result["score_breakdown"]

    def test_automation_keyword(self, config):
        listing = make_listing(title="Workflow Automation Engineer")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("ai_automation") == 3


# ---------------------------------------------------------------------------
# Leadership scoring
# ---------------------------------------------------------------------------


class TestLeadershipScoring:
    def test_director_in_title(self, config):
        listing = make_listing(title="Director of Engineering")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("leadership") == 2

    def test_senior_in_title(self, config):
        listing = make_listing(title="Senior AI Engineer")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("leadership") == 2

    def test_leadership_not_in_snippet(self, config):
        """Leadership keywords only count in title, not snippet."""
        listing = make_listing(title="Engineer", snippet="reports to a director")
        result = score_listing(listing, config)
        assert "leadership" not in result["score_breakdown"]


# ---------------------------------------------------------------------------
# Location scoring
# ---------------------------------------------------------------------------


class TestLocationScoring:
    def test_location_field_match(self, config):
        listing = make_listing(title="Engineer", location="Tucson, AZ")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("location_match") == 2

    def test_remote_in_snippet(self, config):
        listing = make_listing(title="Engineer", snippet="fully remote position")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("location_match") == 2

    def test_no_location_match(self, config):
        listing = make_listing(title="Engineer", location="New York, NY")
        result = score_listing(listing, config)
        assert "location_match" not in result["score_breakdown"]


# ---------------------------------------------------------------------------
# Startup and consulting scoring
# ---------------------------------------------------------------------------


class TestStartupConsultingScoring:
    def test_startup_signal(self, config):
        listing = make_listing(title="AI Lead", snippet="join our series a startup")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("startup") == 1

    def test_consulting_keyword(self, config):
        listing = make_listing(
            title="AI Consultant", snippet="client-facing advisory role"
        )
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("consulting") == 1


# ---------------------------------------------------------------------------
# Salary scoring
# ---------------------------------------------------------------------------


class TestSalaryScoring:
    def test_salary_above_min(self, config):
        listing = make_listing(
            title="Engineer", snippet="salary range $150,000 - $180,000"
        )
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("salary_match") == 1

    def test_salary_below_min(self, config):
        listing = make_listing(title="Engineer", snippet="salary $90,000")
        result = score_listing(listing, config)
        assert "salary_match" not in result["score_breakdown"]

    def test_no_salary_mentioned(self, config):
        listing = make_listing(title="Engineer", snippet="competitive pay")
        result = score_listing(listing, config)
        assert "salary_match" not in result["score_breakdown"]

    def test_salary_min_zero_skips_check(self, config):
        config["salary_min"] = 0
        listing = make_listing(title="Engineer", snippet="salary $50,000")
        result = score_listing(listing, config)
        assert "salary_match" not in result["score_breakdown"]


# ---------------------------------------------------------------------------
# Negative scoring
# ---------------------------------------------------------------------------


class TestNegativeScoring:
    def test_junior_keyword_penalty(self, config):
        listing = make_listing(title="Junior AI Developer")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("junior_role") == -3

    def test_intern_keyword_penalty(self, config):
        listing = make_listing(title="AI Intern")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("junior_role") == -3

    def test_degree_mismatch_penalty(self, config):
        listing = make_listing(title="Engineer", snippet="bachelor's degree required")
        result = score_listing(listing, config)
        assert result["score_breakdown"].get("degree_mismatch") == -2

    def test_degree_with_equivalent_no_penalty(self, config):
        listing = make_listing(
            title="Engineer",
            snippet="bachelor's degree required or equivalent experience",
        )
        result = score_listing(listing, config)
        assert "degree_mismatch" not in result["score_breakdown"]


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


class TestCompositeScoring:
    def test_high_score_listing(self, config):
        """AI + leadership + location + startup = 8 points."""
        listing = make_listing(
            title="Senior AI Operations Lead",
            snippet="join our series a startup, fully remote, building agentic workflows",
            location="Remote",
        )
        result = score_listing(listing, config)
        assert result["score"] >= 7

    def test_low_score_listing(self, config):
        """No matching keywords = 0."""
        listing = make_listing(
            title="Retail Associate",
            snippet="part-time retail position in store",
            location="Miami, FL",
        )
        result = score_listing(listing, config)
        assert result["score"] <= 0

    def test_mixed_positive_negative(self, config):
        """AI match but junior penalty."""
        listing = make_listing(
            title="Junior AI Developer", snippet="entry-level machine learning role"
        )
        result = score_listing(listing, config)
        # AI (+3) + junior (-3) = 0
        assert result["score"] == 0


# ---------------------------------------------------------------------------
# Filter and sort
# ---------------------------------------------------------------------------


class TestFilterAndSort:
    def test_filters_below_min_score(self, config):
        listings = [
            {"title": "A", "score": 6},
            {"title": "B", "score": 3},
            {"title": "C", "score": 5},
        ]
        result = filter_and_sort(listings, min_score=4)
        assert len(result) == 2
        assert result[0]["title"] == "A"
        assert result[1]["title"] == "C"

    def test_empty_list(self, config):
        result = filter_and_sort([], min_score=4)
        assert result == []

    def test_all_below_threshold(self, config):
        listings = [{"title": "A", "score": 1}, {"title": "B", "score": 2}]
        result = filter_and_sort(listings, min_score=4)
        assert result == []
