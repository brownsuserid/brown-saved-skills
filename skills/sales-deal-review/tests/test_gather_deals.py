"""Tests for gather_deals.py -- Airtable deal gathering and aggregation."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "sales-deal-review"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

import gather_deals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "_shared"
    / "configs"
    / "all.yaml"
)


def _load_test_config() -> dict:
    """Load the real YAML config for test use."""
    from airtable_config import load_config

    return load_config(str(_CONFIG_PATH))


def _test_headers() -> dict:
    return {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


def _make_airtable_response(records, offset=None):
    """Build a fake Airtable response body."""
    body = {"records": records}
    if offset:
        body["offset"] = offset
    return json.dumps(body).encode()


def _mock_urlopen(response_bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_deal(
    deal_id="rec1", name="Test Deal", status="Open", deal_type="New Business"
):
    """Create mock deal with Aaron as assignee (required for BB filter)."""
    config = _load_test_config()
    deal_cfg = gather_deals.build_deal_config(config, "bb")
    return {
        "id": deal_id,
        "fields": {
            deal_cfg["deal_name_field"]: name,
            deal_cfg["deal_status_field"]: status,
            deal_cfg["deal_type_field"]: deal_type,
            deal_cfg["deal_org_field"]: [],
            deal_cfg["deal_contact_field"]: [],
            deal_cfg["deal_tasks_field"]: [],
            # Include Aaron's BB record ID so deal passes assignee filter
            deal_cfg["deal_assignee_field"]: [deal_cfg["aaron_id"]],
        },
    }


def _bb_deal_cfg():
    config = _load_test_config()
    return gather_deals.build_deal_config(config, "bb")


# ---------------------------------------------------------------------------
# TestFetchRecords
# ---------------------------------------------------------------------------


class TestFetchRecords:
    """fetch_records() paginates through Airtable API responses."""

    @patch("urllib.request.urlopen")
    def test_single_page(self, mock_urlopen_fn):
        # Arrange
        records = [{"id": "rec1", "fields": {"Name": "A"}}]
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response(records))

        # Act
        result = gather_deals.fetch_records("appXXX", "tblXXX", _test_headers())

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "rec1"

    @patch("urllib.request.urlopen")
    def test_pagination_follows_offset(self, mock_urlopen_fn):
        # Arrange
        page1 = _make_airtable_response(
            [{"id": "rec1", "fields": {}}], offset="cursor1"
        )
        page2 = _make_airtable_response([{"id": "rec2", "fields": {}}])
        mock_urlopen_fn.side_effect = [
            _mock_urlopen(page1),
            _mock_urlopen(page2),
        ]

        # Act
        result = gather_deals.fetch_records("appXXX", "tblXXX", _test_headers())

        # Assert
        assert len(result) == 2
        assert mock_urlopen_fn.call_count == 2

    @patch("urllib.request.urlopen")
    def test_empty_results(self, mock_urlopen_fn):
        # Arrange
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response([]))

        # Act
        result = gather_deals.fetch_records("appXXX", "tblXXX", _test_headers())

        # Assert
        assert result == []

    @patch("urllib.request.urlopen")
    def test_formula_filter_passed(self, mock_urlopen_fn):
        # Arrange
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response([]))

        # Act
        gather_deals.fetch_records(
            "appXXX", "tblXXX", _test_headers(), formula="Status!='Closed'"
        )

        # Assert
        call_args = mock_urlopen_fn.call_args
        url = call_args[0][0].full_url
        assert "filterByFormula" in url


# ---------------------------------------------------------------------------
# TestGatherDealsForBase
# ---------------------------------------------------------------------------


class TestGatherDealsForBase:
    """gather_deals_for_base() fetches and processes deals from a single base."""

    @patch("gather_deals.lookup_record")
    @patch("gather_deals.fetch_records")
    def test_bb_deal_returns_correct_structure(self, mock_fetch, mock_lookup):
        # Arrange
        deal_cfg = _bb_deal_cfg()
        mock_fetch.side_effect = [
            [_make_deal()],  # deals
            [],  # tasks
        ]
        mock_lookup.return_value = None

        # Act
        result = gather_deals.gather_deals_for_base("bb", deal_cfg, _test_headers())

        # Assert
        assert len(result) == 1
        deal = result[0]
        assert deal["name"] == "Test Deal"
        assert deal["base"] == "bb"
        assert deal["type"] == "New Customer"
        assert "airtable_url" in deal

    @patch("gather_deals.lookup_record")
    @patch("gather_deals.fetch_records")
    def test_deal_with_active_tasks(self, mock_fetch, mock_lookup):
        # Arrange - deal must have task IDs in its Tasks field
        deal_cfg = _bb_deal_cfg()
        deal = _make_deal(deal_id="recDeal1")
        deal["fields"][deal_cfg["deal_tasks_field"]] = ["recTask1"]
        task = {
            "id": "recTask1",
            "fields": {
                "Task": "Follow up",
                "Status": "In Progress",
            },
        }
        mock_fetch.side_effect = [
            [deal],  # deals
            [task],  # tasks (batch-fetched by ID from deal's Tasks field)
        ]
        mock_lookup.return_value = None

        # Act
        result = gather_deals.gather_deals_for_base("bb", deal_cfg, _test_headers())

        # Assert
        assert result[0]["has_active_tasks"] is True
        assert "Follow up" in result[0]["task_names"]

    @patch("gather_deals.lookup_record")
    @patch("gather_deals.fetch_records")
    def test_bb_org_contact_lookup(self, mock_fetch, mock_lookup):
        # Arrange
        deal_cfg = _bb_deal_cfg()
        deal = _make_deal()
        deal["fields"][deal_cfg["deal_org_field"]] = ["recOrg1"]
        deal["fields"][deal_cfg["deal_contact_field"]] = [
            "recDealContact1"  # Junction table record ID
        ]
        mock_fetch.side_effect = [[deal], []]
        # BB contact lookup goes through junction table:
        # 1st call: org name lookup
        # 2nd call: junction table -> returns Contact field (list of record IDs)
        # 3rd call: actual contact name lookup
        mock_lookup.side_effect = ["Acme Corp", ["recContact1"], "John Doe"]

        # Act
        result = gather_deals.gather_deals_for_base("bb", deal_cfg, _test_headers())

        # Assert
        assert result[0]["organization_name"] == "Acme Corp"
        assert result[0]["primary_contact_name"] == "John Doe"

    @patch("gather_deals.lookup_record")
    @patch("gather_deals.fetch_records")
    def test_completed_tasks_excluded(self, mock_fetch, mock_lookup):
        # Arrange - deal must have task ID in its Tasks field
        deal_cfg = _bb_deal_cfg()
        deal = _make_deal(deal_id="recD1")
        deal["fields"][deal_cfg["deal_tasks_field"]] = ["recT1"]
        task = {
            "id": "recT1",
            "fields": {
                "Task": "Done task",
                "Status": "Completed",
            },
        }
        mock_fetch.side_effect = [[deal], [task]]
        mock_lookup.return_value = None

        # Act
        result = gather_deals.gather_deals_for_base("bb", deal_cfg, _test_headers())

        # Assert - completed tasks are excluded from active tasks
        assert result[0]["has_active_tasks"] is False


# ---------------------------------------------------------------------------
# TestGatherAllDeals
# ---------------------------------------------------------------------------


class TestGatherAllDeals:
    """gather_all_deals() aggregates across all bases."""

    @patch("gather_deals.gather_deals_for_base")
    def test_multi_base_aggregation(self, mock_gather):
        # Arrange
        config = _load_test_config()
        bb_deal = {"base": "bb", "type": "New Customer", "has_active_tasks": False}
        aitb_deal = {"base": "aitb", "type": "Sponsor", "has_active_tasks": True}
        mock_gather.side_effect = [[bb_deal], [aitb_deal]]

        # Act
        result = gather_deals.gather_all_deals(config)

        # Assert
        assert result["summary"]["total_deals"] == 2
        assert result["summary"]["deals_with_tasks"] == 1
        assert result["summary"]["deals_without_tasks"] == 1

    @patch("gather_deals.gather_deals_for_base")
    def test_single_base_failure_continues(self, mock_gather):
        # Arrange
        config = _load_test_config()
        mock_gather.side_effect = [
            Exception("API error"),
            [{"base": "aitb", "type": "Sponsor", "has_active_tasks": False}],
        ]

        # Act
        result = gather_deals.gather_all_deals(config)

        # Assert
        assert result["summary"]["total_deals"] == 1

    @patch("gather_deals.gather_deals_for_base")
    def test_bb_by_type_summary(self, mock_gather):
        # Arrange
        config = _load_test_config()
        deals = [
            {"base": "bb", "type": "New Customer", "has_active_tasks": False},
            {"base": "bb", "type": "New Customer", "has_active_tasks": True},
            {"base": "bb", "type": "Partner", "has_active_tasks": False},
        ]
        mock_gather.side_effect = [deals, []]

        # Act
        result = gather_deals.gather_all_deals(config)

        # Assert
        by_type = result["summary"]["bb"]["by_type"]
        assert by_type["New Customer"]["total"] == 2
        assert by_type["New Customer"]["without_tasks"] == 1
        assert by_type["Partner"]["total"] == 1
