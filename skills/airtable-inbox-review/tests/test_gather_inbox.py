"""Tests for gather_inbox.py — inbox task gathering, filtering, and classification."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

# Provide a dummy token so airtable_config doesn't fail
os.environ.setdefault("AIRTABLE_TOKEN", "test-token")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "airtable-inbox-review"
    ),
)

# Shared Airtable config
SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared")
sys.path.insert(0, SHARED_DIR)

import airtable_config  # noqa: E402

# Load the config once for test helpers
_test_config = airtable_config.load_config(
    os.path.join(SHARED_DIR, "configs", "all.yaml")
)

from gather_inbox import (  # noqa: E402
    _in_scope,
    build_inbox_filter,
    classify_project_status,
    fetch_inbox_tasks,
)


def _make_airtable_response(records: list[dict], offset: str | None = None) -> bytes:
    data: dict = {"records": records}
    if offset:
        data["offset"] = offset
    return json.dumps(data).encode()


def _make_record(
    record_id: str = "rec123",
    task: str = "Test task",
    description: str = "Ship the feature",
    status: str = "Not Started",
    score: int = 80,
    notes: str = "Some context",
    due_date: str = "2026-03-01",
    assignee_ids: list[str] | None = None,
    project_ids: list[str] | None = None,
    base: str = "personal",
) -> dict:
    """Build a fake Airtable record using the specified base's field names."""
    config = airtable_config.get_base(_test_config, base)
    fields: dict = {
        config["task_field"]: task,
        config["description_field"]: description,
        config["status_field"]: status,
        config["score_field"]: score,
        config["notes_field"]: notes,
        config["due_date_field"]: due_date,
    }
    if assignee_ids is not None:
        fields[config["assignee_field"]] = assignee_ids
    if project_ids is not None:
        fields[config["project_field"]] = project_ids
    return {"id": record_id, "fields": fields}


def _mock_urlopen_with_records(records_by_call: list[list[dict]]):
    """Create mock responses, one per urlopen call."""
    responses = []
    for records in records_by_call:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _make_airtable_response(records)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        responses.append(mock_resp)
    return responses


class TestBuildInboxFilter:
    """build_inbox_filter must produce correct Airtable formulas."""

    def test_personal_filter_uses_find_inbox_in_project(self):
        formula = build_inbox_filter("personal", _test_config)
        assert "FIND('Inbox'" in formula
        assert "ARRAYJOIN({Project})" in formula

    def test_personal_filter_includes_inbox_display_name(self):
        formula = build_inbox_filter("personal", _test_config)
        assert "FIND('Inbox'" in formula

    def test_bb_filter_uses_rock_field(self):
        formula = build_inbox_filter("bb", _test_config)
        assert "ARRAYJOIN({Rock})" in formula
        assert "FIND('Inbox'" in formula

    def test_aitb_filter_uses_project_field(self):
        formula = build_inbox_filter("aitb", _test_config)
        assert "ARRAYJOIN({Project})" in formula

    def test_filter_excludes_all_done_statuses(self):
        base_cfg = airtable_config.get_base(_test_config, "personal")
        formula = build_inbox_filter("personal", _test_config)
        for status in base_cfg["done_statuses"]:
            assert f"{{Status}}!='{status}'" in formula

    def test_filter_is_wrapped_in_and(self):
        formula = build_inbox_filter("personal", _test_config)
        assert formula.startswith("AND(")
        assert formula.endswith(")")

    def test_filter_uses_find_for_inbox_id(self):
        formula = build_inbox_filter("personal", _test_config)
        assert "FIND(" in formula
        assert "ARRAYJOIN(" in formula


