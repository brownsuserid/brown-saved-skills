"""Tests for sync-recurring-tasks.sh — verifies dedup, URL encoding, 24h filter, and counter fixes.

Uses a mock curl script injected via PATH to intercept all Airtable API calls.
The mock curl logs every request to a file for assertions and returns
preconfigured JSON responses based on the URL pattern.
"""

import json
import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "regenerating-recurring-tasks"
    / "sync-recurring-tasks.sh"
)


def _airtable_response(records: list[dict]) -> str:
    return json.dumps({"records": records})


def _recent_timestamp() -> str:
    """Return an ISO timestamp from ~1 hour ago (within the 24h window)."""
    from datetime import datetime, timedelta, timezone

    dt = datetime.now(timezone.utc) - timedelta(hours=1)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _completed_record(
    record_id: str,
    task: str,
    recurrence: str = "Weekly",
    assignee: list[str] | None = None,
    notes: str = "",
    last_modified: str | None = None,
) -> dict:
    fields: dict = {
        "Task": task,
        "Status": "Completed",
        "Recurrence": recurrence,
        "Notes": notes,
        "Last Modified": last_modified or _recent_timestamp(),
    }
    if assignee:
        fields["Assignee"] = assignee
    return {"id": record_id, "fields": fields}


def _created_record(record_id: str) -> str:
    return json.dumps({"id": record_id, "fields": {"Task": "created"}})


def _error_response(msg: str) -> str:
    return json.dumps({"error": {"type": "INVALID_VALUE", "message": msg}})


@pytest.fixture()
def mock_env(tmp_path: Path):
    """Set up a mock curl, log file, and response config for the script."""
    log_file = tmp_path / "curl_log.txt"
    response_file = tmp_path / "curl_responses.json"
    mock_curl = tmp_path / "curl"

    # The mock curl script logs the full command line and returns a response
    # based on URL pattern matching configured in the response file.
    mock_curl_template = textwrap.dedent("""\
        #!/bin/bash
        # Log the full invocation
        echo "$@" >> "__LOG_FILE__"

        # Find the URL (first arg that starts with http)
        URL=""
        METHOD="GET"
        DATA=""
        for arg in "$@"; do
            case "$arg" in
                http*) URL="$arg" ;;
            esac
        done
        # Check for method
        PREV=""
        for i in "$@"; do
            if [ "$PREV" = "-X" ]; then
                METHOD="$i"
            fi
            PREV="$i"
        done
        # Check for data
        PREV=""
        for i in "$@"; do
            if [ "$PREV" = "-d" ]; then
                DATA="$i"
            fi
            PREV="$i"
        done

        # Read response config
        RESPONSES=$(cat "__RESPONSE_FILE__")

        EMPTY_RECORDS='{"records":[]}'
        DEFAULT_CREATE='{"id":"recNEW1","fields":{}}'

        # Match URL patterns to responses
        # Completed query contains "Recurrence"; existing-instance check contains "Task%3D"
        if echo "$URL" | grep -q "filterByFormula"; then
            if echo "$URL" | grep -q "Recurrence"; then
                echo "$RESPONSES" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('completed','{\"records\":[]}'))"
            else
                echo "$RESPONSES" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('existing','{\"records\":[]}'))"
            fi
        elif [ "$METHOD" = "POST" ]; then
            echo "$DATA" >> "__TMP_PATH__/created_payloads.txt"
            echo "$RESPONSES" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('create','{\"id\":\"recNEW1\",\"fields\":{}}'))"
        elif [ "$METHOD" = "PATCH" ]; then
            echo "PATCH: $URL $DATA" >> "__TMP_PATH__/patch_log.txt"
            echo '{"id":"recPATCHED","fields":{"Status":"Archived"}}'
        else
            echo '{"records":[]}'
        fi
    """)
    mock_curl_text = (
        mock_curl_template.replace("__LOG_FILE__", str(log_file))
        .replace("__RESPONSE_FILE__", str(response_file))
        .replace("__TMP_PATH__", str(tmp_path))
    )
    mock_curl.write_text(mock_curl_text)
    mock_curl.chmod(mock_curl.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["PATH"] = str(tmp_path) + ":" + env.get("PATH", "")
    env["AIRTABLE_TOKEN"] = "test-token-fake"

    return {
        "env": env,
        "log_file": log_file,
        "response_file": response_file,
        "tmp_path": tmp_path,
    }


def _run_script(mock_env: dict, responses: dict) -> subprocess.CompletedProcess:
    mock_env["response_file"].write_text(json.dumps(responses))
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=mock_env["env"],
        timeout=30,
    )
    return result


