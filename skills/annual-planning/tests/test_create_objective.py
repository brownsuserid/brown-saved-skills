"""Tests for create_objective.py — verifies correct fields sent per base."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

SHARED_DIR = str(os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))
sys.path.insert(0, SHARED_DIR)
sys.path.insert(
    0,
    str(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "annual-planning"
        )
    ),
)

import airtable_config  # noqa: E402

_test_config = airtable_config.load_config(
    os.path.join(SHARED_DIR, "configs", "all.yaml")
)

from create_objective import (  # noqa: E402
    OBJECTIVE_CONFIG,
    OBJECTIVE_STATUS_VALUES,
    create_objective,
    resolve_category,
    resolve_objective_status,
)


def _mock_response(record_id: str = "recOBJ123", fields: dict | None = None):
    """Build a mock urllib response matching Airtable's POST response."""
    data = {"id": record_id, "fields": fields or {}}
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestResolveObjectiveStatus:
    """Objective status resolution per base."""

    def test_personal_not_started(self):
        assert resolve_objective_status("not_started", "personal") == "Not Started"

    def test_personal_done(self):
        assert resolve_objective_status("done", "personal") == "Done"

    def test_aitb_not_started_maps_to_todo(self):
        assert resolve_objective_status("not_started", "aitb") == "Todo"

    def test_aitb_on_track_maps_to_in_progress(self):
        assert resolve_objective_status("on_track", "aitb") == "In progress"

    def test_bb_done_maps_to_completed(self):
        assert resolve_objective_status("done", "bb") == "Completed"

    def test_bb_off_track_maps_to_at_risk(self):
        assert resolve_objective_status("off_track", "bb") == "At Risk"

    def test_literal_passthrough(self):
        assert resolve_objective_status("Not Started", "personal") == "Not Started"
        assert resolve_objective_status("Todo", "aitb") == "Todo"
        assert resolve_objective_status("Completed", "bb") == "Completed"


class TestResolveCategory:
    """Category resolution for Personal base."""

    def test_semantic_to_literal(self):
        assert resolve_category("mental") == "Mental"
        assert resolve_category("work") == "Work/Intuit"
        assert resolve_category("relationships") == "Key Relationships"

    def test_literal_passthrough(self):
        assert resolve_category("Mental") == "Mental"
        assert resolve_category("Work/Intuit") == "Work/Intuit"


class TestCreateObjectivePersonal:
    """Personal base Objective creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        result = create_objective(
            base_key="personal",
            name="Exercise 4x/week consistently",
            config=_test_config,
            description="Track in Apple Health, 4+ sessions/week for 48+ weeks",
            category="physical",
            year="2027",
            priority=4,
        )

        assert result["id"] == "recOBJ123"
        assert result["base"] == "personal"
        assert "tbll1AUS4uBF9Cgnh" in result["airtable_url"]

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Name"] == "Exercise 4x/week consistently"
        assert (
            fields["Measurements"]
            == "Track in Apple Health, 4+ sessions/week for 48+ weeks"
        )
        assert fields["Status"] == "Not Started"
        assert fields["Area of Focus"] == "Physical"
        assert fields["Year"] == "2027"
        assert fields["Priority"] == 4

    @patch("urllib.request.urlopen")
    def test_uses_name_field(self, mock_urlopen):
        """Personal uses 'Name' not 'Objective'."""
        mock_urlopen.return_value = _mock_response()

        create_objective(base_key="personal", name="Test Goal", config=_test_config)

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Name" in payload["fields"]
        assert "Objective" not in payload["fields"]

    @patch("urllib.request.urlopen")
    def test_uses_measurements_field(self, mock_urlopen):
        """Personal uses 'Measurements' not 'Description'."""
        mock_urlopen.return_value = _mock_response()

        create_objective(
            base_key="personal",
            name="Test",
            config=_test_config,
            description="Some measurements",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Measurements" in payload["fields"]
        assert "Description" not in payload["fields"]


class TestCreateObjectiveAITB:
    """AITB base Objective creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_objective(
            base_key="aitb",
            name="Grow AITB membership to 500",
            config=_test_config,
            description="Reach 500 active members by year end",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Name"] == "Grow AITB membership to 500"
        assert fields["Notes"] == "Reach 500 active members by year end"
        assert fields["Status"] == "Todo"

    @patch("urllib.request.urlopen")
    def test_no_category_or_year_fields(self, mock_urlopen):
        """AITB has no category or year fields."""
        mock_urlopen.return_value = _mock_response()

        create_objective(base_key="aitb", name="Test", config=_test_config)

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Area of Focus" not in payload["fields"]
        assert "Year" not in payload["fields"]
        assert "Years" not in payload["fields"]
        assert "Priority" not in payload["fields"]


class TestCreateObjectiveBB:
    """BB base Objective creation."""

    @patch("urllib.request.urlopen")
    def test_basic_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()

        create_objective(
            base_key="bb",
            name="Reach $500K ARR",
            config=_test_config,
            description="Annual recurring revenue target",
            year="2027",
            organization="BB",
            status="not_started",
            notes="Requires 10 new enterprise clients",
        )

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        fields = payload["fields"]
        assert fields["Objective"] == "Reach $500K ARR"
        assert fields["Description"] == "Annual recurring revenue target"
        assert fields["Status"] == "Not Started"
        assert fields["Years"] == "2027"
        assert fields["Organization"] == "BB"
        assert fields["Notes"] == "Requires 10 new enterprise clients"

    @patch("urllib.request.urlopen")
    def test_uses_objective_field_not_name(self, mock_urlopen):
        """BB uses 'Objective' not 'Name'."""
        mock_urlopen.return_value = _mock_response()

        create_objective(base_key="bb", name="Test", config=_test_config)

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "Objective" in payload["fields"]
        assert "Name" not in payload["fields"]


class TestCreateObjectiveDefaults:
    """Default status values per base."""

    @patch("urllib.request.urlopen")
    def test_personal_default_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()
        create_objective(base_key="personal", name="Test", config=_test_config)
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Not Started"

    @patch("urllib.request.urlopen")
    def test_aitb_default_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()
        create_objective(base_key="aitb", name="Test", config=_test_config)
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Todo"

    @patch("urllib.request.urlopen")
    def test_bb_default_status(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response()
        create_objective(base_key="bb", name="Test", config=_test_config)
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert payload["fields"]["Status"] == "Not Started"


class TestObjectiveConfig:
    """Verify objective config consistency across bases."""

    def test_all_bases_have_config(self):
        for base in ["personal", "aitb", "bb"]:
            assert base in OBJECTIVE_CONFIG

    def test_all_bases_have_required_fields(self):
        required = [
            "table",
            "table_id",
            "name_field",
            "description_field",
            "status_field",
        ]
        for base_key, config in OBJECTIVE_CONFIG.items():
            for field in required:
                assert field in config, f"{base_key} missing {field}"

    def test_personal_has_category_field(self):
        assert OBJECTIVE_CONFIG["personal"]["category_field"] == "Area of Focus"

    def test_aitb_has_no_category_field(self):
        assert OBJECTIVE_CONFIG["aitb"]["category_field"] is None

    def test_bb_has_organization_field(self):
        assert OBJECTIVE_CONFIG["bb"]["organization_field"] == "Organization"

    def test_status_values_cover_all_bases(self):
        for base in ["personal", "aitb", "bb"]:
            assert base in OBJECTIVE_STATUS_VALUES
            assert "not_started" in OBJECTIVE_STATUS_VALUES[base]
            assert "done" in OBJECTIVE_STATUS_VALUES[base]
