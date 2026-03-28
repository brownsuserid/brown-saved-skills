"""Tests for airtable_config.py — ensures done_statuses and field mappings are correct."""

import os
import sys
from pathlib import Path

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent / "_shared")
)

from airtable_config import get_bases, load_config

config = load_config()
BASES = get_bases(config)


class TestDoneStatuses:
    """Archived tasks must be excluded from all active task queries."""

    def test_personal_includes_archived(self):
        assert "Archived" in BASES["personal"]["done_statuses"]

    def test_aitb_includes_archived(self):
        assert "Archived" in BASES["aitb"]["done_statuses"]

    def test_bb_includes_archived(self):
        assert "Archived" in BASES["bb"]["done_statuses"]

    def test_all_bases_include_completed(self):
        for base_key, base_cfg in BASES.items():
            assert "Completed" in base_cfg["done_statuses"], (
                f"{base_key} missing 'Completed' in done_statuses"
            )

    def test_all_bases_include_cancelled(self):
        for base_key, base_cfg in BASES.items():
            assert "Cancelled" in base_cfg["done_statuses"], (
                f"{base_key} missing 'Cancelled' in done_statuses"
            )


class TestFieldMappings:
    """Every base must have a description_field mapped so tasks include it."""

    def test_all_bases_have_description_field(self):
        for base_key, base_cfg in BASES.items():
            assert "description_field" in base_cfg, (
                f"{base_key} missing description_field"
            )
            assert base_cfg["description_field"], (
                f"{base_key} has empty description_field"
            )

    def test_all_bases_have_notes_field(self):
        for base_key, base_cfg in BASES.items():
            assert "notes_field" in base_cfg, f"{base_key} missing notes_field"
            assert base_cfg["notes_field"], f"{base_key} has empty notes_field"

    def test_all_bases_have_for_today_field(self):
        for base_key, base_cfg in BASES.items():
            assert "for_today_field" in base_cfg, f"{base_key} missing for_today_field"

    def test_all_bases_have_size_field(self):
        for base_key, base_cfg in BASES.items():
            assert "size_field" in base_cfg, f"{base_key} missing size_field"
            assert base_cfg["size_field"], f"{base_key} has empty size_field"

    def test_all_bases_have_project_driver_field(self):
        for base_key, base_cfg in BASES.items():
            assert "project_driver_field" in base_cfg, (
                f"{base_key} missing project_driver_field"
            )

    def test_all_bases_have_project_mountain_field(self):
        for base_key, base_cfg in BASES.items():
            assert "project_mountain_field" in base_cfg, (
                f"{base_key} missing project_mountain_field"
            )

    def test_project_driver_field_values(self):
        assert BASES["personal"]["project_driver_field"] is None
        assert BASES["aitb"]["project_driver_field"] == "Driver"
        assert BASES["bb"]["project_driver_field"] == "Driver"

    def test_project_mountain_field_values(self):
        assert BASES["personal"]["project_mountain_field"] == "Mountains (30d)"
        assert BASES["aitb"]["project_mountain_field"] == "Mountains (30d)"
        assert BASES["bb"]["project_mountain_field"] == "Mountains"


class TestMountainGoalFields:
    """Every base must have mountain and goal resolution fields configured."""

    def test_all_bases_have_mountain_table_id(self):
        for base_key, base_cfg in BASES.items():
            assert "mountain_table_id" in base_cfg, (
                f"{base_key} missing mountain_table_id"
            )
            assert base_cfg["mountain_table_id"], (
                f"{base_key} has empty mountain_table_id"
            )

    def test_all_bases_have_mountain_name_field(self):
        for base_key, base_cfg in BASES.items():
            assert base_cfg.get("mountain_name_field") == "Title", (
                f"{base_key} mountain_name_field should be 'Title'"
            )

    def test_all_bases_have_mountain_goal_field(self):
        for base_key, base_cfg in BASES.items():
            assert "mountain_goal_field" in base_cfg, (
                f"{base_key} missing mountain_goal_field"
            )
            assert base_cfg["mountain_goal_field"], (
                f"{base_key} has empty mountain_goal_field"
            )

    def test_all_bases_have_mountain_goal_table_id(self):
        for base_key, base_cfg in BASES.items():
            assert "mountain_goal_table_id" in base_cfg, (
                f"{base_key} missing mountain_goal_table_id"
            )
            assert base_cfg["mountain_goal_table_id"], (
                f"{base_key} has empty mountain_goal_table_id"
            )

    def test_all_bases_have_mountain_goal_name_field(self):
        for base_key, base_cfg in BASES.items():
            assert "mountain_goal_name_field" in base_cfg, (
                f"{base_key} missing mountain_goal_name_field"
            )
            assert base_cfg["mountain_goal_name_field"], (
                f"{base_key} has empty mountain_goal_name_field"
            )

    def test_personal_mountain_goal_field(self):
        assert BASES["personal"]["mountain_goal_field"] == "1yr Goal"
        assert BASES["personal"]["mountain_goal_name_field"] == "Name"

    def test_aitb_mountain_goal_field(self):
        assert BASES["aitb"]["mountain_goal_field"] == "Objective"
        assert BASES["aitb"]["mountain_goal_name_field"] == "Name"

    def test_bb_mountain_goal_field(self):
        assert BASES["bb"]["mountain_goal_field"] == "Objective (1y)"
        assert BASES["bb"]["mountain_goal_name_field"] == "Objective"
