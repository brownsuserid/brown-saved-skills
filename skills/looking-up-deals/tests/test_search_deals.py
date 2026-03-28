"""Tests for search_deals.py — deal lookup with fuzzy matching."""

import json
import os
import sys
from unittest.mock import MagicMock, patch


# Add scripts dir to path so we can import the module
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "looking-up-deals"),
)

import search_deals

# Initialize config so DEAL_CONFIG is populated for tests
search_deals._ensure_config()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_bb_deal_record(
    record_id="recDeal1",
    name="Acme Phase 2",
    status="Proposal/Price Quote",
    deal_type="Existing Business",
    org="Acme Corp",
    contact="Jane Smith",
    amount=45000,
    description="Phase 2 engagement",
):
    return {
        "id": record_id,
        "fields": {
            "Name": name,
            "Status": status,
            "Type": deal_type,
            "Organization": org,
            "Deal Contacts": contact,
            "Amount": amount,
            "Description": description,
        },
    }


def _make_aitb_deal_record(
    record_id="recDeal1",
    title="AITB Sponsor Deal",
    stage="Interest Expressed",
    org_name=None,
    contact_name=None,
    deal_value=5000,
    description="Sponsor deal",
):
    return {
        "id": record_id,
        "fields": {
            "Project Title": title,
            "Stage": stage,
            "Organization Name": ["Sponsor Corp"] if org_name is None else org_name,
            "Contact": ["John Doe"] if contact_name is None else contact_name,
            "Deal Value": deal_value,
            "Description": description,
        },
    }


# ---------------------------------------------------------------------------
# TestNormalizeName
# ---------------------------------------------------------------------------


class TestNormalizeName:
    """normalize_name() strips non-alphanumeric chars and lowercases."""

    def test_basic(self):
        assert search_deals.normalize_name("Acme Corp") == "acmecorp"

    def test_special_chars(self):
        assert search_deals.normalize_name("Deal - Phase 2") == "dealphase2"

    def test_empty(self):
        assert search_deals.normalize_name("") == ""


# ---------------------------------------------------------------------------
# TestFuzzyScore
# ---------------------------------------------------------------------------


class TestFuzzyScore:
    """fuzzy_score() returns 0-100 based on string similarity."""

    def test_exact_match(self):
        assert search_deals.fuzzy_score("Acme Phase 2", "Acme Phase 2") == 100

    def test_query_in_target(self):
        assert search_deals.fuzzy_score("Acme", "Acme Corp Phase 2") == 90

    def test_target_in_query(self):
        assert search_deals.fuzzy_score("Acme Corp Phase 2", "Acme") == 80

    def test_no_match(self):
        assert search_deals.fuzzy_score("Alpha", "Zebra") == 0

    def test_empty_strings(self):
        assert search_deals.fuzzy_score("", "") == 0


# ---------------------------------------------------------------------------
# TestParseDealRecord
# ---------------------------------------------------------------------------


class TestParseBBDealRecord:
    """parse_deal_record() normalizes BB deal records."""

    def test_full_bb_record(self):
        # Arrange
        record = _make_bb_deal_record()
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appBB", "tblDeals")

        # Assert
        assert result["name"] == "Acme Phase 2"
        assert result["status"] == "Proposal/Price Quote"
        assert result["type"] == "Existing Customer"
        assert result["amount"] == 45000
        assert "airtable.com" in result["link"]

    def test_bb_type_display_mapping(self):
        # Arrange
        record = _make_bb_deal_record(deal_type="New Business")
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appBB", "tblD")

        # Assert
        assert result["type"] == "New Customer"

    def test_bb_partner_type(self):
        # Arrange
        record = _make_bb_deal_record(deal_type="Partner")
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appBB", "tblD")

        # Assert
        assert result["type"] == "Partner"

    def test_missing_optional_fields(self):
        # Arrange
        record = {"id": "recDeal1", "fields": {"Name": "Bare Deal"}}
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appBB", "tblD")

        # Assert
        assert result["name"] == "Bare Deal"
        assert result["status"] == ""
        assert result["amount"] is None


