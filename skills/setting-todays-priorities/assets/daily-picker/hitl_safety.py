"""
HITL writeback safety layer.

Sits between api_hitl_respond (and future HITL write endpoints) and the
underlying _patch_task call. Provides:

    - Feature flags per action (default OFF, must be opted in)
    - Process-local freeze switch (one-click "panic stop")
    - Idempotency key dedupe (10-min TTL)
    - Sliding-window rate limit (per user)
    - Dry-run mode (build payload, skip Airtable call)
    - JSON-lines audit log with before/after field snapshots
    - Loud errors on UNKNOWN_FIELD_NAME so silent data loss is impossible

Design notes:
    - Process-local state only. No shared cache, no database. If the Flask
      process restarts, idempotency window and freeze switch reset. That is
      acceptable for a single-user prototype and keeps the failure surface
      small.
    - Thread-safe: each shared structure is guarded by a single lock. Flask's
      dev server runs multi-threaded.
    - Never mutates the existing Aaron-owned _patch_task. Callers wrap it.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
# Each HITL writeback action has a flag. Default OFF. Flip individual flags
# from False to True only after a successful single-record verification.
#
# The prototype UI asks the backend which flags are on and greys out the
# actions whose flags are off.

HITL_WRITE_FLAGS: dict[str, bool] = {
    "approve_output_asis":   False,  # phase 1 — verify first
    "approve_output_edits":  False,  # phase 2
    "approve_plan":          False,  # phase 2
    "decline":               False,  # phase 2
    "cascade_decline":       False,  # phase 3
    "stop_outreach":         False,  # phase 3
    "snooze":                False,  # phase 4
    "escalate":              False,  # phase 4
    "add_note":              False,  # phase 4
}

# ---------------------------------------------------------------------------
# Freeze switch — process-local panic stop
# ---------------------------------------------------------------------------

_freeze_lock = threading.Lock()
_freeze_state: dict[str, Any] = {
    "frozen": False,
    "reason": "",
    "set_at": None,
    "set_by": None,
}


def is_frozen() -> bool:
    with _freeze_lock:
        return _freeze_state["frozen"]


def freeze_status() -> dict[str, Any]:
    with _freeze_lock:
        return dict(_freeze_state)


def set_freeze(frozen: bool, reason: str = "", user: str = "") -> dict[str, Any]:
    with _freeze_lock:
        _freeze_state["frozen"] = bool(frozen)
        _freeze_state["reason"] = reason or ""
        _freeze_state["set_at"] = _iso_now() if frozen else None
        _freeze_state["set_by"] = user or None
        return dict(_freeze_state)


# ---------------------------------------------------------------------------
# Idempotency cache
# ---------------------------------------------------------------------------

_IDEMPOTENCY_TTL_SEC = 10 * 60  # 10 minutes
_idempotency_lock = threading.Lock()
_idempotency: dict[str, tuple[float, dict[str, Any]]] = {}  # key -> (stored_at, response)


def idempotency_check(key: str | None) -> dict[str, Any] | None:
    """Return a cached response if this key was used in the last 10 min, else None."""
    if not key:
        return None
    now = time.time()
    with _idempotency_lock:
        _idempotency_gc_locked(now)
        entry = _idempotency.get(key)
        if entry is None:
            return None
        stored_at, response = entry
        if now - stored_at > _IDEMPOTENCY_TTL_SEC:
            _idempotency.pop(key, None)
            return None
        return response


def idempotency_store(key: str | None, response: dict[str, Any]) -> None:
    if not key:
        return
    with _idempotency_lock:
        _idempotency[key] = (time.time(), response)


def _idempotency_gc_locked(now: float) -> None:
    stale = [k for k, (ts, _) in _idempotency.items() if now - ts > _IDEMPOTENCY_TTL_SEC]
    for k in stale:
        _idempotency.pop(k, None)


# ---------------------------------------------------------------------------
# Rate limiter — sliding window per user
# ---------------------------------------------------------------------------

_RATE_LIMIT_PER_MIN = 10
_rate_lock = threading.Lock()
_rate_events: dict[str, deque] = {}  # user -> deque of timestamps


def rate_limit_check(user: str) -> tuple[bool, int]:
    """Return (ok, remaining). ok=False means blocked."""
    user = user or "unknown"
    now = time.time()
    window_start = now - 60.0
    with _rate_lock:
        q = _rate_events.setdefault(user, deque())
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= _RATE_LIMIT_PER_MIN:
            return False, 0
        q.append(now)
        return True, _RATE_LIMIT_PER_MIN - len(q)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

AUDIT_LOG_PATH = Path(__file__).parent / "hitl_audit.jsonl"
_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB, rotate after
_audit_lock = threading.Lock()


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rotate_if_needed_locked() -> None:
    try:
        if AUDIT_LOG_PATH.exists() and AUDIT_LOG_PATH.stat().st_size > _MAX_LOG_BYTES:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            rotated = AUDIT_LOG_PATH.with_suffix(f".{ts}.jsonl")
            AUDIT_LOG_PATH.rename(rotated)
    except OSError:
        # Rotation is best-effort; never block a write on it
        pass


def audit_log(entry: dict[str, Any]) -> None:
    """Append one JSON line to the audit log. Never raises."""
    try:
        line = json.dumps(entry, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        line = json.dumps({"ts": _iso_now(), "audit_error": "unserializable entry"})
    with _audit_lock:
        _rotate_if_needed_locked()
        try:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def audit_tail(n: int = 50) -> list[dict[str, Any]]:
    """Return the last n audit entries. Used by /api/hitl-audit-tail."""
    if not AUDIT_LOG_PATH.exists():
        return []
    with _audit_lock:
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return []
    tail = lines[-max(1, int(n)):]
    out = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"raw": line, "parse_error": True})
    return out


# ---------------------------------------------------------------------------
# Safety-wrapped patch
# ---------------------------------------------------------------------------

class HitlWriteError(Exception):
    """Raised when a write is rejected by the safety layer.

    .code is a short string ('frozen', 'flag_off', 'rate_limited',
    'unknown_field', etc). The Flask endpoint maps this to an HTTP status.
    """

    def __init__(self, code: str, message: str, http_status: int = 400, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details


def _detect_unknown_field(err: urllib.error.HTTPError) -> tuple[bool, str]:
    """Inspect a 4xx from Airtable for UNKNOWN_FIELD_NAME."""
    try:
        body = err.read().decode("utf-8", errors="replace")
    except Exception:
        return False, ""
    if "UNKNOWN_FIELD_NAME" in body:
        return True, body
    return False, body


def safe_patch_task(
    *,
    action: str,
    base_key: str,
    record_id: str,
    fields: dict[str, Any],
    fields_before: dict[str, Any] | None,
    user: str,
    dry_run: bool,
    idempotency_key: str | None,
    patch_fn: Callable[[str, str, dict[str, Any]], dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run all safety layers, then (optionally) call patch_fn.

    patch_fn: the underlying _patch_task(base_key, record_id, fields) from app.py.
              Injected so this module has zero knowledge of app internals.

    Returns a dict suitable for the Flask endpoint to jsonify. On safety
    rejection raises HitlWriteError.
    """
    t0 = time.time()
    context = context or {}

    # --- 1. Idempotency (fast path) ---
    # CRITICAL: skip idempotency lookup AND store entirely when dry_run=True.
    # Dry-runs are harmless to repeat, and caching them under a UUID would
    # cause the subsequent live write (which intentionally reuses the same
    # UUID so a double-click can't cause a double-write) to be served the
    # cached dry-run response instead of actually executing. This was a real
    # bug in early Phase 2 testing — the live write never reached Airtable.
    if not dry_run:
        cached = idempotency_check(idempotency_key)
        if cached is not None:
            return {**cached, "idempotent_replay": True}

    # --- 2. Feature flag ---
    if action not in HITL_WRITE_FLAGS:
        raise HitlWriteError("unknown_action", f"Unknown action '{action}'", 400)
    if not HITL_WRITE_FLAGS[action] and not dry_run:
        raise HitlWriteError(
            "flag_off",
            f"Action '{action}' is not enabled for live writes. Use dry_run=true to preview.",
            403,
            details={"action": action},
        )

    # --- 3. Freeze ---
    if is_frozen() and not dry_run:
        fs = freeze_status()
        raise HitlWriteError(
            "frozen",
            f"Writes are frozen: {fs.get('reason') or '(no reason given)'}",
            423,
            details=fs,
        )

    # --- 4. Rate limit ---
    if not dry_run:
        ok, remaining = rate_limit_check(user)
        if not ok:
            raise HitlWriteError(
                "rate_limited",
                f"Rate limit exceeded ({_RATE_LIMIT_PER_MIN}/min).",
                429,
                details={"user": user},
            )

    # --- 5. Execute (or dry run) ---
    started = _iso_now()
    http_status: int | None = None
    error: dict[str, Any] | None = None
    response_body: dict[str, Any] | None = None

    if dry_run:
        response = {
            "ok": True,
            "dry_run": True,
            "action": action,
            "id": record_id,
            "base": base_key,
            "fields_to_write": fields,
            "fields_before": fields_before,
        }
        http_status = 200
    else:
        try:
            response_body = patch_fn(base_key, record_id, fields)
            http_status = 200
            response = {
                "ok": True,
                "dry_run": False,
                "action": action,
                "id": record_id,
                "base": base_key,
                "fields_written": fields,
                "fields_before": fields_before,
            }
        except urllib.error.HTTPError as e:
            http_status = e.code
            is_unknown, body = _detect_unknown_field(e)
            if is_unknown:
                # Auto-freeze on unknown-field: this is the silent-data-loss
                # failure mode we are most concerned about.
                set_freeze(
                    True,
                    reason=f"Auto-freeze: UNKNOWN_FIELD_NAME from Airtable on {action}",
                    user="system",
                )
                audit_log({
                    "ts": _iso_now(),
                    "event": "auto_freeze",
                    "cause": "unknown_field_name",
                    "action": action,
                    "task_id": record_id,
                    "airtable_response": body[:1000],
                })
                raise HitlWriteError(
                    "unknown_field",
                    "Airtable rejected a field name. Writes have been auto-frozen.",
                    500,
                    details={"airtable_body": body[:500]},
                )
            raise HitlWriteError(
                "airtable_http_error",
                f"Airtable returned HTTP {e.code}",
                500,
                details={"airtable_body": body[:500]},
            )
        except urllib.error.URLError as e:
            http_status = -1
            raise HitlWriteError("network_error", f"Network error: {e}", 502)
        except Exception as e:
            http_status = -1
            error = {"type": type(e).__name__, "msg": str(e)}
            raise HitlWriteError("unexpected", f"Unexpected error: {e}", 500)

    # --- 6. Audit ---
    duration_ms = int((time.time() - t0) * 1000)
    audit_log({
        "ts": started,
        "event": "write",
        "action": action,
        "user": user,
        "task_id": record_id,
        "base": base_key,
        "dry_run": dry_run,
        "idempotency_key": idempotency_key,
        "fields_before": fields_before,
        "fields_after_requested": fields,
        "http_status": http_status,
        "error": error,
        "duration_ms": duration_ms,
        "context": context,
    })

    # --- 7. Idempotency store ---
    # Only cache live-write responses. Dry-runs are inspection-only and must
    # never populate the cache, otherwise the subsequent live write with the
    # same key would be served the dry-run response (see comment at step 1).
    if not dry_run:
        idempotency_store(idempotency_key, response)

    return response