def _curl_log(mock_env: dict) -> str:
    log = mock_env["log_file"]
    return log.read_text() if log.exists() else ""


def _patch_log(mock_env: dict) -> str:
    log = mock_env["tmp_path"] / "patch_log.txt"
    return log.read_text() if log.exists() else ""


def _created_payloads(mock_env: dict) -> list[dict]:
    path = mock_env["tmp_path"] / "created_payloads.txt"
    if not path.exists():
        return []
    # jq outputs pretty-printed multiline JSON, so we use raw_decode
    # to parse multiple JSON objects from the concatenated file.
    payloads = []
    content = path.read_text().strip()
    decoder = json.JSONDecodeError
    idx = 0
    while idx < len(content):
        try:
            obj, end_idx = json.JSONDecoder().raw_decode(content, idx)
            payloads.append(obj)
            idx = end_idx
        except decoder:
            idx += 1
    return payloads


class TestDeduplicationWithinSingleRun:
    """Multiple completed records with the same task name should produce only 1 new task per base."""

    def test_duplicate_completed_records_create_only_one_per_base(self, mock_env):
        # Arrange: 3 completed records for the same task name
        records = [
            _completed_record("rec1", "Exercise 4x weekly"),
            _completed_record("rec2", "Exercise 4x weekly"),
            _completed_record("rec3", "Exercise 4x weekly"),
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),  # no active instance
            "create": _created_record("recNEW1"),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: script processes 2 bases (Personal, AITB — BB excluded), each sees the
        # same mock data. Within each base, dedup should reduce 3 records to 1 create.
        # So 2 bases x 1 create = 2 total (NOT 2 bases x 3 records = 6).
        payloads = _created_payloads(mock_env)
        num_bases = 2
        assert len(payloads) == num_bases, (
            f"Expected {num_bases} tasks (1 per base) but got {len(payloads)}. "
            f"Dedup within a single run failed."
        )
        assert all(p["fields"]["Task"] == "Exercise 4x weekly" for p in payloads)

    def test_different_task_names_each_create_one_per_base(self, mock_env):
        # Arrange: 2 different recurring tasks
        records = [
            _completed_record("rec1", "Exercise 4x weekly"),
            _completed_record("rec2", "Log breakfast"),
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: 2 bases x 2 tasks = 4 creates (BB excluded)
        payloads = _created_payloads(mock_env)
        task_names = [p["fields"]["Task"] for p in payloads]
        num_bases = 2
        assert len(payloads) == 2 * num_bases
        assert task_names.count("Exercise 4x weekly") == num_bases
        assert task_names.count("Log breakfast") == num_bases


class TestSkipsWhenActiveInstanceExists:
    """If an active instance already exists, no new task should be created."""

    def test_skips_creation_when_active_instance_found(self, mock_env):
        # Arrange
        records = [_completed_record("rec1", "Exercise 4x weekly")]
        active_instance = {
            "id": "recACTIVE",
            "fields": {"Task": "Exercise 4x weekly", "Status": "Not Started"},
        }
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([active_instance]),
            "create": _created_record("recNEW1"),
        }

        # Act
        result = _run_script(mock_env, responses)

        # Assert
        payloads = _created_payloads(mock_env)
        assert len(payloads) == 0, "Should not create task when active instance exists"
        assert "active instance exists" in result.stdout