class TestParseAITBDealRecord:
    """parse_deal_record() normalizes AITB sponsor deal records."""

    def test_full_aitb_record(self):
        # Arrange
        record = _make_aitb_deal_record()
        config = search_deals.DEAL_CONFIG["aitb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appAITB", "tblDeals")

        # Assert
        assert result["name"] == "AITB Sponsor Deal"
        assert result["status"] == "Interest Expressed"
        assert result["type"] == "Sponsor"
        assert result["organization"] == "Sponsor Corp"
        assert result["primary_contact"] == "John Doe"
        assert result["amount"] == 5000

    def test_aitb_multi_org_lookup(self):
        # Arrange — lookup field returns multiple values
        record = _make_aitb_deal_record(org_name=["Org A", "Org B"])
        config = search_deals.DEAL_CONFIG["aitb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appAITB", "tblDeals")

        # Assert
        assert "Org A" in result["organization"]
        assert "Org B" in result["organization"]

    def test_aitb_empty_lookup_fields(self):
        # Arrange
        record = _make_aitb_deal_record(org_name=[], contact_name=[])
        config = search_deals.DEAL_CONFIG["aitb"]

        # Act
        result = search_deals.parse_deal_record(record, config, "appAITB", "tblDeals")

        # Assert
        assert result["organization"] == ""
        assert result["primary_contact"] == ""


# ---------------------------------------------------------------------------
# TestFetchDeals
# ---------------------------------------------------------------------------


class TestFetchDeals:
    """fetch_deals() queries the Airtable API with correct filters."""

    @patch("urllib.request.urlopen")
    def test_returns_records(self, mock_urlopen_fn):
        # Arrange
        records = [_make_bb_deal_record()]
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response(records))
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        result = search_deals.fetch_deals("appXXX", "tblXXX", "Acme", config)

        # Assert
        assert len(result) == 1

    @patch("urllib.request.urlopen")
    def test_open_only_filter_bb(self, mock_urlopen_fn):
        # Arrange
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response([]))
        config = search_deals.DEAL_CONFIG["bb"]

        # Act
        search_deals.fetch_deals("appXXX", "tblXXX", "Acme", config, open_only=True)

        # Assert — URL should contain closed status exclusions
        url = mock_urlopen_fn.call_args[0][0].full_url
        assert "Closed" in url or "Closed%20" in url or "Closed+Won" in url

    @patch("urllib.request.urlopen")
    def test_aitb_searches_multiple_fields(self, mock_urlopen_fn):
        # Arrange
        mock_urlopen_fn.return_value = _mock_urlopen(_make_airtable_response([]))
        config = search_deals.DEAL_CONFIG["aitb"]

        # Act
        search_deals.fetch_deals("appXXX", "tblXXX", "Acme", config)

        # Assert — URL should contain OR() for multi-field search
        url = mock_urlopen_fn.call_args[0][0].full_url
        assert "OR" in url


# ---------------------------------------------------------------------------
# TestFilterAndDedup
# ---------------------------------------------------------------------------


class TestFilterAndDedup:
    """filter_and_dedup() applies fuzzy scoring and deduplication."""

    def test_filters_non_matching(self):
        results = [{"name": "Totally Different", "source": "BB"}]
        filtered = search_deals.filter_and_dedup(results, "Acme")
        assert len(filtered) == 0

    def test_keeps_matching(self):
        results = [{"name": "Acme Phase 2", "source": "BB"}]
        filtered = search_deals.filter_and_dedup(results, "Acme")
        assert len(filtered) == 1

    def test_dedup_same_source(self):
        results = [
            {"name": "Acme Deal", "source": "BB"},
            {"name": "Acme Deal", "source": "BB"},
        ]
        filtered = search_deals.filter_and_dedup(results, "Acme Deal")
        assert len(filtered) == 1

    def test_keeps_different_sources(self):
        results = [
            {"name": "Acme Deal", "source": "BB"},
            {"name": "Acme Deal", "source": "AITB"},
        ]
        filtered = search_deals.filter_and_dedup(results, "Acme Deal")
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# TestSearchAllBases
# ---------------------------------------------------------------------------


