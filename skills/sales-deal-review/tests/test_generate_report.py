"""Tests for generate_report.py — deal report formatting."""

import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "sales-deal-review"),
)

from generate_report import _deal_section, format_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deal(
    name="Test Deal",
    org="Acme Corp",
    contact="John Doe",
    status="Open",
    deal_type="New Customer",
    base="bb",
    has_tasks=False,
    task_names=None,
):
    return {
        "id": "rec1",
        "name": name,
        "status": status,
        "type": deal_type,
        "base": base,
        "organization_name": org,
        "primary_contact_name": contact,
        "task_ids": ["recT1"] if has_tasks else [],
        "task_names": task_names or (["Follow up"] if has_tasks else []),
        "has_active_tasks": has_tasks,
        "airtable_url": "https://airtable.com/app/tbl/rec1",
    }


# ---------------------------------------------------------------------------
# TestDealSection
# ---------------------------------------------------------------------------


class TestDealSection:
    """_deal_section() formats groups of deals."""

    def test_deals_needing_action(self):
        # Arrange
        deals = [_make_deal(has_tasks=False)]

        # Act
        lines = _deal_section(deals, "New Customer")

        # Assert
        output = "\n".join(lines)
        assert "NEEDS NEXT ACTION" in output
        assert "Acme Corp" in output

    def test_deals_with_active_tasks(self):
        # Arrange
        deals = [_make_deal(has_tasks=True, task_names=["Task A", "Task B"])]

        # Act
        lines = _deal_section(deals, "Section")

        # Assert
        output = "\n".join(lines)
        assert "HAS ACTIVE TASKS" in output
        assert "Task A" in output

    def test_empty_deals(self):
        # Act
        lines = _deal_section([], "Section")

        # Assert
        output = "\n".join(lines)
        assert "No open deals." in output

    def test_task_list_truncation(self):
        # Arrange
        tasks = ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]
        deals = [_make_deal(has_tasks=True, task_names=tasks)]

        # Act
        lines = _deal_section(deals, "Section")

        # Assert
        output = "\n".join(lines)
        assert "(+2 more)" in output

    def test_mixed_deals(self):
        # Arrange
        deals = [
            _make_deal(org="Needs Action Inc", has_tasks=False),
            _make_deal(org="Has Tasks LLC", has_tasks=True),
        ]

        # Act
        lines = _deal_section(deals, "Mixed")

        # Assert
        output = "\n".join(lines)
        assert "NEEDS NEXT ACTION (1)" in output
        assert "HAS ACTIVE TASKS (1)" in output


# ---------------------------------------------------------------------------
# TestFormatReport
# ---------------------------------------------------------------------------


class TestFormatReport:
    """format_report() produces the full markdown report."""

    def test_full_report_structure(self):
        # Arrange
        data = {
            "deals": [
                _make_deal(deal_type="New Customer", base="bb"),
                _make_deal(deal_type="Sponsor", base="aitb"),
            ],
            "summary": {
                "total_deals": 2,
                "deals_with_tasks": 0,
                "deals_without_tasks": 2,
                "bb": {
                    "total": 1,
                    "without_tasks": 1,
                    "by_type": {"New Customer": {"total": 1, "without_tasks": 1}},
                },
                "aitb": {"total": 1, "without_tasks": 1},
            },
        }

        # Act
        report = format_report(data)

        # Assert
        assert "Deal Review" in report
        assert "BRAIN BRIDGE" in report
        assert "AI TRAILBLAZERS" in report
        assert "Total open deals: 2" in report

    def test_empty_deals(self):
        # Arrange
        data = {
            "deals": [],
            "summary": {
                "total_deals": 0,
                "deals_with_tasks": 0,
                "deals_without_tasks": 0,
                "bb": {"total": 0, "without_tasks": 0, "by_type": {}},
                "aitb": {"total": 0, "without_tasks": 0},
            },
        }

        # Act
        report = format_report(data)

        # Assert
        assert "Total open deals: 0" in report
        assert "No open BB deals." in report

    def test_bb_by_type_breakdown(self):
        # Arrange
        data = {
            "deals": [
                _make_deal(deal_type="Partner", base="bb"),
            ],
            "summary": {
                "total_deals": 1,
                "deals_with_tasks": 0,
                "deals_without_tasks": 1,
                "bb": {
                    "total": 1,
                    "without_tasks": 1,
                    "by_type": {"Partner": {"total": 1, "without_tasks": 1}},
                },
                "aitb": {"total": 0, "without_tasks": 0},
            },
        }

        # Act
        report = format_report(data)

        # Assert
        assert "Partner" in report
        assert "BB breakdown:" in report

    def test_missing_fields_handled(self):
        # Arrange
        deal = _make_deal()
        deal["organization_name"] = "No Organization"
        deal["primary_contact_name"] = "No Contact"
        data = {
            "deals": [deal],
            "summary": {
                "total_deals": 1,
                "deals_with_tasks": 0,
                "deals_without_tasks": 1,
                "bb": {"total": 1, "without_tasks": 1, "by_type": {}},
                "aitb": {"total": 0, "without_tasks": 0},
            },
        }

        # Act
        report = format_report(data)

        # Assert
        assert "No Organization" in report