# ---------------------------------------------------------------------------
# Cascade write — batch decline across multiple related tasks
# ---------------------------------------------------------------------------
# A cascade is a single reviewer decision that writes to N tasks at once
# (current task + its siblings in the same contact/deal cluster). Common
# shapes:
#   scope="plans": decline this task + every subsequent plan-type HITL task
#   scope="all":   stop outreach entirely (all remaining tasks get Cancelled)
#
# The safety layer treats a cascade as one logical operation:
#   - One flag check (cascade_decline or stop_outreach)
#   - One rate-limit slot used
#   - One idempotency key
#   - One audit entry summarizing the whole batch + per-task outcomes
# Partial failures are surfaced as successes + pending list, never silently
# half-applied.

CASCADE_MAX_TASKS = 50  # hard cap: primary + siblings combined


def _airtable_batch_patch(
    base_id: str,
    table_id: str,
    records: list[dict[str, Any]],
    api_headers_fn: Callable[[], dict[str, str]],
    api_url_fn: Callable[[str, str], str],
) -> dict[str, Any]:
    """PATCH up to 10 records in a single Airtable call.

    records: list of {"id": "recXXX", "fields": {...}}
    Returns the raw Airtable response.
    """
    if len(records) > 10:
        raise ValueError("Airtable batch PATCH accepts at most 10 records per call")
    url = api_url_fn(base_id, table_id)
    payload = json.dumps({"records": records}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=api_headers_fn(), method="PATCH"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def safe_cascade_write(
    *,
    scope: str,                                  # "plans" or "all"
    primary: dict[str, Any],                     # {task_id, base_key, fields_to_write, fields_before, hitl_type}
    cascades: list[dict[str, Any]],              # same shape per sibling
    user: str,
    dry_run: bool,
    idempotency_key: str | None,
    base_id: str,
    table_id: str,
    api_headers_fn: Callable[[], dict[str, str]],
    api_url_fn: Callable[[str, str], str],
) -> dict[str, Any]:
    """Safety-gated batch decline across primary + cascade tasks.

    Enforces the same layers as safe_patch_task (feature flag, freeze, rate
    limit, idempotency, audit log) but for a batch of related writes. All
    writes share a single idempotency key; repeating the exact same cascade
    call is a no-op.

    Returns a dict with:
        ok:                bool
        dry_run:           bool
        scope:             "plans" | "all"
        primary:           {task_id, fields_to_write, fields_before}
        cascades:          list of same
        task_count:        int total tasks in operation (primary + cascades)
        results:           per-task {task_id, status, error?} (live only)
        idempotent_replay: bool (when cache hit)

    Raises HitlWriteError on any pre-flight rejection.
    """
    t0 = time.time()
    all_tasks = [primary] + list(cascades)
    task_count = len(all_tasks)

    # --- 0. Shape validation ---
    if scope not in ("plans", "all"):
        raise HitlWriteError("bad_scope", f"scope must be 'plans' or 'all', got {scope!r}", 400)
    if task_count > CASCADE_MAX_TASKS:
        raise HitlWriteError(
            "cascade_too_large",
            f"Cascade covers {task_count} tasks, cap is {CASCADE_MAX_TASKS}. "
            f"Split into smaller batches or contact engineering to raise the cap.",
            400,
            details={"task_count": task_count, "cap": CASCADE_MAX_TASKS},
        )

    action = "cascade_decline" if scope == "plans" else "stop_outreach"

    # --- 1. Idempotency (fast path, live-only) ---
    if not dry_run:
        cached = idempotency_check(idempotency_key)
        if cached is not None:
            return {**cached, "idempotent_replay": True}

    # --- 2. Flag ---
    if not HITL_WRITE_FLAGS.get(action, False) and not dry_run:
        raise HitlWriteError(
            "flag_off",
            f"Action '{action}' is not enabled for live writes. Use dry_run=true to preview.",
            403,
            details={"action": action},
        )

    # --- 3. Freeze ---
    if is_frozen() and not dry_run:
        fs = freeze_status()
        raise HitlWriteError(
            "frozen",
            f"Writes are frozen: {fs.get('reason') or '(no reason given)'}",
            423,
            details=fs,
        )

    # --- 4. Rate limit (cascade uses 1 slot, not N) ---
    if not dry_run:
        ok, remaining = rate_limit_check(user)
        if not ok:
            raise HitlWriteError(
                "rate_limited",
                f"Rate limit exceeded ({_RATE_LIMIT_PER_MIN}/min).",
                429,
                details={"user": user},
            )

    started = _iso_now()
    per_task_results: list[dict[str, Any]] = []

    if dry_run:
        # Just return the intended writes
        response = {
            "ok": True,
            "dry_run": True,
            "action": action,
            "scope": scope,
            "primary": primary,
            "cascades": cascades,
            "task_count": task_count,
        }
    else:
        # Execute live: batch PATCH up to 10 at a time. On first batch failure,
        # we stop and surface the partial result honestly.
        any_failures = False
        first_error: dict[str, Any] | None = None
        i = 0
        while i < task_count:
            batch = all_tasks[i : i + 10]
            batch_records = [
                {"id": t["task_id"], "fields": t["fields_to_write"]}
                for t in batch
            ]
            try:
                _airtable_batch_patch(
                    base_id, table_id, batch_records, api_headers_fn, api_url_fn
                )
                for t in batch:
                    per_task_results.append({"task_id": t["task_id"], "status": "written"})
            except urllib.error.HTTPError as e:
                any_failures = True
                is_unknown, body = _detect_unknown_field(e)
                err = {
                    "type": "http",
                    "http_status": e.code,
                    "airtable_body": body[:500],
                    "is_unknown_field": is_unknown,
                }
                first_error = err
                for t in batch:
                    per_task_results.append({"task_id": t["task_id"], "status": "failed", "error": err})
                if is_unknown:
                    set_freeze(
                        True,
                        reason=f"Auto-freeze: UNKNOWN_FIELD_NAME from Airtable during cascade {scope}",
                        user="system",
                    )
                    audit_log({
                        "ts": _iso_now(),
                        "event": "auto_freeze",
                        "cause": "unknown_field_name",
                        "action": action,
                        "scope": scope,
                        "batch_start_index": i,
                        "airtable_response": body[:1000],
                    })
                break
            except urllib.error.URLError as e:
                any_failures = True
                first_error = {"type": "network", "msg": str(e)}
                for t in batch:
                    per_task_results.append({"task_id": t["task_id"], "status": "failed", "error": first_error})
                break
            i += 10

        # Tasks not yet attempted (after a failure) get a "pending" status
        already_handled = {r["task_id"] for r in per_task_results}
        for t in all_tasks:
            if t["task_id"] not in already_handled:
                per_task_results.append({"task_id": t["task_id"], "status": "pending"})

        response = {
            "ok": not any_failures,
            "dry_run": False,
            "action": action,
            "scope": scope,
            "primary": primary,
            "cascades": cascades,
            "task_count": task_count,
            "results": per_task_results,
        }
        if first_error:
            response["first_error"] = first_error

    # --- 6. Audit ---
    duration_ms = int((time.time() - t0) * 1000)
    audit_log({
        "ts": started,
        "event": "cascade_write",
        "action": action,
        "scope": scope,
        "user": user,
        "primary_task_id": primary.get("task_id"),
        "cascade_task_ids": [t.get("task_id") for t in cascades],
        "task_count": task_count,
        "dry_run": dry_run,
        "idempotency_key": idempotency_key,
        "ok": response.get("ok"),
        "per_task_results": per_task_results if not dry_run else None,
        "duration_ms": duration_ms,
    })

    # --- 7. Idempotency store (live only) ---
    if not dry_run:
        idempotency_store(idempotency_key, response)

    return response


# ---------------------------------------------------------------------------
# Diff helper — compute which fields actually differ from current values
# ---------------------------------------------------------------------------

def diff_fields(
    before: dict[str, Any],
    proposed: dict[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """Return {field: (before_value, proposed_value)} for fields that differ.

    A proposed value that equals the current value is a no-op — the Flask
    endpoint uses this to drop no-op fields from the PATCH payload.
    """
    out: dict[str, tuple[Any, Any]] = {}
    for k, new_v in proposed.items():
        old_v = before.get(k)
        if _normalize(old_v) != _normalize(new_v):
            out[k] = (old_v, new_v)
    return out


def _normalize(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip()
    return v