class TestSearchAllBases:
    """search_all_bases() orchestrates across BB and AITB."""

    @patch("search_deals.fetch_deals")
    def test_combines_both_bases(self, mock_fetch):
        # Arrange
        mock_fetch.side_effect = [
            [_make_bb_deal_record()],
            [_make_aitb_deal_record()],
        ]

        # Act
        results = search_deals.search_all_bases("Deal")

        # Assert
        assert len(results) == 2
        sources = {r["source"] for r in results}
        assert "Brain Bridge Airtable" in sources
        assert "AITB Airtable" in sources

    @patch("search_deals.fetch_deals")
    def test_base_filter_bb(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = [_make_bb_deal_record()]

        # Act
        results = search_deals.search_all_bases("Deal", base_filter="bb")

        # Assert
        assert mock_fetch.call_count == 1
        assert all(r["source"] == "Brain Bridge Airtable" for r in results)

    @patch("search_deals.fetch_deals")
    def test_base_filter_aitb(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = [_make_aitb_deal_record()]

        # Act
        results = search_deals.search_all_bases("Deal", base_filter="aitb")

        # Assert
        assert mock_fetch.call_count == 1
        assert all(r["source"] == "AITB Airtable" for r in results)

    @patch("search_deals.fetch_deals")
    def test_graceful_degradation(self, mock_fetch):
        # Arrange — BB fails, AITB succeeds
        mock_fetch.side_effect = [
            Exception("API error"),
            [_make_aitb_deal_record()],
        ]

        # Act
        results = search_deals.search_all_bases("Deal")

        # Assert
        assert len(results) == 1
        assert results[0]["source"] == "AITB Airtable"

    @patch("search_deals.fetch_deals")
    def test_open_only_passed_through(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = []

        # Act
        search_deals.search_all_bases("Deal", open_only=True)

        # Assert — all calls should have open_only=True
        for call in mock_fetch.call_args_list:
            assert (
                call.kwargs.get("open_only") is True or call[1].get("open_only") is True
            )


# ---------------------------------------------------------------------------
# TestFormatJson
# ---------------------------------------------------------------------------


class TestFormatJson:
    """format_json() produces valid JSON structure."""

    def test_structure(self):
        results = [{"name": "Acme Deal", "source": "BB"}]
        data = json.loads(search_deals.format_json("Acme", results))
        assert data["query"] == "Acme"
        assert data["total_sources"] == 1
        assert len(data["results"]) == 1

    def test_empty(self):
        data = json.loads(search_deals.format_json("Acme", []))
        assert data["results"] == []
        assert data["total_sources"] == 0


# ---------------------------------------------------------------------------
# TestFormatHuman
# ---------------------------------------------------------------------------


class TestFormatHuman:
    """format_human() produces readable text output."""

    def test_shows_deal_header(self):
        results = [
            {
                "name": "Acme Phase 2",
                "source": "BB",
                "status": "",
                "type": "",
                "organization": "",
                "primary_contact": "",
                "amount": None,
                "description": "",
                "link": "",
            }
        ]
        output = search_deals.format_human("Acme", results)
        assert "DEAL: Acme Phase 2" in output

    def test_shows_status_and_type(self):
        results = [
            {
                "name": "Acme Phase 2",
                "source": "BB",
                "status": "Qualification",
                "type": "New Customer",
                "organization": "",
                "primary_contact": "",
                "amount": None,
                "description": "",
                "link": "",
            }
        ]
        output = search_deals.format_human("Acme", results)
        assert "Qualification" in output
        assert "New Customer" in output

    def test_shows_amount(self):
        results = [
            {
                "name": "Acme Deal",
                "source": "BB",
                "status": "",
                "type": "",
                "organization": "",
                "primary_contact": "",
                "amount": 45000,
                "description": "",
                "link": "",
            }
        ]
        output = search_deals.format_human("Acme", results)
        assert "$45000" in output

    def test_no_results_message(self):
        output = search_deals.format_human("ZZZ", [])
        assert "No deals found" in output

    def test_no_results_with_base_filter(self):
        output = search_deals.format_human("ZZZ", [], base_filter="bb")
        assert "No deals found" in output
        assert "Brain Bridge Airtable" in output
        # AITB should NOT appear when filtering to bb only
        assert "AITB" not in output

    def test_missing_sources_shown(self):
        results = [
            {
                "name": "Acme",
                "source": "Brain Bridge Airtable",
                "status": "",
                "type": "",
                "organization": "",
                "primary_contact": "",
                "amount": None,
                "description": "",
                "link": "",
            }
        ]
        output = search_deals.format_human("Acme", results)
        assert "Not found in:" in output
        assert "AITB Airtable" in output
