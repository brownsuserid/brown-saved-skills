"""Tests for scan_sops.py — SOP frontmatter parsing and review status."""

import os
import sys
from datetime import date, timedelta

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "maintaining-sops"),
)

import scan_sops


# ---------------------------------------------------------------------------
# TestParseFrontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    """parse_frontmatter() extracts key-value pairs from YAML."""

    def test_valid_frontmatter(self):
        # Arrange
        text = '---\ntitle: "My SOP"\nowner: Aaron\nnext-review: 2026-03-01\n---\n\n# Content'

        # Act
        result = scan_sops.parse_frontmatter(text)

        # Assert
        assert result["title"] == "My SOP"
        assert result["owner"] == "Aaron"
        assert result["next-review"] == "2026-03-01"

    def test_no_frontmatter(self):
        # Arrange
        text = "# Just a heading\nSome content"

        # Act
        result = scan_sops.parse_frontmatter(text)

        # Assert
        assert result == {}

    def test_empty_values_skipped(self):
        # Arrange
        text = "---\ntitle: Test\nempty_field:\n---\n"

        # Act
        result = scan_sops.parse_frontmatter(text)

        # Assert
        assert "title" in result
        assert "empty_field" not in result

    def test_quoted_values(self):
        # Arrange
        text = '---\ntitle: "Quoted Value"\n---\n'

        # Act
        result = scan_sops.parse_frontmatter(text)

        # Assert
        assert result["title"] == "Quoted Value"


# ---------------------------------------------------------------------------
# TestDetermineState
# ---------------------------------------------------------------------------


class TestDetermineState:
    """determine_state() classifies SOP review status."""

    def test_ok_future_review(self):
        # Arrange
        fm = {"next-review": (date.today() + timedelta(days=30)).isoformat()}

        # Act
        result = scan_sops.determine_state(fm, date.today())

        # Assert
        assert result == "ok"

    def test_overdue_past_review(self):
        # Arrange
        fm = {"next-review": (date.today() - timedelta(days=1)).isoformat()}

        # Act
        result = scan_sops.determine_state(fm, date.today())

        # Assert
        assert result == "overdue"

    def test_overdue_today(self):
        # Arrange
        fm = {"next-review": date.today().isoformat()}

        # Act
        result = scan_sops.determine_state(fm, date.today())

        # Assert
        assert result == "overdue"

    def test_missing_frontmatter(self):
        # Arrange — no next-review key
        fm = {"title": "SOP without review date"}

        # Act
        result = scan_sops.determine_state(fm, date.today())

        # Assert
        assert result == "missing_frontmatter"

    def test_invalid_date_format(self):
        # Arrange
        fm = {"next-review": "not-a-date"}

        # Act
        result = scan_sops.determine_state(fm, date.today())

        # Assert
        assert result == "missing_frontmatter"


# ---------------------------------------------------------------------------
# TestScanSops
# ---------------------------------------------------------------------------


class TestScanSops:
    """scan_sops() walks directory and reports review status."""

    def test_scans_markdown_files(self, tmp_path):
        # Arrange
        future = (date.today() + timedelta(days=30)).isoformat()
        sop = tmp_path / "deploy-process.md"
        sop.write_text(
            f"---\ntitle: Deploy Process\nnext-review: {future}\n---\n# Deploy"
        )

        # Act
        result = scan_sops.scan_sops(str(tmp_path))

        # Assert
        assert result["total"] == 1
        assert result["sops"][0]["state"] == "ok"
        assert result["summary"]["ok"] == 1

    def test_mixed_states(self, tmp_path):
        # Arrange
        future = (date.today() + timedelta(days=30)).isoformat()
        past = (date.today() - timedelta(days=10)).isoformat()

        (tmp_path / "ok-sop.md").write_text(f"---\nnext-review: {future}\n---\n")
        (tmp_path / "overdue-sop.md").write_text(f"---\nnext-review: {past}\n---\n")
        (tmp_path / "missing-sop.md").write_text("# No frontmatter\n")

        # Act
        result = scan_sops.scan_sops(str(tmp_path))

        # Assert
        assert result["total"] == 3
        assert result["summary"]["ok"] == 1
        assert result["summary"]["overdue"] == 1
        assert result["summary"]["missing_frontmatter"] == 1

    def test_skips_underscore_files(self, tmp_path):
        # Arrange
        (tmp_path / "_template.md").write_text("---\ntitle: Template\n---\n")
        (tmp_path / "real-sop.md").write_text(
            "---\ntitle: Real\nnext-review: 2030-01-01\n---\n"
        )

        # Act
        result = scan_sops.scan_sops(str(tmp_path))

        # Assert
        assert result["total"] == 1

    def test_skips_non_markdown(self, tmp_path):
        # Arrange
        (tmp_path / "notes.txt").write_text("not a markdown file")
        (tmp_path / "real.md").write_text("---\nnext-review: 2030-01-01\n---\n")

        # Act
        result = scan_sops.scan_sops(str(tmp_path))

        # Assert
        assert result["total"] == 1

    def test_missing_directory(self, tmp_path):
        # Act
        result = scan_sops.scan_sops(str(tmp_path / "nonexistent"))

        # Assert
        assert result["total"] == 0
        assert "error" in result

    def test_nested_directory(self, tmp_path):
        # Arrange
        subdir = tmp_path / "category"
        subdir.mkdir()
        (subdir / "nested-sop.md").write_text("---\nnext-review: 2030-01-01\n---\n")

        # Act
        result = scan_sops.scan_sops(str(tmp_path))

        # Assert
        assert result["total"] == 1
        assert "category" in result["sops"][0]["file"]
