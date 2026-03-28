"""Tests for score_content.py — verifies scoring logic, boosts, and frontmatter parsing.

All tests use deterministic inputs to avoid time-dependent flakiness.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ruff: noqa: E402
SCRIPT_DIR = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "scoring-content"
)
sys.path.insert(0, str(SCRIPT_DIR))

import score_content


class TestParseFrontmatter:
    """parse_frontmatter() extracts YAML from markdown files."""

    def test_parses_valid_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntitle: Hello World\nauthor: Test\n---\n\n# Content")

        result = score_content.parse_frontmatter(md)

        assert result["title"] == "Hello World"
        assert result["author"] == "Test"

    def test_returns_empty_dict_without_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Just Markdown\n\nNo frontmatter here.")

        result = score_content.parse_frontmatter(md)

        assert result == {}

    def test_returns_empty_dict_on_invalid_yaml(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\n: invalid: yaml: [[\n---\n")

        result = score_content.parse_frontmatter(md)

        assert result == {}

    def test_handles_empty_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\n\n---\n\n# Content")

        result = score_content.parse_frontmatter(md)

        assert result == {}

    def test_handles_nested_yaml(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntitle: Test\nmetadata:\n  key1: val1\n  key2: val2\n---\n")

        result = score_content.parse_frontmatter(md)

        assert result["title"] == "Test"
        assert result["metadata"]["key1"] == "val1"

    def test_handles_list_values(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntags:\n  - ai\n  - ml\n---\n")

        result = score_content.parse_frontmatter(md)

        assert result["tags"] == ["ai", "ml"]


class TestComputeCreatorBoost:
    """compute_creator_boost() matches creator against preferred list."""

    def test_exact_match_returns_boost(self):
        creators = [{"name": "Andrew Huberman", "weight_boost": 0.15}]

        result = score_content.compute_creator_boost("Andrew Huberman", creators)

        assert result == 0.15

    def test_case_insensitive_match(self):
        creators = [{"name": "Andrew Huberman", "weight_boost": 0.15}]

        result = score_content.compute_creator_boost("andrew huberman", creators)

        assert result == 0.15

    def test_partial_match_creator_in_preferred(self):
        creators = [{"name": "Huberman", "weight_boost": 0.1}]

        result = score_content.compute_creator_boost("Andrew Huberman Lab", creators)

        assert result == 0.1

    def test_partial_match_preferred_in_creator(self):
        creators = [{"name": "Andrew Huberman Lab Podcast", "weight_boost": 0.1}]

        result = score_content.compute_creator_boost("Huberman", creators)

        assert result == 0.1

    def test_no_match_returns_zero(self):
        creators = [{"name": "Andrew Huberman", "weight_boost": 0.15}]

        result = score_content.compute_creator_boost("Random Creator", creators)

        assert result == 0.0

    def test_empty_creator_returns_zero(self):
        creators = [{"name": "Andrew Huberman", "weight_boost": 0.15}]

        result = score_content.compute_creator_boost("", creators)

        assert result == 0.0

    def test_empty_preferred_list_returns_zero(self):
        result = score_content.compute_creator_boost("Some Creator", [])

        assert result == 0.0

    def test_none_creator_returns_zero(self):
        creators = [{"name": "Test", "weight_boost": 0.1}]

        result = score_content.compute_creator_boost(None, creators)

        assert result == 0.0

    def test_first_match_wins(self):
        creators = [
            {"name": "Huberman", "weight_boost": 0.1},
            {"name": "Andrew Huberman", "weight_boost": 0.2},
        ]

        result = score_content.compute_creator_boost("Andrew Huberman", creators)

        assert result == 0.1

    def test_missing_weight_boost_defaults_zero(self):
        creators = [{"name": "Test Creator"}]

        result = score_content.compute_creator_boost("Test Creator", creators)

        assert result == 0.0


class TestComputeRecencyBoost:
    """compute_recency_boost() applies time-based scoring."""

    def _date_str(self, days_ago: int) -> str:
        dt = datetime.now() - timedelta(days=days_ago)
        return dt.strftime("%Y-%m-%d")

    def test_very_recent_gets_full_boost(self):
        # Published today
        result = score_content.compute_recency_boost(self._date_str(0))
        assert result == pytest.approx(0.1, abs=0.01)

    def test_within_boost_window_gets_full_boost(self):
        # Published 2 days ago (within default 3-day window)
        result = score_content.compute_recency_boost(self._date_str(2))
        assert result == pytest.approx(0.1, abs=0.01)

    def test_old_content_gets_no_boost(self):
        # Published 30 days ago (well past 14-day decay)
        result = score_content.compute_recency_boost(self._date_str(30))
        assert result == 0.0

    def test_decay_period_gives_partial_boost(self):
        # Published ~8 days ago (midway in 3-14 day decay window)
        result = score_content.compute_recency_boost(self._date_str(8))
        assert 0.0 < result < 0.1

    def test_at_decay_boundary_gives_zero(self):
        result = score_content.compute_recency_boost(self._date_str(14))
        assert result == 0.0

    def test_empty_date_returns_zero(self):
        assert score_content.compute_recency_boost("") == 0.0

    def test_invalid_date_returns_zero(self):
        assert score_content.compute_recency_boost("not-a-date") == 0.0

    def test_none_date_returns_zero(self):
        assert score_content.compute_recency_boost(None) == 0.0

    def test_custom_boost_window(self):
        result = score_content.compute_recency_boost(
            self._date_str(5), boost_under_days=7
        )
        assert result == pytest.approx(0.1, abs=0.01)

    def test_custom_decay_window(self):
        # 20 days ago, default decay is 14 (= 0), but custom decay = 30
        result = score_content.compute_recency_boost(
            self._date_str(20), decay_after_days=30
        )
        assert result > 0.0

    def test_future_date_treated_as_zero_age(self):
        future = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        result = score_content.compute_recency_boost(future)
        assert result == pytest.approx(0.1, abs=0.01)

    def test_linear_decay_is_monotonic(self):
        """Boost should decrease as content gets older."""
        boosts = [
            score_content.compute_recency_boost(self._date_str(d)) for d in range(0, 20)
        ]
        # After initial flat period, values should be non-increasing
        for i in range(1, len(boosts)):
            assert boosts[i] <= boosts[i - 1] + 0.001  # small tolerance


class TestComputeFinalScore:
    """compute_final_score() combines components and clamps."""

    def test_basic_calculation(self):
        result = score_content.compute_final_score(
            topic_relevance=0.5,
            creator_boost=0.1,
            format_match=0.1,
            recency_boost=0.05,
            negative_penalty=0.0,
        )
        assert result == pytest.approx(0.75, abs=0.01)

    def test_clamped_to_max_1(self):
        result = score_content.compute_final_score(
            topic_relevance=0.9,
            creator_boost=0.2,
            format_match=0.2,
            recency_boost=0.1,
            negative_penalty=0.0,
        )
        assert result == 1.0

    def test_clamped_to_min_0(self):
        result = score_content.compute_final_score(
            topic_relevance=0.1,
            creator_boost=0.0,
            format_match=0.0,
            recency_boost=0.0,
            negative_penalty=0.8,
        )
        assert result == 0.0

    def test_negative_penalty_reduces_score(self):
        without = score_content.compute_final_score(0.5, 0.1, 0.1, 0.0, 0.0)
        with_penalty = score_content.compute_final_score(0.5, 0.1, 0.1, 0.0, 0.3)
        assert with_penalty < without

    def test_all_zeros(self):
        result = score_content.compute_final_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert result == 0.0

    @pytest.mark.parametrize(
        "topic,creator,fmt,recency,penalty,expected",
        [
            (0.8, 0.15, 0.1, 0.1, 0.0, 1.0),  # clamped at 1.0
            (0.6, 0.0, 0.0, 0.0, 0.0, 0.6),
            (0.4, 0.1, -0.1, 0.05, 0.2, 0.25),
        ],
    )
    def test_parametrized_scenarios(
        self, topic, creator, fmt, recency, penalty, expected
    ):
        result = score_content.compute_final_score(
            topic, creator, fmt, recency, penalty
        )
        assert result == pytest.approx(expected, abs=0.01)


class TestScoreItem:
    """score_item() produces deterministic scores and LLM assessment data."""

    def _write_profile(self, tmp_path: Path) -> Path:
        profile = tmp_path / "profile.md"
        profile.write_text(
            "---\n"
            "preferred_creators:\n"
            "  - name: Huberman\n"
            "    weight_boost: 0.15\n"
            "core_interests:\n"
            "  - topic: AI\n"
            "    weight: 0.9\n"
            "    keywords: [machine learning, neural networks]\n"
            "negative_signals:\n"
            "  - topic: Crypto scams\n"
            "    weight: 0.5\n"
            "    keywords: [pump and dump]\n"
            "content_preferences:\n"
            "  recency_bias:\n"
            "    boost_under_days: 3\n"
            "    decay_after_days: 14\n"
            "  preferred_formats: [podcast, article]\n"
            "  penalized_formats: [listicle]\n"
            "---\n"
        )
        return profile

    def _write_item(
        self, tmp_path: Path, creator: str = "Huberman", published: str = ""
    ) -> Path:
        if not published:
            published = datetime.now().strftime("%Y-%m-%d")
        item = tmp_path / "item.md"
        item.write_text(
            f"---\ntitle: Test Article\ncreator: {creator}\n"
            f"published: {published}\nsource: youtube\nurl: https://example.com\n---\n"
        )
        return item

    def test_returns_creator_boost_for_preferred_creator(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path, creator="Andrew Huberman")

        result = score_content.score_item(str(profile), str(item))

        assert result["deterministic_scores"]["creator_boost"] == 0.15

    def test_returns_zero_creator_boost_for_unknown(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path, creator="Unknown Person")

        result = score_content.score_item(str(profile), str(item))

        assert result["deterministic_scores"]["creator_boost"] == 0.0

    def test_returns_recency_boost_for_recent_item(self, tmp_path):
        profile = self._write_profile(tmp_path)
        today = datetime.now().strftime("%Y-%m-%d")
        item = self._write_item(tmp_path, published=today)

        result = score_content.score_item(str(profile), str(item))

        assert result["deterministic_scores"]["recency_boost"] == 0.1

    def test_returns_zero_recency_for_old_item(self, tmp_path):
        profile = self._write_profile(tmp_path)
        old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        item = self._write_item(tmp_path, published=old)

        result = score_content.score_item(str(profile), str(item))

        assert result["deterministic_scores"]["recency_boost"] == 0.0

    def test_includes_interests_for_llm(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path)

        result = score_content.score_item(str(profile), str(item))

        interests = result["llm_assessment_needed"]["interests"]
        assert len(interests) >= 1
        assert interests[0]["topic"] == "AI"
        assert interests[0]["weight"] == 0.9

    def test_includes_negative_signals_for_llm(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path)

        result = score_content.score_item(str(profile), str(item))

        negatives = result["llm_assessment_needed"]["negative_signals"]
        assert len(negatives) >= 1
        assert negatives[0]["topic"] == "Crypto scams"

    def test_includes_format_preferences(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path)

        result = score_content.score_item(str(profile), str(item))

        fmt = result["llm_assessment_needed"]["format_preferences"]
        assert "podcast" in fmt["preferred"]
        assert "listicle" in fmt["penalized"]

    def test_error_on_missing_profile(self, tmp_path):
        item = self._write_item(tmp_path)

        result = score_content.score_item("/nonexistent/profile.md", str(item))

        assert "error" in result

    def test_error_on_missing_item(self, tmp_path):
        profile = self._write_profile(tmp_path)

        result = score_content.score_item(str(profile), "/nonexistent/item.md")

        assert "error" in result

    def test_item_metadata_populated(self, tmp_path):
        profile = self._write_profile(tmp_path)
        item = self._write_item(tmp_path, creator="Test Author")

        result = score_content.score_item(str(profile), str(item))

        assert result["item"]["title"] == "Test Article"
        assert result["item"]["creator"] == "Test Author"
        assert result["item"]["source"] == "youtube"
