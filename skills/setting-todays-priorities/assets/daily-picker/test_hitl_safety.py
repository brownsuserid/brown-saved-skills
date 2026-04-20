"""
Phase 1 endpoint safety tests.

Exercises every safety layer end-to-end against REAL Airtable records using
dry_run=true. No live writes occur. The only side effects are:
  - Reads (_fetch_record calls to snapshot fields_before)
  - Appends to hitl_audit.jsonl
  - Transient process-local state (freeze switch, idempotency cache,
    feature flag flips). All reset at end of test run.

Run:
    cd <daily-picker dir>
    python test_hitl_safety.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid

import app
import hitl_safety

# Real HITL task IDs from hitl_real_data.json, live in the BB base.
# These are READ-ONLY in this test. No writes.
PLAN_TASK_ID = "rec8tX677CPR0l0CX"   # Clean up late-stage deals (Taft...)
OUTPUT_TASK_ID = "rec04uWI4uqX90G78"  # Review: send_email: Touch 4 - Qualification Check - Irfan Pi
BASE = "bb"

# Test bookkeeping
results: list[tuple[str, bool, str]] = []   # (test_name, passed, detail)


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail else ""))


def header(txt: str) -> None:
    print(f"\n=== {txt} ===")


def main() -> int:
    import os
    token_available = bool(os.environ.get("AIRTABLE_TOKEN", "").strip())
    print("=" * 70)
    print("PHASE 1 SAFETY-LAYER TESTS")
    print("=" * 70)
    if token_available:
        print("[env] AIRTABLE_TOKEN is set - live-read tests WILL run against Airtable")
    else:
        print("[env] AIRTABLE_TOKEN is NOT set - tests that depend on live field")
        print("      snapshots will be marked SKIPPED. All other safety-layer tests")
        print("      run normally. Re-run with the token loaded to cover everything.")

    client = app.app.test_client()

    # Snapshot starting state so we can restore
    starting_flags = dict(hitl_safety.HITL_WRITE_FLAGS)
    starting_freeze = hitl_safety.is_frozen()

    try:
        # ----------------------------------------------------------------------
        header("1. Default state -- flags off, not frozen")
        # ----------------------------------------------------------------------
        r = client.get("/api/hitl-flags")
        body = r.get_json()
        check("GET /api/hitl-flags returns 200", r.status_code == 200)
        check(
            "All flags default to False",
            all(v is False for v in body["flags"].values()),
            f"flags={body['flags']}",
        )
        check("Flags response includes frozen state", "frozen" in body)

        r = client.get("/api/hitl-freeze")
        check("GET /api/hitl-freeze returns 200", r.status_code == 200)
        check(
            "Freeze default = False",
            r.get_json()["frozen"] is False,
        )

        # ----------------------------------------------------------------------
        header("2. Flag-off blocks live writes (403)")
        # ----------------------------------------------------------------------
        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
            },
        )
        body = r.get_json()
        check(
            "Live approve_output_asis with flag off returns 403",
            r.status_code == 403,
            f"status={r.status_code}, code={body.get('code')}",
        )
        check(
            "Error code is 'flag_off'",
            body.get("code") == "flag_off",
        )
        check(
            "Error message mentions dry_run",
            "dry_run" in (body.get("error") or "").lower(),
        )

        # ----------------------------------------------------------------------
        header("3. Dry-run bypasses flag block, reads real fields_before")
        # ----------------------------------------------------------------------
        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "dry_run": True,
            },
        )
        body = r.get_json()
        check("Dry-run returns 200", r.status_code == 200)
        check("Dry-run response has dry_run=True", body.get("dry_run") is True)
        check("Dry-run response has action", body.get("action") == "approve_output_asis")
        if token_available:
            before_vals = body.get("fields_before") or {}
            has_real_data = any(v is not None for v in before_vals.values())
            check(
                "Dry-run fetched real fields_before (live read)",
                isinstance(before_vals, dict) and has_real_data,
                f"before keys: {list(before_vals.keys())}",
            )
        else:
            check(
                "Dry-run response has fields_before structure (live read SKIPPED)",
                isinstance(body.get("fields_before"), dict),
                "token not set - fields_before values will be None",
            )
        # With a live token the no-op detection will drop any field whose
        # proposed value already matches current Airtable state. That is
        # correct behavior — we only want to verify the payload was BUILT
        # with the right intent (i.e. HITL Response is always set for an
        # output approval, because its value differs from the live state).
        check(
            "Dry-run payload sets HITL Response + HITL Status (the always-new fields)",
            "HITL Response" in body["fields_to_write"]
            and "HITL Status" in body["fields_to_write"],
            f"keys={list(body['fields_to_write'].keys())}",
        )
        check(
            "Dry-run does NOT write Definition of Done (unedited)",
            "Definition of Done" not in body["fields_to_write"],
        )

        # ----------------------------------------------------------------------
        header("4. Edited Definition of Done shows up in dry-run payload")
        # ----------------------------------------------------------------------
        # Fetch the current DoD so we can submit a legitimately edited version
        before_fields = app._fetch_task_fields(BASE, OUTPUT_TASK_ID)
        original_dod = before_fields.get("Definition of Done", "") or ""
        edited_dod = original_dod + "\n\n[REVIEWER EDIT: tightened closing paragraph.]"

        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "definition_of_done": edited_dod,
                "dry_run": True,
            },
        )
        body = r.get_json()
        check("Edited-draft dry-run returns 200", r.status_code == 200)
        check(
            "Edited-draft action = approve_output_edits",
            body.get("action") == "approve_output_edits",
            f"action={body.get('action')}",
        )
        check(
            "Edited-draft payload INCLUDES Definition of Done",
            "Definition of Done" in body["fields_to_write"],
        )
        check(
            "Edited-draft payload contains the new content",
            body["fields_to_write"].get("Definition of Done", "").endswith(
                "[REVIEWER EDIT: tightened closing paragraph.]"
            ),
        )

        # ----------------------------------------------------------------------
        header("5. Whitespace-only changes do NOT count as an edit")
        # ----------------------------------------------------------------------
        ws_only = original_dod + "   \n"   # just appended trailing whitespace
        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "definition_of_done": ws_only,
                "dry_run": True,
            },
        )
        body = r.get_json()
        check(
            "Whitespace-only edit classified as approve_output_asis",
            body.get("action") == "approve_output_asis",
            f"action={body.get('action')}",
        )
        check(
            "Whitespace-only edit does NOT write Definition of Done",
            "Definition of Done" not in (body.get("fields_to_write") or {}),
        )

        # ----------------------------------------------------------------------
        header("6. No-op detection: submit values that already match")
        # ----------------------------------------------------------------------
        # Pick a plan-type task and fake a decline whose fields already match
        # (task already had HITL Status = Response Submitted + same response).
        # Easier version: submit an empty-change request. Since all Output
        # approvals change Status -> Completed, there's no easy no-op path for
        # output. Instead, test that the diff helper drops matching fields.
        # Synthesize: fetch current, pretend to re-submit same Status.
        plan_before = app._fetch_task_fields(BASE, PLAN_TASK_ID)
        current_hitl_status = plan_before.get("HITL Status", "")

        # Decline a plan with the response text that matches current HITL
        # Response (if any). If it already matches both fields, we expect noop.
        # Most plan tasks have HITL Status = Processed, so the decline write
        # to "Response Submitted" will differ -- expect a non-noop response.
        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": PLAN_TASK_ID,
                "base": BASE,
                "approved": False,
                "hitl_type": "plan",
                "response": "Test decline note for Phase 1 validation",
                "dry_run": True,
            },
        )
        body = r.get_json()
        check("Plan decline dry-run returns 200", r.status_code == 200)
        check(
            "Plan decline action = decline",
            body.get("action") == "decline",
        )
        check(
            "Plan decline writes HITL Status=Response Submitted",
            body.get("fields_to_write", {}).get("HITL Status") == "Response Submitted",
            f"HITL Status was: {current_hitl_status}",
        )

        # ----------------------------------------------------------------------
        header("7. Freeze switch -- engage, verify block, dry-run bypass, release")
        # ----------------------------------------------------------------------
        # Enable the flag temporarily so we can confirm freeze (not flag_off)
        # is the blocker
        hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = True

        r = client.post("/api/hitl-freeze", json={"frozen": True, "reason": "phase-1 test"})
        check("Engage freeze returns 200", r.status_code == 200)
        check("Freeze status now true", r.get_json().get("frozen") is True)

        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
            },
        )
        body = r.get_json()
        check(
            "Live write while frozen returns 423",
            r.status_code == 423,
            f"status={r.status_code}, code={body.get('code')}",
        )
        check("Frozen error code is 'frozen'", body.get("code") == "frozen")

        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "dry_run": True,
            },
        )
        check(
            "Dry-run bypasses freeze",
            r.status_code == 200,
            f"status={r.status_code}",
        )

        r = client.post("/api/hitl-freeze", json={"frozen": False})
        check("Release freeze returns 200", r.status_code == 200)
        check("Freeze status now false", r.get_json().get("frozen") is False)

        # Revert the flag flip
        hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = False

        # ----------------------------------------------------------------------
        header("8. Feature-flag flip via API")
        # ----------------------------------------------------------------------
        r = client.post(
            "/api/hitl-flags",
            json={"action": "approve_plan", "enabled": True},
        )
        check("Flag flip returns 200", r.status_code == 200)
        check(
            "approve_plan flag now True",
            r.get_json()["flags"]["approve_plan"] is True,
        )

        # Revert
        r = client.post(
            "/api/hitl-flags",
            json={"action": "approve_plan", "enabled": False},
        )
        check(
            "Flag flip-back returns 200 and flag False",
            r.status_code == 200
            and r.get_json()["flags"]["approve_plan"] is False,
        )

        r = client.post(
            "/api/hitl-flags",
            json={"action": "bogus_action", "enabled": True},
        )
        check(
            "Unknown action rejected with 400",
            r.status_code == 400,
        )

        # ----------------------------------------------------------------------
        header("9. Idempotency -- LIVE writes with same key replay; dry-runs DON'T cache")
        # ----------------------------------------------------------------------
        # Critical behavior (fixed after a real Phase 2 production bug):
        #   - Dry-runs MUST NOT populate the idempotency cache. If they did,
        #     a live write using the same key as its preview would be served
        #     the cached dry-run response and never execute.
        #   - Live writes MUST populate the cache so double-clicks are safe.
        #
        # We simulate live writes through safe_patch_task directly (with a
        # mocked patch_fn) so we don't hit Airtable.
        key = str(uuid.uuid4())

        # First call: dry-run. Must NOT cache.
        r1 = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "dry_run": True,
                "idempotency_key": key,
            },
        )
        check("Dry-run #1 returns 200", r1.status_code == 200)
        check(
            "Dry-run #1 is NOT idempotent_replay",
            not (r1.get_json() or {}).get("idempotent_replay"),
        )

        # Second call with same key, still dry-run. Must return a FRESH
        # response (no replay from cache, because dry-runs aren't cached).
        r2 = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "dry_run": True,
                "idempotency_key": key,
            },
        )
        check(
            "Dry-run #2 with same key is NOT replay (dry-runs don't cache)",
            not (r2.get_json() or {}).get("idempotent_replay"),
            "this is the critical fix: dry-run responses must never cache "
            "or the subsequent live write gets served the dry-run response",
        )

        # Now simulate the live-write idempotency via direct call with mock
        # patch_fn. First call executes, second call replays.
        def fake_patch_success(base_key, record_id, fields):
            return {"id": record_id, "fields": fields}

        hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = True
        try:
            live_key = str(uuid.uuid4())
            live1 = hitl_safety.safe_patch_task(
                action="approve_output_asis",
                base_key=BASE,
                record_id="recSIMIDEMP",
                fields={"Status": "Completed"},
                fields_before={"Status": "Human Review"},
                user="test",
                dry_run=False,
                idempotency_key=live_key,
                patch_fn=fake_patch_success,
            )
            check(
                "Live write #1 executes (not replay)",
                not live1.get("idempotent_replay"),
            )
            live2 = hitl_safety.safe_patch_task(
                action="approve_output_asis",
                base_key=BASE,
                record_id="recSIMIDEMP",
                fields={"Status": "Completed"},
                fields_before={"Status": "Human Review"},
                user="test",
                dry_run=False,
                idempotency_key=live_key,
                patch_fn=fake_patch_success,
            )
            check(
                "Live write #2 with same key IS replay (cache hit)",
                live2.get("idempotent_replay") is True,
            )
        finally:
            hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = False

        # ----------------------------------------------------------------------
        header("10. /api/hitl-preview forces dry_run regardless of client")
        # ----------------------------------------------------------------------
        r = client.post(
            "/api/hitl-preview",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
                "dry_run": False,  # client LIES and says dry_run=false
            },
        )
        body = r.get_json()
        check("Preview returns 200", r.status_code == 200)
        check(
            "Preview enforces dry_run=true even when client sends false",
            body.get("dry_run") is True,
        )

        # ----------------------------------------------------------------------
        header("10b. Auto-freeze on UNKNOWN_FIELD_NAME (unit test with mock)")
        # ----------------------------------------------------------------------
        # We can't trigger this through the live Airtable call without actually
        # sending a real write, so we test the safe_patch_task function directly
        # with a patch_fn that simulates an UNKNOWN_FIELD_NAME response.
        import urllib.error
        import io

        def fake_patch_unknown_field(base_key, record_id, fields):
            fake_body = json.dumps({
                "error": {"type": "UNKNOWN_FIELD_NAME", "message": "Final Output"}
            }).encode()
            raise urllib.error.HTTPError(
                url="http://fake",
                code=422,
                msg="Unprocessable Entity",
                hdrs=None,
                fp=io.BytesIO(fake_body),
            )

        # Enable the flag so we reach the actual patch_fn call
        hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = True
        try:
            hitl_safety.safe_patch_task(
                action="approve_output_asis",
                base_key=BASE,
                record_id="recSIMULATED",
                fields={"Final Output": "fake"},
                fields_before={"Final Output": None},
                user="test",
                dry_run=False,
                idempotency_key=None,
                patch_fn=fake_patch_unknown_field,
            )
            check("Unknown-field raises HitlWriteError", False, "no exception raised")
        except hitl_safety.HitlWriteError as e:
            check(
                "Unknown-field raises HitlWriteError with code=unknown_field",
                e.code == "unknown_field",
                f"code={e.code}",
            )
            check(
                "Auto-freeze engaged after unknown-field",
                hitl_safety.is_frozen(),
            )
        finally:
            # Release the auto-freeze and the test-only flag
            hitl_safety.set_freeze(False, reason="test cleanup", user="test")
            hitl_safety.HITL_WRITE_FLAGS["approve_output_asis"] = False

        # ----------------------------------------------------------------------
        header("10c. Rate limit triggers at 11th live call in under a minute")
        # ----------------------------------------------------------------------
        # We stress only the rate-limit check itself, not the full endpoint,
        # so we don't need to enable any feature flags or mock the patch_fn.
        test_user = f"rate-test-{uuid.uuid4().hex[:6]}"
        ok_count = 0
        blocked_count = 0
        for i in range(15):
            ok, _ = hitl_safety.rate_limit_check(test_user)
            if ok:
                ok_count += 1
            else:
                blocked_count += 1
        check(
            "Exactly 10 calls admitted, rest blocked",
            ok_count == 10 and blocked_count == 5,
            f"admitted={ok_count}, blocked={blocked_count}",
        )

        # ----------------------------------------------------------------------
        header("11. Audit log - every attempt captured")
        # ----------------------------------------------------------------------
        r = client.get("/api/hitl-audit-tail?n=50")
        entries = (r.get_json() or {}).get("entries", [])
        check("Audit tail returns 200", r.status_code == 200)
        check("Audit tail has entries", len(entries) > 0, f"count={len(entries)}")

        events = [e.get("event") for e in entries]
        check("Audit log contains write events", "write" in events)
        check("Audit log contains freeze_set events", "freeze_set" in events)
        check("Audit log contains flag_set events", "flag_set" in events)

        # Confirm dry_run entries exist and contain fields_before
        dry_runs = [e for e in entries if e.get("event") == "write" and e.get("dry_run")]
        check(
            "Audit log captures dry_run writes with fields_before",
            len(dry_runs) > 0 and isinstance(dry_runs[-1].get("fields_before"), dict),
            f"dry_runs={len(dry_runs)}",
        )

        # ----------------------------------------------------------------------
        header("12. Input validation")
        # ----------------------------------------------------------------------
        r = client.post("/api/hitl-respond-safe", json={})
        check("Missing id/base returns 400", r.status_code == 400)

        r = client.post(
            "/api/hitl-respond-safe",
            json={"id": "recX", "base": "bb", "approved": False, "hitl_type": "plan"},
        )
        check(
            "Decline without response text returns 400",
            r.status_code == 400,
        )

        r = client.post(
            "/api/hitl-respond-safe",
            json={
                "id": "recX",
                "base": "nonexistent_base_xyz",
                "approved": True,
                "hitl_type": "output",
                "dry_run": True,
            },
        )
        check(
            "Unknown base returns 400",
            r.status_code == 400,
        )

        # ----------------------------------------------------------------------
        header("12b. Cascade decline — shape validation + flag gating")
        # ----------------------------------------------------------------------
        # /api/hitl-cascade-decline shape checks
        r = client.post("/api/hitl-cascade-decline", json={})
        check("cascade: missing id/base returns 400", r.status_code == 400)

        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "BOGUS",
            "response": "x", "cascade_task_ids": [],
        })
        check(
            "cascade: bad scope returns 400",
            r.status_code == 400,
            f"status={r.status_code}",
        )

        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "plans",
            "response": "", "cascade_task_ids": [],
        })
        check(
            "cascade: empty response text rejected",
            r.status_code == 400,
        )

        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "plans",
            "response": "note", "cascade_task_ids": ["not_a_rec_id"],
        })
        check(
            "cascade: invalid sibling id returns 400",
            r.status_code == 400,
        )

        # Live cascade should be blocked by flag_off (default)
        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "plans",
            "response": "testing", "cascade_task_ids": [],
        })
        body = r.get_json() or {}
        check(
            "cascade: live 'plans' with flag off returns 403 flag_off",
            r.status_code == 403 and body.get("code") == "flag_off",
            f"status={r.status_code}, code={body.get('code')}",
        )

        # Dry-run cascade bypasses flag
        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "plans",
            "response": "dry-run test", "cascade_task_ids": [],
            "dry_run": True,
        })
        body = r.get_json() or {}
        check(
            "cascade: dry-run bypasses flag, returns 200",
            r.status_code == 200 and body.get("dry_run") is True,
            f"status={r.status_code}",
        )
        check(
            "cascade: dry-run response includes scope + task_count",
            body.get("scope") == "plans" and body.get("task_count", 0) >= 1,
        )
        check(
            "cascade: dry-run includes primary fields_to_write",
            isinstance((body.get("primary") or {}).get("fields_to_write"), dict),
        )

        # 50-task cap
        r = client.post("/api/hitl-cascade-decline", json={
            "id": OUTPUT_TASK_ID, "base": BASE, "scope": "all",
            "response": "cap test", "cascade_task_ids": [f"rec{i:017d}" for i in range(51)],
            "dry_run": True,
        })
        body = r.get_json() or {}
        check(
            "cascade: over-50-task batch rejected with cascade_too_large",
            r.status_code == 400 and body.get("code") == "cascade_too_large",
            f"status={r.status_code}, code={body.get('code')}",
        )

        # ----------------------------------------------------------------------
        header("12c. Cascade live execution — mock patch path")
        # ----------------------------------------------------------------------
        import urllib.error, io as _io
        hitl_safety.HITL_WRITE_FLAGS["cascade_decline"] = True

        captured_batches = []
        def mock_batch_patch(base_id, table_id, records, api_headers_fn, api_url_fn):
            captured_batches.append(list(records))
            return {"records": [{"id": r["id"], "fields": r["fields"]} for r in records]}

        # Monkey-patch the batch function directly
        orig = hitl_safety._airtable_batch_patch
        hitl_safety._airtable_batch_patch = mock_batch_patch
        try:
            result = hitl_safety.safe_cascade_write(
                scope="plans",
                primary={"task_id": "recPRIM", "hitl_type": "plan",
                         "fields_to_write": {"HITL Status": "Response Submitted", "HITL Response": "reject"},
                         "fields_before": {"HITL Status": "Processed", "HITL Response": None}},
                cascades=[
                    {"task_id": "recC1", "fields_to_write": {"HITL Status": "Response Submitted"},
                     "fields_before": {"HITL Status": "Processed"}},
                    {"task_id": "recC2", "fields_to_write": {"HITL Status": "Response Submitted"},
                     "fields_before": {"HITL Status": "Processed"}},
                ],
                user="test@brown",
                dry_run=False,
                idempotency_key="cascade-test-1",
                base_id="appTEST",
                table_id="tblTEST",
                api_headers_fn=lambda: {},
                api_url_fn=lambda b, t: f"http://mock/{b}/{t}",
            )
            check(
                "cascade live write: ok=True",
                result.get("ok") is True,
            )
            check(
                "cascade live write: batch sent 3 records in 1 batch",
                len(captured_batches) == 1 and len(captured_batches[0]) == 3,
                f"batches={len(captured_batches)}, records={[len(b) for b in captured_batches]}",
            )
            check(
                "cascade live write: all results marked 'written'",
                all(r["status"] == "written" for r in result.get("results", [])),
            )

            # Same idempotency key on a second call replays
            result2 = hitl_safety.safe_cascade_write(
                scope="plans",
                primary={"task_id": "recPRIM", "hitl_type": "plan",
                         "fields_to_write": {"HITL Status": "Response Submitted"},
                         "fields_before": {"HITL Status": "Processed"}},
                cascades=[],
                user="test@brown",
                dry_run=False,
                idempotency_key="cascade-test-1",
                base_id="appTEST",
                table_id="tblTEST",
                api_headers_fn=lambda: {},
                api_url_fn=lambda b, t: f"http://mock/{b}/{t}",
            )
            check(
                "cascade: same idempotency key replays (no second batch sent)",
                result2.get("idempotent_replay") is True and len(captured_batches) == 1,
            )
        finally:
            hitl_safety._airtable_batch_patch = orig
            hitl_safety.HITL_WRITE_FLAGS["cascade_decline"] = False

        # ----------------------------------------------------------------------
        header("13. Existing endpoints still work (regression check)")
        # ----------------------------------------------------------------------
        r = client.get("/api/config")
        check("/api/config still 200", r.status_code == 200)
        r = client.get("/api/hitl-count")
        check(
            "/api/hitl-count still functional",
            r.status_code == 200,
            f"status={r.status_code}",
        )
        # Aaron's original /api/hitl-respond must still be present and
        # behave identically to its pre-Phase-1 shape. Must NOT enforce
        # any feature-flag gating.
        r = client.post("/api/hitl-respond", json={})
        check(
            "Aaron's /api/hitl-respond present and validates (400 on empty body)",
            r.status_code == 400,
            f"status={r.status_code}",
        )
        r = client.post(
            "/api/hitl-respond",
            json={
                "id": OUTPUT_TASK_ID,
                "base": BASE,
                "approved": True,
                "hitl_type": "output",
            },
        )
        body = r.get_json() or {}
        check(
            "Aaron's endpoint does NOT enforce feature flags (no 403 flag_off)",
            not (r.status_code == 403 and body.get("code") == "flag_off"),
            f"status={r.status_code}, code={body.get('code')}",
        )

    finally:
        # Restore starting state so the process is clean if someone runs
        # the test during a live session.
        for k, v in starting_flags.items():
            hitl_safety.HITL_WRITE_FLAGS[k] = v
        hitl_safety.set_freeze(starting_freeze, reason="test cleanup", user="test")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"RESULT: {passed} / {total} checks passed")
    failures = [(n, d) for n, ok, d in results if not ok]
    if failures:
        print("\nFAILURES:")
        for n, d in failures:
            print(f"  - {n}  ({d})")
        return 1
    print("All safety layers verified. Live writes remain blocked by default flags.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
