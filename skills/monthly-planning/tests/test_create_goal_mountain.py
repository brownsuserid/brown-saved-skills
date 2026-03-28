"""Tests for create_goal_mountain.py — verifies correct fields sent per base."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    str(os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")),
)
sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "monthly-planning"
        )
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(None)

from create_goal_mountain import (  # noqa: E402
    MOUNTAIN_CONFIG,
    create_mountain,
    resolve_mountain_status,
)


def _mock_response(record_id: str = "recMOUNTAIN123", fields: dict | None = None):
    """Build a mock urllib response matching Airtable's POST response."""
    data = {"id": record_id, "fields": fields or {}}
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestResolveStatus:
    """Mountain status resolution."""

    def test_semantic_to_literal(self):
        assert resolve_mountain_status("on_track") == "On track"
        assert resolve_mountain_status("at_risk") == "At risk"
        assert resolve_mountain_status("archived") == "Archived"

    def test_literal_passthrough(self):
        assert resolve_mountain_status("On track") == "On track"
        assert resolve_mountain_status("Complete") == "Complete"


class TestCreateMountainPersonal:
    """Personal base Mountain creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = create_mountain(
            base_key="personal",
            title="Build daily meditation habit",
            config=_test_config,
            description="Done when meditation tracked 20+ days this month",
            objective_id="recGOAL123",
        )

        assert result["id"] == "recMOUNTAIN123"
        assert result["base"] == "personal"

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Title"] == "Build daily meditation habit"
        assert (
            fields["Definition of Done"]
            == "Done when meditation tracked 20+ days this month"
        )
        assert fields["1yr Goal"] == ["recGOAL123"]
        assert fields["Status"] == "On track"

    @patch("urllib.request.urlopen")
    def test_objective_field_is_1yr_goal(self, mock_urlopen):
        """Personal uses '1yr Goal' not 'Objective'."""
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="personal",
            title="Test",
            config=_test_config,
            description="Test",
            objective_id="recXYZ",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "1yr Goal" in payload["fields"]
        assert "Objective" not in payload["fields"]


class TestCreateMountainAITB:
    """AITB base Mountain creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="aitb",
            title="Launch Q1 Workshop Series",
            config=_test_config,
            description="Done when 3 workshops scheduled and promoted",
            objective_id="recOBJ456",
            priority=8,
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Title"] == "Launch Q1 Workshop Series"
        assert fields["Objective"] == ["recOBJ456"]
        assert fields["Priority"] == 8

    @patch("urllib.request.urlopen")
    def test_objective_field_is_objective(self, mock_urlopen):
        """AITB uses 'Objective' for linked up field."""
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="aitb",
            title="Test",
            config=_test_config,
            description="Test",
            objective_id="recXYZ",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Objective" in payload["fields"]
        assert "1yr Goals" not in payload["fields"]
        assert "Objective (1y)" not in payload["fields"]


class TestCreateMountainBB:
    """BB base Mountain creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="[S][03] Close 5 deals",
            config=_test_config,
            description="Done when 5 new contracts signed",
            objective_id="recBOVlhzvBS31y9q",
            priority=9,
            status="on_track",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Title"] == "[S][03] Close 5 deals"
        assert fields["Definition of Done"] == "Done when 5 new contracts signed"
        assert fields["Objective (1y)"] == ["recBOVlhzvBS31y9q"]
        assert fields["Priority"] == 9
        assert fields["Status"] == "On track"

    @patch("urllib.request.urlopen")
    def test_objective_field_is_objective_1y(self, mock_urlopen):
        """BB uses 'Objective (1y)' for linked up field."""
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="Test",
            config=_test_config,
            description="Test",
            objective_id="recXYZ",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Objective (1y)" in payload["fields"]
        assert "Objective" not in payload["fields"]
        assert "1yr Goals" not in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_notes_field(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="Notes Test",
            config=_test_config,
            description="Test",
            objective_id="recOBJ789",
            notes="Created during monthly planning Feb 2026",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Notes"] == "Created during monthly planning Feb 2026"

    @patch("urllib.request.urlopen")
    def test_custom_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="At Risk Test",
            config=_test_config,
            description="Test",
            objective_id="recOBJ789",
            status="at_risk",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "At risk"


class TestMountainConfig:
    """Verify mountain config consistency across bases."""

    def test_all_bases_have_config(self):
        for base in ["personal", "aitb", "bb"]:
            assert base in MOUNTAIN_CONFIG

    def test_all_bases_have_required_fields(self):
        required = [
            "table",
            "name_field",
            "description_field",
            "status_field",
            "objective_field",
            "priority_field",
        ]
        for base_key, config in MOUNTAIN_CONFIG.items():
            for field in required:
                assert field in config, f"{base_key} missing {field}"

    def test_table_name_consistent(self):
        for config in MOUNTAIN_CONFIG.values():
            assert config["table"] == "Mountains (30d)"

    def test_objective_field_differs_per_base(self):
        assert MOUNTAIN_CONFIG["personal"]["objective_field"] == "1yr Goal"
        assert MOUNTAIN_CONFIG["aitb"]["objective_field"] == "Objective"
        assert MOUNTAIN_CONFIG["bb"]["objective_field"] == "Objective (1y)"


class TestMountainMonthField:
    """Month field is set on every Mountain."""

    @patch("urllib.request.urlopen")
    def test_month_defaults_to_current(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="Test month default",
            description="Test",
            objective_id="recOBJ123",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        month_val = payload["fields"]["Month"]
        # Should be YYYY-MM format
        assert len(month_val) == 7
        assert month_val[4] == "-"

    @patch("urllib.request.urlopen")
    def test_month_explicit(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="bb",
            title="Test explicit month",
            description="Test",
            objective_id="recOBJ123",
            month="2026-04",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Month"] == "2026-04"

    @patch("urllib.request.urlopen")
    def test_month_set_for_personal(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="personal",
            title="Personal mountain",
            description="Test",
            objective_id="recOBJ123",
            month="2026-03",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Month"] == "2026-03"

    @patch("urllib.request.urlopen")
    def test_month_set_for_aitb(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_mountain(
            base_key="aitb",
            title="AITB mountain",
            description="Test",
            objective_id="recOBJ123",
            month="2026-03",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Month"] == "2026-03"