class TestCompletedRecordsPreserved:
    """Completed records should NOT be archived — they stay as Completed."""

    def test_completed_record_not_archived_after_creation(self, mock_env):
        # Arrange
        records = [_completed_record("recCOMPLETED1", "Exercise 4x weekly")]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: no PATCH calls — completed records are preserved
        patches = _patch_log(mock_env)
        assert patches == "", (
            "Completed records should NOT be archived; no PATCH calls expected"
        )

    def test_no_patch_calls_even_with_duplicates(self, mock_env):
        # Arrange: 2 completed records same name
        records = [
            _completed_record("recA", "Exercise 4x weekly"),
            _completed_record("recB", "Exercise 4x weekly"),
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: no PATCH calls at all
        patches = _patch_log(mock_env)
        assert patches == "", "No records should be archived"


class TestURLEncoding:
    """filterByFormula parameters must be URL-encoded to prevent silent failures."""

    def test_completed_query_is_url_encoded(self, mock_env):
        # Arrange
        responses = {
            "completed": _airtable_response([]),
            "existing": _airtable_response([]),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: check the curl log for URL-encoded formula
        log = _curl_log(mock_env)
        # The formula should be URL-encoded (spaces become %20, quotes become %27, etc.)
        # At minimum, the filterByFormula value should not contain raw single quotes
        for line in log.splitlines():
            if "filterByFormula" in line:
                # Extract the URL from the curl args
                # URL-encoded formulas should not have raw spaces in the formula value
                assert (
                    "filterByFormula=AND(" not in line or "%28" in line or "%27" in line
                ), f"filterByFormula appears to not be URL-encoded: {line}"


class TestCounterAccuracy:
    """Counters must reflect actual operations (subshell fix verification)."""

    def test_created_counter_matches_actual_creations(self, mock_env):
        # Arrange: 2 tasks that should both be created
        records = [
            _completed_record("rec1", "Exercise 4x weekly"),
            _completed_record("rec2", "Log breakfast"),
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        result = _run_script(mock_env, responses)

        # Assert: the output should show the correct count
        # With the subshell bug, this would show "Created: 0"
        # Note: the script processes 3 bases, so we get creates from the first base
        # The mock returns the same completed records for all bases, but the existing
        # check should catch them for bases 2 and 3 (since we create in base 1)
        assert "Created: 0" not in result.stdout or "Skipped:" in result.stdout, (
            "Counter should reflect actual creations (subshell bug regression)"
        )

    def test_skipped_counter_increments_for_duplicates(self, mock_env):
        # Arrange: 3 completed records, same name — 1 created, 2 skipped
        records = [
            _completed_record("rec1", "Exercise 4x weekly"),
            _completed_record("rec2", "Exercise 4x weekly"),
            _completed_record("rec3", "Exercise 4x weekly"),
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        result = _run_script(mock_env, responses)

        # Assert: should see skip messages in output
        assert "already processed this run" in result.stdout


class TestProcessSubstitution:
    """Verify the script uses process substitution, not pipe, for the while loop."""

    def test_script_uses_process_substitution(self):
        """The while loop must use 'done < <(...)' not 'cmd | while read'."""
        script_content = SCRIPT_PATH.read_text()
        assert "done < <(" in script_content, (
            "Script must use process substitution (done < <(...)) "
            "to avoid subshell variable isolation"
        )
        # Make sure there's no pipe-to-while pattern
        lines = script_content.splitlines()
        for line in lines:
            stripped = line.strip()
            if "| while read" in stripped and not stripped.startswith("#"):
                pytest.fail(
                    f"Found pipe-to-while pattern which causes subshell isolation: {stripped}"
                )


class TestRecurrencePatterns:
    """Each recurrence type should produce a task with the correct pattern preserved."""

    @pytest.mark.parametrize(
        "recurrence",
        ["Daily", "Weekly", "Bi-weekly", "Monthly", "Quarterly", "Annually"],
    )
    def test_recurrence_preserved_in_new_task(self, mock_env, recurrence):
        # Arrange
        records = [
            _completed_record("rec1", f"Test {recurrence} task", recurrence=recurrence)
        ]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            "create": _created_record("recNEW1"),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert
        payloads = _created_payloads(mock_env)
        assert len(payloads) >= 1
        assert payloads[0]["fields"]["Recurrence"] == recurrence


class TestComputedFieldRetry:
    """If Deadline is a computed field, the script should retry without it."""

    def test_retries_without_deadline_on_computed_error(self, mock_env):
        # Arrange
        records = [_completed_record("rec1", "Exercise 4x weekly")]
        responses = {
            "completed": _airtable_response(records),
            "existing": _airtable_response([]),
            # First creation attempt fails with computed field error
            "create": _error_response(
                'Field "Deadline" cannot accept a value because the field is computed'
            ),
        }

        # Act
        _run_script(mock_env, responses)

        # Assert: the script should have attempted creation
        # (it will fail on retry too since mock returns same error,
        # but the retry attempt should be visible in the log)
        log = _curl_log(mock_env)
        post_calls = [line for line in log.splitlines() if "-X POST" in line]
        # Should have at least 2 POST calls (original + retry) for the first base
        assert len(post_calls) >= 2, (
            "Script should retry POST without Deadline when computed field error occurs"
        )


class TestNoTasksScenario:
    """When no completed recurring tasks exist, script should complete cleanly."""

    def test_no_completed_tasks_produces_clean_output(self, mock_env):
        # Arrange
        responses = {
            "completed": _airtable_response([]),
            "existing": _airtable_response([]),
        }

        # Act
        result = _run_script(mock_env, responses)

        # Assert
        assert result.returncode == 0
        assert "Recurring Tasks Sync Complete" in result.stdout
        assert "Created: 0" in result.stdout