class TestFetchInboxTasks:
    """fetch_inbox_tasks must return tasks and respect scope filtering."""

    @patch("urllib.request.urlopen")
    def test_returns_tasks_with_correct_fields(self, mock_urlopen):
        record = _make_record(
            record_id="recABC",
            task="Review PR",
            description="All checks pass",
            status="Not Started",
            score=90,
        )
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1
        t = tasks[0]
        assert t["id"] == "recABC"
        assert t["task"] == "Review PR"
        assert t["description"] == "All checks pass"
        assert t["status"] == "Not Started"
        assert t["score"] == 90
        assert t["base"] == "personal"
        assert "recABC" in t["airtable_url"]

    @patch("urllib.request.urlopen")
    def test_includes_unassigned_tasks(self, mock_urlopen):
        record = _make_record(assignee_ids=[])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1

    @patch("urllib.request.urlopen")
    def test_includes_aaron_tasks(self, mock_urlopen):
        people = airtable_config.get_people(_test_config)
        aaron_id = people["aaron"]["personal"]
        record = _make_record(assignee_ids=[aaron_id])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1

    @patch("urllib.request.urlopen")
    def test_includes_pablo_tasks(self, mock_urlopen):
        people = airtable_config.get_people(_test_config)
        pablo_id = people["pablo"]["personal"]
        record = _make_record(assignee_ids=[pablo_id])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1

    @patch("urllib.request.urlopen")
    def test_excludes_juan_tasks(self, mock_urlopen):
        people = airtable_config.get_people(_test_config)
        juan_id = people["juan"]["personal"]
        record = _make_record(assignee_ids=[juan_id])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 0

    @patch("urllib.request.urlopen")
    def test_handles_pagination(self, mock_urlopen):
        record1 = _make_record(record_id="rec001", task="Task 1")
        record2 = _make_record(record_id="rec002", task="Task 2")

        mock_resp1 = MagicMock()
        mock_resp1.read.return_value = _make_airtable_response(
            [record1], offset="next_page_token"
        )
        mock_resp1.__enter__ = lambda s: s
        mock_resp1.__exit__ = MagicMock(return_value=False)

        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = _make_airtable_response([record2])
        mock_resp2.__enter__ = lambda s: s
        mock_resp2.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [mock_resp1, mock_resp2]

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 2
        assert tasks[0]["id"] == "rec001"
        assert tasks[1]["id"] == "rec002"
        assert mock_urlopen.call_count == 2

    @patch("urllib.request.urlopen")
    def test_handles_api_error_gracefully(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.airtable.com",
            code=422,
            msg="Unprocessable",
            hdrs={},
            fp=MagicMock(read=lambda: b"Bad formula"),
        )

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert tasks == []

    @patch("urllib.request.urlopen")
    def test_includes_project_status_field(self, mock_urlopen):
        record = _make_record(project_ids=[])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1
        assert "project_status" in tasks[0]

    @patch("urllib.request.urlopen")
    def test_excludes_routed_tasks(self, mock_urlopen):
        record = _make_record(project_ids=["recSomeRealProject"])
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 0

    @patch("urllib.request.urlopen")
    def test_empty_string_project_normalized_to_empty_list(self, mock_urlopen):
        record = _make_record()
        record["fields"]["Project"] = ""
        mock_urlopen.side_effect = _mock_urlopen_with_records([[record]])

        tasks = fetch_inbox_tasks("personal", _test_config)

        assert len(tasks) == 1
        assert tasks[0]["project_ids"] == []
        assert tasks[0]["project_status"] == "unrouted"


class TestClassifyProjectStatus:
    """classify_project_status must correctly categorize tasks."""

    def test_unrouted_when_no_project(self):
        task = {"project_ids": []}
        assert classify_project_status(task, "personal", _test_config) == "unrouted"

    def test_inbox_when_only_inbox_project(self):
        base_cfg = airtable_config.get_base(_test_config, "personal")
        inbox_id = base_cfg["inbox_project_id"]
        task = {"project_ids": [inbox_id]}
        assert classify_project_status(task, "personal", _test_config) == "inbox"

    def test_routed_when_has_real_project(self):
        task = {"project_ids": ["recSomeRealProject"]}
        assert classify_project_status(task, "personal", _test_config) == "routed"

    def test_routed_when_has_inbox_plus_real_project(self):
        base_cfg = airtable_config.get_base(_test_config, "personal")
        inbox_id = base_cfg["inbox_project_id"]
        task = {"project_ids": [inbox_id, "recSomeRealProject"]}
        assert classify_project_status(task, "personal", _test_config) == "routed"

    def test_inbox_for_bb_base(self):
        base_cfg = airtable_config.get_base(_test_config, "bb")
        inbox_id = base_cfg["inbox_project_id"]
        task = {"project_ids": [inbox_id]}
        assert classify_project_status(task, "bb", _test_config) == "inbox"

    def test_inbox_for_aitb_base(self):
        base_cfg = airtable_config.get_base(_test_config, "aitb")
        inbox_id = base_cfg["inbox_project_id"]
        task = {"project_ids": [inbox_id]}
        assert classify_project_status(task, "aitb", _test_config) == "inbox"


class TestInScope:
    """_in_scope must correctly filter assignees."""

    def test_unassigned_is_in_scope(self):
        assert _in_scope([], "personal", _test_config) is True

    def test_aaron_is_in_scope(self):
        people = airtable_config.get_people(_test_config)
        assert (
            _in_scope([people["aaron"]["personal"]], "personal", _test_config) is True
        )

    def test_pablo_is_in_scope(self):
        people = airtable_config.get_people(_test_config)
        assert (
            _in_scope([people["pablo"]["personal"]], "personal", _test_config) is True
        )

    def test_juan_is_not_in_scope(self):
        people = airtable_config.get_people(_test_config)
        assert (
            _in_scope([people["juan"]["personal"]], "personal", _test_config) is False
        )

    def test_unknown_id_is_not_in_scope(self):
        assert _in_scope(["recUnknownPerson"], "personal", _test_config) is False

    def test_mixed_assignees_with_aaron_is_in_scope(self):
        people = airtable_config.get_people(_test_config)
        assert (
            _in_scope(
                [people["juan"]["personal"], people["aaron"]["personal"]],
                "personal",
                _test_config,
            )
            is True
        )
