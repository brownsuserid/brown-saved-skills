#!/usr/bin/env python3
"""
Work Queue — web UI for managing AI agent tasks and reviewing HITL approvals.

Usage:
    source ~/.zshrc && python3 app.py

Runs on http://localhost:5151
"""

import json
import os
import queue
import sys
import threading
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, jsonify, request, stream_with_context

# Wire up imports from existing skills
SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
sys.path.insert(0, os.path.join(SKILLS_DIR, "airtable-config"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "executing-tasks", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "setting-todays-priorities", "scripts"))

# Load a local .env file (if present) BEFORE importing airtable_config so
# AIRTABLE_TOKEN is in os.environ when airtable_config reads it. Purely
# additive — if no .env file exists, nothing happens and behavior is
# unchanged. Does not override env vars already set by the shell.
def _load_dotenv():
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

_load_dotenv()

import airtable_config  # noqa: E402
from search_tasks import (  # noqa: E402
    _fetch_record,
    build_filter,
    resolve_assignee_id,
    search_base,
    resolve_hierarchy,
)
from set_for_today import update_for_today  # noqa: E402

# HITL writeback safety layer. Co-located in this directory so it is editable
# alongside the Flask app without crossing skill boundaries. See hitl_safety.py
# for rationale and layer-by-layer docs.
import hitl_safety  # noqa: E402
import hitl_live_data  # noqa: E402

app = Flask(__name__)

CONFIG = airtable_config.load_config()
PHOENIX_TZ = timezone(timedelta(hours=-7))


# CORS for the prototype-only HITL endpoints. Scoped to specific paths so
# Aaron's /hitl page and /api/hitl-respond are not touched. Permits the
# static-server origin (localhost:8080) to call the Flask backend.
_PROTOTYPE_CORS_PATHS = {
    "/api/hitl-respond-safe",
    "/api/hitl-preview",
    "/api/hitl-cascade-decline",
    "/api/hitl-freeze",
    "/api/hitl-flags",
    "/api/hitl-audit-tail",
    "/api/hitl-live-data",
    "/api/hitl-status",
}
_ALLOWED_ORIGINS = {
    "http://localhost:8080",
    "http://127.0.0.1:8080",
}


@app.after_request
def _prototype_cors(response):
    origin = request.headers.get("Origin", "")
    if request.path in _PROTOTYPE_CORS_PATHS and origin in _ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "600"
    return response


@app.route(
    "/api/hitl-respond-safe", methods=["OPTIONS"], endpoint="_cors_preflight_safe"
)
@app.route(
    "/api/hitl-preview", methods=["OPTIONS"], endpoint="_cors_preflight_preview"
)
@app.route(
    "/api/hitl-freeze", methods=["OPTIONS"], endpoint="_cors_preflight_freeze"
)
@app.route(
    "/api/hitl-flags", methods=["OPTIONS"], endpoint="_cors_preflight_flags"
)
@app.route(
    "/api/hitl-audit-tail", methods=["OPTIONS"], endpoint="_cors_preflight_audit"
)
@app.route(
    "/api/hitl-cascade-decline", methods=["OPTIONS"], endpoint="_cors_preflight_cascade"
)
@app.route(
    "/api/hitl-live-data", methods=["OPTIONS"], endpoint="_cors_preflight_livedata"
)
@app.route(
    "/api/hitl-status", methods=["OPTIONS"], endpoint="_cors_preflight_status"
)
def _cors_preflight():
    """Bare 204 for CORS preflight. Headers are added by the after_request hook."""
    return ("", 204)


def _task_slim(t: dict) -> dict:
    return {
        "id": t.get("id"),
        "task": t.get("task", ""),
        "description": t.get("description", ""),
        "status": t.get("status", ""),
        "score": t.get("score", ""),
        "due_date": t.get("due_date", ""),
        "base": t.get("base", ""),
        "project_name": t.get("project_name", ""),
        "airtable_url": t.get("airtable_url", ""),
        "created_time": t.get("created_time", ""),
        "updated_time": t.get("updated_time", ""),
    }


def _current_user() -> str:
    return CONFIG.get("current_user", "aaron")


def fetch_all_tasks(assignee: str | None = None, max_per_base: int = 200) -> list:
    """Fetch all active tasks across all bases for an assignee, plus unassigned tasks."""
    if assignee is None:
        assignee = _current_user()

    bases = airtable_config.get_bases(CONFIG)
    seen_ids: set[str] = set()
    all_tasks = []

    for base_key in bases:
        base_cfg = bases[base_key]
        base_formula = build_filter(
            CONFIG, base_key, status=None, query=None, include_done=False
        )

        # Exclude Human Review tasks — those belong on the HITL page
        human_review_val = base_cfg.get("status_values", {}).get(
            "human_review", "Human Review"
        )
        hr_exclusion = f"{{Status}}!='{human_review_val}'"
        base_formula = (
            f"AND({base_formula},{hr_exclusion})" if base_formula else hr_exclusion
        )

        # Fetch assigned tasks
        assignee_id = resolve_assignee_id(CONFIG, assignee, base_key)
        tasks = search_base(CONFIG, base_key, base_formula, max_per_base, assignee_id)
        for t in tasks:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                all_tasks.append(t)

        # Fetch unassigned tasks (empty Assignee field)
        assignee_field = base_cfg["assignee_field"]
        unassigned_cond = f"{{{assignee_field}}}=BLANK()"
        if base_formula:
            unassigned_formula = f"AND({base_formula},{unassigned_cond})"
        else:
            unassigned_formula = unassigned_cond
        unassigned = search_base(
            CONFIG, base_key, unassigned_formula, max_per_base, None
        )
        for t in unassigned:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                t["_unassigned"] = True
                all_tasks.append(t)

    all_tasks.sort(key=lambda t: t.get("score") or 0, reverse=True)

    # Resolve project/rock names and campaign links
    resolve_hierarchy(CONFIG, all_tasks, include_mountains=False, include_goals=False)
    _resolve_campaigns(CONFIG, all_tasks)

    return all_tasks


@app.route("/")
def index():
    return HTML_PAGE


@app.route("/api/config")
def api_config():
    people = list(airtable_config.get_people(CONFIG).keys())
    return jsonify({"current_user": _current_user(), "people": people})


@app.route("/api/tasks")
def api_tasks():
    assignee = request.args.get("assignee") or _current_user()
    tasks = fetch_all_tasks(assignee)
    slim = []
    for t in tasks:
        row = _task_slim(t)
        row["for_today"] = t.get("for_today", False)
        row["_unassigned"] = t.get("_unassigned", False)
        row["deal_ids"] = t.get("deal_ids", [])
        row["campaign_name"] = t.get("campaign_name", "")
        row["campaign_url"] = t.get("campaign_url", "")
        slim.append(row)
    return jsonify(slim)


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.json
    record_id = data.get("id")
    base_key = data.get("base")
    value = data.get("value")

    if not record_id or not base_key or value is None:
        return jsonify({"error": "Missing id, base, or value"}), 400

    try:
        update_for_today(record_id, base_key, value, CONFIG)
        return jsonify({"ok": True, "id": record_id, "for_today": value})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return jsonify({"error": f"HTTP {e.code}: {body}"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _patch_task(base_key: str, record_id: str, fields: dict) -> dict:
    """PATCH a task record via the Airtable API."""
    base_cfg = airtable_config.get_base(CONFIG, base_key)
    url = f"{airtable_config.api_url(base_cfg['base_id'], base_cfg['tasks_table_id'])}/{record_id}"
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers=airtable_config.api_headers(),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode())


def _delete_task(base_key: str, record_id: str) -> None:
    """DELETE a task record via the Airtable API."""
    base_cfg = airtable_config.get_base(CONFIG, base_key)
    url = f"{airtable_config.api_url(base_cfg['base_id'], base_cfg['tasks_table_id'])}/{record_id}"
    req = urllib.request.Request(
        url,
        headers=airtable_config.api_headers(),
        method="DELETE",
    )
    with urllib.request.urlopen(req):
        pass


@app.route("/api/complete", methods=["POST"])
def api_complete():
    data = request.json
    record_id = data.get("id")
    base_key = data.get("base")

    if not record_id or not base_key:
        return jsonify({"error": "Missing id or base"}), 400

    try:
        base_cfg = airtable_config.get_base(CONFIG, base_key)
        status_val = base_cfg["status_values"]["complete"]
        fields = {
            base_cfg["status_field"]: status_val,
            "Date Complete": datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d"),
        }
        _patch_task(base_key, record_id, fields)
        return jsonify({"ok": True, "id": record_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _resolve_campaigns(config: dict, tasks: list) -> None:
    """Annotate tasks with campaign_name and campaign_url by resolving Deals → Campaigns."""
    bases = airtable_config.get_bases(config)
    deal_campaign_cache: dict[str, list] = {}
    campaign_name_cache: dict[str, str] = {}

    for task in tasks:
        base_key = task.get("base")
        if not base_key or base_key not in bases:
            continue
        base_cfg = bases[base_key]
        campaigns_table_id = (base_cfg.get("tables") or {}).get("campaigns")
        deals_table_id = base_cfg.get("deals_table_id")
        deals_campaign_field = base_cfg.get("deals_campaign_field")
        if not campaigns_table_id or not deals_table_id or not deals_campaign_field:
            continue

        deal_ids = task.get("deal_ids", [])
        if not deal_ids:
            continue

        deal_id = deal_ids[0]
        if deal_id not in deal_campaign_cache:
            record = _fetch_record(
                base_cfg["base_id"],
                deals_table_id,
                deal_id,
                config=config,
                base_key=base_key,
            )
            deal_campaign_cache[deal_id] = (
                record["fields"].get(deals_campaign_field, []) if record else []
            )

        campaign_ids = deal_campaign_cache[deal_id]
        if not campaign_ids:
            continue

        campaign_id = campaign_ids[0]
        if campaign_id not in campaign_name_cache:
            record = _fetch_record(
                base_cfg["base_id"],
                campaigns_table_id,
                campaign_id,
                config=config,
                base_key=base_key,
            )
            campaign_name_cache[campaign_id] = (
                record["fields"].get("Name", "") if record else ""
            )

        name = campaign_name_cache[campaign_id]
        if name:
            task["campaign_name"] = name
            task["campaign_url"] = airtable_config.airtable_record_url(
                base_cfg["base_id"], campaigns_table_id, campaign_id
            )


def fetch_hitl_tasks(
    assignee: str | None = None,
    count_only: bool = False,
    status_queue: queue.Queue | None = None,
) -> list:
    """Fetch HITL review tasks across all bases, optionally filtered by assignee."""

    def emit(msg: str) -> None:
        if status_queue is not None:
            status_queue.put(("status", msg))

    bases = airtable_config.get_bases(CONFIG)
    hitl_tasks = []

    for base_key in bases:
        base_cfg = bases[base_key]
        hitl_status_field = base_cfg.get("hitl_status_field")
        if not hitl_status_field:
            continue

        emit(f"Querying {base_key}...")
        assignee_id = (
            resolve_assignee_id(CONFIG, assignee, base_key) if assignee else None
        )

        status_values = base_cfg.get("status_values", {})
        in_progress_val = status_values.get("in_progress", "In Progress")
        human_review_val = status_values.get("human_review", "Human Review")

        plan_formula = (
            f"AND({{Status}}='{in_progress_val}',{{{hitl_status_field}}}='Processed')"
        )
        for t in search_base(CONFIG, base_key, plan_formula, 1000, assignee_id):
            t["hitl_type"] = "plan"
            hitl_tasks.append(t)

        output_formula = (
            f"AND({{Status}}='{human_review_val}',"
            f"{{{hitl_status_field}}}='Pending Review')"
        )
        for t in search_base(CONFIG, base_key, output_formula, 1000, assignee_id):
            t["hitl_type"] = "output"
            hitl_tasks.append(t)

    if count_only:
        return hitl_tasks

    hitl_tasks.sort(key=lambda t: t.get("score") or 0, reverse=True)
    emit("Resolving projects...")
    resolve_hierarchy(CONFIG, hitl_tasks, include_mountains=False, include_goals=False)
    emit("Resolving campaigns...")
    _resolve_campaigns(CONFIG, hitl_tasks)
    return hitl_tasks


def _hitl_slim_row(t: dict, outreach_mgr_id: str) -> dict:
    row = _task_slim(t)
    row.update(
        {
            "hitl_type": t.get("hitl_type", "plan"),
            "hitl_brief": t.get("hitl_brief", ""),
            "hitl_response": t.get("hitl_response", ""),
            "hitl_status": t.get("hitl_status", ""),
            "task_output": t.get("task_output", ""),
            "is_gtm": bool(
                outreach_mgr_id and outreach_mgr_id in t.get("deal_assignee", "")
            ),
            "campaign_name": t.get("campaign_name", ""),
            "campaign_url": t.get("campaign_url", ""),
            "deal_ids": t.get("deal_ids", []),
        }
    )
    return row


@app.route("/hitl")
def hitl_page():
    return HITL_PAGE


@app.route("/api/hitl-count")
def api_hitl_count():
    assignee = request.args.get("assignee") or _current_user()
    tasks = fetch_hitl_tasks(assignee, count_only=True)
    return jsonify({"count": len(tasks)})


@app.route("/api/hitl-tasks")
def api_hitl_tasks():
    assignee = request.args.get("assignee") or _current_user()
    tasks = fetch_hitl_tasks(assignee)
    people = airtable_config.get_people(CONFIG)
    outreach_mgr_id = people.get("outreach_manager", {}).get("bb", "")
    return jsonify([_hitl_slim_row(t, outreach_mgr_id) for t in tasks])


@app.route("/api/hitl-tasks-stream")
def api_hitl_tasks_stream():
    assignee = request.args.get("assignee") or _current_user()
    q: queue.Queue = queue.Queue()

    def run() -> None:
        try:
            people = airtable_config.get_people(CONFIG)
            outreach_mgr_id = people.get("outreach_manager", {}).get("bb", "")
            tasks = fetch_hitl_tasks(assignee, status_queue=q)
            slim = [_hitl_slim_row(t, outreach_mgr_id) for t in tasks]
            q.put(("done", slim))
        except Exception as exc:
            q.put(("error", str(exc)))

    def generate():
        t = threading.Thread(target=run, daemon=True)
        t.start()
        while True:
            try:
                event_type, data = q.get(timeout=60)
            except queue.Empty:
                yield 'event: error\ndata: {"error": "timeout"}\n\n'
                break
            if event_type == "status":
                yield f"event: status\ndata: {json.dumps(data)}\n\n"
            elif event_type == "done":
                yield f"event: done\ndata: {json.dumps(data)}\n\n"
                break
            else:
                yield f"event: error\ndata: {json.dumps({'error': data})}\n\n"
                break

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/hitl-respond", methods=["POST"])
def api_hitl_respond():
    """Original HITL approve/decline endpoint used by Aaron's /hitl page.

    Behavior preserved EXACTLY as written originally. Do not add safety-layer
    coupling here. New prototype traffic uses /api/hitl-respond-safe instead.
    """
    data = request.json
    record_id = data.get("id")
    base_key = data.get("base")
    approved = data.get("approved", False)
    hitl_type = data.get("hitl_type", "plan")
    response_text = data.get("response", "").strip()

    if not record_id or not base_key:
        return jsonify({"error": "Missing id or base"}), 400
    if not approved and not response_text:
        return jsonify({"error": "Response required when declining"}), 400

    try:
        base_cfg = airtable_config.get_base(CONFIG, base_key)
        hitl_status_field = base_cfg.get("hitl_status_field")
        hitl_response_field = base_cfg.get("hitl_response_field")

        if not hitl_status_field:
            return jsonify({"error": "Base does not support HITL"}), 400

        if approved and hitl_type == "output":
            status_val = base_cfg["status_values"]["complete"]
            fields = {
                base_cfg["status_field"]: status_val,
                "Date Complete": datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d"),
            }
        else:
            fields = {hitl_status_field: "Response Submitted"}
            if hitl_response_field and response_text:
                fields[hitl_response_field] = response_text

        _patch_task(base_key, record_id, fields)
        return jsonify({"ok": True, "id": record_id, "approved": approved})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Prototype-only safety-gated HITL write endpoint
# ---------------------------------------------------------------------------
# Parallel to /api/hitl-respond. All new prototype traffic routes here. Does
# not touch Aaron's /hitl page or /api/hitl-respond behavior in any way.

def _fetch_task_fields(base_key: str, record_id: str) -> dict:
    """Fetch the current fields dict of a task record. Returns {} on miss."""
    base_cfg = airtable_config.get_base(CONFIG, base_key)
    rec = _fetch_record(base_cfg["base_id"], base_cfg["tasks_table_id"], record_id)
    if not rec:
        return {}
    return rec.get("fields", {}) or {}


def _derive_hitl_action(
    approved: bool,
    hitl_type: str,
    has_def_of_done_edit: bool,
) -> str:
    """Map (approved, hitl_type, edit-flag) -> safety flag name."""
    if approved:
        if hitl_type == "output":
            return "approve_output_edits" if has_def_of_done_edit else "approve_output_asis"
        return "approve_plan"
    return "decline"


@app.route("/api/hitl-respond-safe", methods=["POST"])
def api_hitl_respond_safe():
    """Safety-gated HITL approve / decline used by the prototype.

    Accepted request fields:
        id                  (str, required)    Airtable record id
        base                (str, required)    Base key from airtable_config
        approved            (bool)             True for approve, False for decline
        hitl_type           (str)              "output" or "plan"
        response            (str)              Reviewer note / HITL Response text
        definition_of_done  (str, optional)    Edited email draft. Omit when
                                               the draft is unchanged.
        dry_run             (bool)             If true, build payload but do not PATCH
        idempotency_key     (str, optional)    UUID from UI. Same key within 10 min
                                               returns the first response, no-op.
        user                (str, optional)    Actor email for audit log.
    """
    data = request.json or {}
    record_id = data.get("id")
    base_key = data.get("base")
    approved = bool(data.get("approved", False))
    hitl_type = data.get("hitl_type", "plan")
    response_text = (data.get("response") or "").strip()
    dod_edit = data.get("definition_of_done")
    dry_run = bool(data.get("dry_run", False))
    idempotency_key = data.get("idempotency_key")
    user = data.get("user") or _current_user()

    if not record_id or not base_key:
        return jsonify({"error": "Missing id or base"}), 400
    if not approved and not response_text:
        return jsonify({"error": "Response required when declining"}), 400

    try:
        base_cfg = airtable_config.get_base(CONFIG, base_key)
    except KeyError:
        return jsonify({"error": f"Unknown base '{base_key}'"}), 400

    hitl_status_field = base_cfg.get("hitl_status_field")
    hitl_response_field = base_cfg.get("hitl_response_field")
    status_field = base_cfg["status_field"]
    description_field = base_cfg.get("description_field", "Definition of Done")

    if not hitl_status_field:
        return jsonify({"error": "Base does not support HITL"}), 400

    fields_before = _fetch_task_fields(base_key, record_id)
    if not fields_before:
        hitl_safety.audit_log({
            "ts": hitl_safety._iso_now(),
            "event": "snapshot_miss",
            "task_id": record_id,
            "base": base_key,
            "note": "Could not read current fields_before; proceeding anyway",
        })

    has_dod_edit = False
    if dod_edit is not None:
        original_dod = (fields_before.get(description_field) or "").strip()
        proposed_dod = (dod_edit or "").strip()
        has_dod_edit = proposed_dod != original_dod and proposed_dod != ""

    today = datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d")
    if approved and hitl_type == "output":
        fields: dict = {
            status_field: base_cfg["status_values"]["complete"],
            "Date Complete": today,
            hitl_status_field: "Response Submitted",
        }
        if has_dod_edit:
            fields[description_field] = dod_edit
            default_note = "Approved with edits"
        else:
            default_note = "Approved as-is"
        if hitl_response_field:
            fields[hitl_response_field] = response_text or default_note
    elif approved:
        fields = {hitl_status_field: "Response Submitted"}
        if has_dod_edit:
            fields[description_field] = dod_edit
            default_note = "Approved with edits"
        else:
            default_note = "Approved"
        if hitl_response_field:
            fields[hitl_response_field] = response_text or default_note
    else:
        fields = {hitl_status_field: "Response Submitted"}
        if hitl_response_field and response_text:
            fields[hitl_response_field] = response_text

    diff = hitl_safety.diff_fields(fields_before, fields)
    fields_to_write = {k: v for k, v in fields.items() if k in diff}

    if not fields_to_write:
        return jsonify({
            "ok": True,
            "id": record_id,
            "approved": approved,
            "noop": True,
            "message": "All proposed values already match current record; nothing to write.",
        })

    action = _derive_hitl_action(approved, hitl_type, has_dod_edit)

    try:
        result = hitl_safety.safe_patch_task(
            action=action,
            base_key=base_key,
            record_id=record_id,
            fields=fields_to_write,
            fields_before={k: fields_before.get(k) for k in fields_to_write.keys()},
            user=user,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
            patch_fn=_patch_task,
            context={"hitl_type": hitl_type, "approved": approved},
        )
        result.setdefault("approved", approved)
        # A successful live write changes Airtable state that our live-data
        # cache now holds stale. Invalidate so the next /api/hitl-live-data
        # call triggers a fresh rebuild.
        if not dry_run and result.get("ok"):
            hitl_live_data.invalidate_cache()
        return jsonify(result)
    except hitl_safety.HitlWriteError as e:
        return jsonify({
            "error": e.message,
            "code": e.code,
            "details": e.details,
        }), e.http_status
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Cascade decline endpoint — prototype-only
# ---------------------------------------------------------------------------
# A cascade write is one reviewer decision that propagates to N tasks. The
# caller supplies the primary task and the list of sibling task ids that
# should be cascaded. Scope drives what gets written to each sibling.
#
# Request shape:
# {
#   "id": "recXXX",                 // primary task id
#   "base": "bb",
#   "hitl_type": "output" | "plan",
#   "response": "reviewer note",
#   "definition_of_done": "...",    // optional, for primary only
#   "cascade_task_ids": ["recAAA", "recBBB", ...],  // siblings to cascade
#   "scope": "plans" | "all",
#   "dry_run": true,
#   "idempotency_key": "uuid",
#   "user": "brown@brainbridge.app"
# }

def _build_cascade_task_payload(
    base_cfg: dict,
    scope: str,
    current_fields: dict,
    note_text: str,
) -> dict:
    """Build the field writes for a SINGLE cascaded task (not the primary).

    scope="plans": decline semantics only (HITL Status + HITL Response)
    scope="all":   decline + Status=Cancelled
    """
    hitl_status_field = base_cfg["hitl_status_field"]
    hitl_response_field = base_cfg.get("hitl_response_field")
    status_field = base_cfg["status_field"]

    if scope == "plans":
        reason = "Cascade declined"
    else:
        reason = "Stopped by reviewer"
    note = f"{reason}: {note_text}" if note_text else reason

    proposed = {hitl_status_field: "Response Submitted"}
    if hitl_response_field:
        proposed[hitl_response_field] = note
    if scope == "all":
        proposed[status_field] = base_cfg["status_values"].get("cancelled", "Cancelled")

    diff = hitl_safety.diff_fields(current_fields, proposed)
    return {k: v for k, v in proposed.items() if k in diff}


@app.route("/api/hitl-cascade-decline", methods=["POST"])
def api_hitl_cascade_decline():
    data = request.json or {}
    record_id = data.get("id")
    base_key = data.get("base")
    hitl_type = data.get("hitl_type", "plan")
    response_text = (data.get("response") or "").strip()
    dod_edit = data.get("definition_of_done")
    cascade_ids = data.get("cascade_task_ids") or []
    scope = data.get("scope")
    dry_run = bool(data.get("dry_run", False))
    idempotency_key = data.get("idempotency_key")
    user = data.get("user") or _current_user()

    # Shape validation
    if not record_id or not base_key:
        return jsonify({"error": "Missing id or base"}), 400
    if scope not in ("plans", "all"):
        return jsonify({"error": "scope must be 'plans' or 'all'"}), 400
    if not response_text:
        return jsonify({"error": "Response note required for a cascade decline"}), 400
    if not isinstance(cascade_ids, list):
        return jsonify({"error": "cascade_task_ids must be a list"}), 400
    for cid in cascade_ids:
        if not isinstance(cid, str) or not cid.startswith("rec"):
            return jsonify({"error": f"Invalid cascade task id: {cid!r}"}), 400

    try:
        base_cfg = airtable_config.get_base(CONFIG, base_key)
    except KeyError:
        return jsonify({"error": f"Unknown base '{base_key}'"}), 400

    hitl_status_field = base_cfg.get("hitl_status_field")
    hitl_response_field = base_cfg.get("hitl_response_field")
    description_field = base_cfg.get("description_field", "Definition of Done")

    if not hitl_status_field:
        return jsonify({"error": "Base does not support HITL"}), 400

    # --- Build the primary task write (decline semantics) ---
    primary_before = _fetch_task_fields(base_key, record_id)
    if not primary_before:
        hitl_safety.audit_log({
            "ts": hitl_safety._iso_now(),
            "event": "snapshot_miss",
            "task_id": record_id,
            "base": base_key,
            "note": "cascade primary snapshot miss",
        })

    primary_proposed: dict = {hitl_status_field: "Response Submitted"}
    if hitl_response_field:
        primary_proposed[hitl_response_field] = response_text
    if scope == "all":
        primary_proposed[base_cfg["status_field"]] = base_cfg["status_values"].get(
            "cancelled", "Cancelled"
        )
    # Primary may also carry an edited Definition of Done (rare for decline,
    # but the UI may surface it if the user edited before deciding to reject)
    has_dod_edit = False
    if dod_edit is not None:
        original = (primary_before.get(description_field) or "").strip()
        proposed = (dod_edit or "").strip()
        has_dod_edit = proposed != original and proposed != ""
        if has_dod_edit:
            primary_proposed[description_field] = dod_edit
    primary_diff = hitl_safety.diff_fields(primary_before, primary_proposed)
    primary_fields_to_write = {k: v for k, v in primary_proposed.items() if k in primary_diff}

    primary = {
        "task_id": record_id,
        "hitl_type": hitl_type,
        "fields_to_write": primary_fields_to_write,
        "fields_before": {k: primary_before.get(k) for k in primary_fields_to_write},
    }

    # --- Build each cascade task's write ---
    cascades: list[dict] = []
    for cid in cascade_ids:
        before = _fetch_task_fields(base_key, cid)
        if not before:
            hitl_safety.audit_log({
                "ts": hitl_safety._iso_now(),
                "event": "snapshot_miss",
                "task_id": cid,
                "base": base_key,
                "note": "cascade sibling snapshot miss",
            })
        to_write = _build_cascade_task_payload(base_cfg, scope, before, response_text)
        if not to_write:
            # Nothing to change for this task — skip entirely rather than
            # sending an empty PATCH (Airtable would still mark it modified)
            continue
        cascades.append({
            "task_id": cid,
            "fields_to_write": to_write,
            "fields_before": {k: before.get(k) for k in to_write},
        })

    if not primary_fields_to_write and not cascades:
        return jsonify({
            "ok": True,
            "noop": True,
            "message": "Nothing to write; all proposed values already match Airtable.",
        })

    # --- Hand off to the safety layer ---
    try:
        result = hitl_safety.safe_cascade_write(
            scope=scope,
            primary=primary,
            cascades=cascades,
            user=user,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
            base_id=base_cfg["base_id"],
            table_id=base_cfg["tasks_table_id"],
            api_headers_fn=airtable_config.api_headers,
            api_url_fn=airtable_config.api_url,
        )
        # A successful live cascade changes Airtable state. Invalidate the
        # live-data cache so the next prototype refresh reflects the new
        # truth immediately.
        if not dry_run and result.get("ok"):
            hitl_live_data.invalidate_cache()
        return jsonify(result)
    except hitl_safety.HitlWriteError as e:
        return jsonify({
            "error": e.message,
            "code": e.code,
            "details": e.details,
        }), e.http_status
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Safety-control endpoints (no-op for existing UI; used by the prototype)
# ---------------------------------------------------------------------------

@app.route("/api/hitl-freeze", methods=["GET", "POST"])
def api_hitl_freeze():
    """GET: return freeze status. POST: set freeze on/off."""
    if request.method == "GET":
        return jsonify(hitl_safety.freeze_status())
    data = request.json or {}
    state = hitl_safety.set_freeze(
        bool(data.get("frozen", False)),
        reason=data.get("reason", ""),
        user=data.get("user") or _current_user(),
    )
    hitl_safety.audit_log({
        "ts": hitl_safety._iso_now(),
        "event": "freeze_set",
        "state": state,
    })
    return jsonify(state)


@app.route("/api/hitl-flags", methods=["GET", "POST"])
def api_hitl_flags():
    """GET: return feature-flag dict. POST: flip one flag.

    POST body: {"action": "approve_output_asis", "enabled": true, "user": "..."}
    """
    if request.method == "GET":
        return jsonify({
            "flags": dict(hitl_safety.HITL_WRITE_FLAGS),
            "frozen": hitl_safety.is_frozen(),
        })
    data = request.json or {}
    action = data.get("action")
    enabled = bool(data.get("enabled", False))
    if action not in hitl_safety.HITL_WRITE_FLAGS:
        return jsonify({"error": f"Unknown action '{action}'"}), 400
    hitl_safety.HITL_WRITE_FLAGS[action] = enabled
    hitl_safety.audit_log({
        "ts": hitl_safety._iso_now(),
        "event": "flag_set",
        "action": action,
        "enabled": enabled,
        "user": data.get("user") or _current_user(),
    })
    return jsonify({"flags": dict(hitl_safety.HITL_WRITE_FLAGS)})


@app.route("/api/hitl-status", methods=["GET"])
def api_hitl_status():
    """Return current Status + HITL Status for a comma-separated list of
    task record IDs. Used by the prototype to verify freshness before
    rendering a cluster: any task not still in a pending HITL state gets
    filtered out, and if the whole cluster has been processed since last
    load, the prototype bounces the user back to home.

    Query param:
        ids=recAAA,recBBB,recCCC   (max 50)

    Response:
        {
          "statuses": {
            "recAAA": {"status": "Human Review", "hitl_status": "Pending Review", "still_pending": true},
            "recBBB": {"status": "Completed", "hitl_status": "Response Submitted", "still_pending": false},
            "recMISSING": {"error": "not_found", "still_pending": false},
            ...
          }
        }
    """
    ids_raw = request.args.get("ids", "")
    ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
    if not ids:
        return jsonify({"error": "No ids provided"}), 400
    if len(ids) > 50:
        return jsonify({"error": f"Too many ids ({len(ids)}, max 50)"}), 400
    for rid in ids:
        if not rid.startswith("rec"):
            return jsonify({"error": f"Invalid id {rid!r}"}), 400

    base_cfg = airtable_config.get_base(CONFIG, "bb")
    base_id = base_cfg["base_id"]
    table_id = base_cfg["tasks_table_id"]

    # One filter call covers all ids — batched OR().
    formula = "OR(" + ",".join(f"RECORD_ID()='{rid}'" for rid in ids) + ")"
    url = f"{airtable_config.api_url(base_id, table_id)}?{urllib.parse.urlencode({'filterByFormula': formula, 'pageSize': 50})}"
    req = urllib.request.Request(url, headers=airtable_config.api_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return jsonify({
            "error": f"Airtable HTTP {e.code}",
            "code": "airtable_http_error",
            "details": {"airtable_body": body},
        }), 502
    except Exception as e:
        return jsonify({"error": str(e), "code": "unexpected"}), 500

    # Build response keyed by id. Mark ids not returned as "not_found"
    # (task may have been deleted or isn't in BB base).
    got: dict[str, dict] = {}
    for rec in data.get("records", []):
        f = rec.get("fields", {}) or {}
        status = f.get("Status", "")
        hitl_status = f.get("HITL Status", "")
        # A task is still pending HITL if:
        #   Output task: Status == "Human Review" AND HITL Status == "Pending Review"
        #   Plan task:   Status == "In Progress"  AND HITL Status == "Processed"
        still_pending = (
            (status == "Human Review" and hitl_status == "Pending Review")
            or (status == "In Progress" and hitl_status == "Processed")
        )
        got[rec["id"]] = {
            "status": status,
            "hitl_status": hitl_status,
            "still_pending": bool(still_pending),
        }
    for rid in ids:
        if rid not in got:
            got[rid] = {"error": "not_found", "still_pending": False}

    return jsonify({"statuses": got, "queried": len(ids), "returned": len(data.get("records", []))})


# Needed by api_hitl_status; centralizing the import here to match app.py style.
import urllib.parse  # noqa: E402


@app.route("/api/hitl-live-data", methods=["GET"])
def api_hitl_live_data():
    """Return the full HITL data payload (tasks + contacts + campaigns + stats)
    computed LIVE from Airtable. Used by the prototype in place of the stale
    embedded JSON snapshot.

    Query params:
        force=1  - bypass the 60-second in-memory cache and force a rebuild
    """
    force = request.args.get("force") in ("1", "true", "yes")
    try:
        payload = hitl_live_data.build_live_data(airtable_config, force=force)
        return jsonify(payload)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return jsonify({
            "error": f"Airtable HTTP {e.code}",
            "code": "airtable_http_error",
            "details": {"airtable_body": body},
        }), 502
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "code": "unexpected",
        }), 500


@app.route("/api/hitl-audit-tail", methods=["GET"])
def api_hitl_audit_tail():
    n = request.args.get("n", "50")
    try:
        n_int = max(1, min(500, int(n)))
    except ValueError:
        n_int = 50
    return jsonify({"entries": hitl_safety.audit_tail(n_int)})


@app.route("/api/hitl-preview", methods=["POST"])
def api_hitl_preview():
    """Dry-run convenience wrapper: forces dry_run=true regardless of what
    the client sent. Same request shape as /api/hitl-respond-safe. Used by
    the prototype's preview-before-write modal so the client cannot
    accidentally execute a live write from a preview call."""
    payload = dict(request.json or {})
    payload["dry_run"] = True
    with app.test_request_context(
        "/api/hitl-respond-safe",
        method="POST",
        json=payload,
    ):
        return api_hitl_respond_safe()


@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = request.json
    record_id = data.get("id")
    base_key = data.get("base")

    if not record_id or not base_key:
        return jsonify({"error": "Missing id or base"}), 400

    try:
        _delete_task(base_key, record_id)
        return jsonify({"ok": True, "id": record_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Work Queue</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a; color: #e0e0e0;
    padding: 24px; max-width: 1400px; margin: 0 auto;
  }
  .sticky-header {
    position: sticky; top: 0; z-index: 20; background: #0a0a0a;
    padding-bottom: 8px;
  }
  h1 { font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #fff; }
  .controls {
    display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap;
  }
  .controls input[type="text"] {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 12px; border-radius: 6px; font-size: 14px; width: 260px;
  }
  .controls button {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
  }
  .controls button:hover { background: #252525; }
  .controls button.active { background: #2563eb; border-color: #2563eb; color: #fff; }
  .controls select {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 10px; border-radius: 6px; font-size: 13px; cursor: pointer;
    text-transform: capitalize;
  }
  .controls select:focus { outline: none; border-color: #555; }
  .count { font-size: 13px; color: #888; margin-left: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th {
    text-align: left; padding: 8px 10px; border-bottom: 1px solid #333;
    font-weight: 500; color: #888; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.5px; position: sticky; top: 0; background: #0a0a0a; z-index: 10;
  }
  th.sortable { cursor: pointer; user-select: none; }
  th.sortable:hover { color: #ccc; }
  th .arrow { font-size: 10px; margin-left: 4px; }
  td { padding: 7px 10px; border-bottom: 1px solid #1a1a1a; vertical-align: top; }
  tr:hover { background: #111; }
  tr.flagged { background: #0d1b2a; }
  tr.flagged:hover { background: #112240; }
  tr.blocked td { opacity: 0.55; }
  tr.blocked.flagged td { opacity: 0.8; }
  .cb { width: 18px; height: 18px; cursor: pointer; accent-color: #2563eb; }
  .cb:disabled { cursor: wait; }
  .base-tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.3px;
  }
  .base-personal { background: #1a3a2a; color: #4ade80; }
  .base-bb { background: #1a2a3a; color: #60a5fa; }
  .base-aitb { background: #2a1a3a; color: #c084fc; }
  .status-tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 11px; white-space: nowrap;
  }
  .status-not-started { background: #1a1a1a; color: #888; }
  .status-in-progress { background: #1a2a1a; color: #4ade80; }
  .status-blocked { background: #2a1a1a; color: #f87171; }
  .status-human-review { background: #2a2a1a; color: #fbbf24; }
  .status-validating { background: #1a1a2a; color: #60a5fa; }
  .dod { max-width: 350px; color: #999; font-size: 12px; line-height: 1.4; white-space: normal; word-wrap: break-word; }
  .task-name { font-weight: 500; color: #e0e0e0; }
  .task-name a { color: inherit; text-decoration: none; }
  .task-name a:hover { text-decoration: underline; }
  .project { color: #666; font-size: 12px; }
  .score { font-variant-numeric: tabular-nums; color: #888; }
  .due { white-space: nowrap; color: #888; }
  .due.overdue { color: #f87171; }
  .loading { text-align: center; padding: 48px; color: #666; }
  .spinner {
    display: inline-block; width: 28px; height: 28px;
    border: 3px solid #333; border-top-color: #2563eb;
    border-radius: 50%; animation: spin 0.7s linear infinite;
    vertical-align: middle; margin-right: 12px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { vertical-align: middle; font-size: 14px; }
  .error { text-align: center; padding: 40px; color: #f87171; }
  tbody.refreshing { opacity: 0.4; transition: opacity 0.2s; }
  tbody.refreshing tr { pointer-events: none; }
  .action-btn {
    background: none; border: 1px solid #333; border-radius: 4px;
    cursor: pointer; padding: 2px 6px; font-size: 14px; line-height: 1;
    transition: all 0.15s;
  }
  .action-btn:hover { background: #252525; }
  .action-btn:disabled { cursor: wait; opacity: 0.4; }
  .btn-done { color: #4ade80; }
  .btn-done:hover { border-color: #4ade80; background: #0a2a0a; }
  .btn-delete { color: #f87171; }
  .btn-delete:hover { border-color: #f87171; background: #2a0a0a; }
  .btn-launch { color: #f59e0b; }
  .btn-launch:hover { border-color: #f59e0b; background: #2a1a0a; }
  .actions { white-space: nowrap; }
  .hitl-link {
    background: #1a1a1a; border: 1px solid #f59e0b; color: #f59e0b;
    padding: 6px 14px; border-radius: 6px; font-size: 13px;
    text-decoration: none; position: relative; display: inline-flex; align-items: center; gap: 6px;
  }
  .hitl-link:hover { background: #2a1a00; }
  .hitl-badge {
    background: #ef4444; color: #fff; border-radius: 9px;
    font-size: 10px; font-weight: 700; padding: 1px 5px; min-width: 16px;
    text-align: center; line-height: 14px;
  }
  tr.completing td { opacity: 0.3; text-decoration: line-through; }
  tr.unassigned td:first-child { border-left: 3px solid #6366f1; }
  tr.unassigned { background: #0d0d14; }
  tr.unassigned:hover { background: #13132a; }
  .toggle-label { display: flex; align-items: center; gap: 5px; font-size: 13px; color: #888; cursor: pointer; white-space: nowrap; }
  .toggle-label input[type="checkbox"] { accent-color: #6366f1; width: 14px; height: 14px; cursor: pointer; }
  /* Deal groups */
  tr.deal-group-header td {
    background: #111622; border-top: 1px solid #2a2a3a; border-bottom: 1px solid #1e1e2e;
    padding: 5px 10px; cursor: pointer; font-size: 12px; font-weight: 600; color: #9999bb;
    user-select: none;
  }
  tr.deal-group-header:hover td { background: #161a2e; }
  .deal-arrow { font-size: 8px; color: #555; margin-right: 5px; display: inline-block; transition: transform 0.15s; }
  tr.deal-group-header.collapsed .deal-arrow { transform: rotate(-90deg); }
  .deal-count { background: #1e1e3a; border-radius: 9px; padding: 1px 7px; font-size: 11px; color: #666; margin-left: 6px; }
  tr.deal-task td { padding-left: 22px; }
  tr.deal-task:last-of-type td { border-bottom: 2px solid #1e1e2e; }
</style>
</head>
<body>
<div class="sticky-header">
  <h1>Work Queue</h1>
  <div class="controls">
    <select id="assignee-select" onchange="onAssigneeChange()" title="View tasks for..."></select>
    <input type="text" id="search" placeholder="Filter tasks..." oninput="scheduleRender()">
    <button id="btn-all" class="active" onclick="setFilter('all')">All</button>
    <button id="btn-flagged" onclick="setFilter('flagged')">For Today</button>
    <button id="btn-personal" onclick="setFilter('personal')">Personal</button>
    <button id="btn-bb" onclick="setFilter('bb')">BB</button>
    <button id="btn-aitb" onclick="setFilter('aitb')">AITB</button>
    <label class="toggle-label" title="Show tasks with no assignee"><input type="checkbox" id="chk-unassigned" checked onchange="render()"> Unassigned</label>
    <button id="btn-refresh" onclick="refreshTasks()" title="Refresh tasks from Airtable">&#8635; Refresh</button>
    <a href="/hitl" class="hitl-link" id="hitl-link" title="HITL Review queue">&#9888; HITL<span class="hitl-badge" id="hitl-badge" style="display:none"></span></a>
    <span class="count" id="count"></span>
  </div>
  <div id="last-refreshed" style="font-size:12px; color:#666; margin-bottom:12px; margin-top:-8px; text-align:right;"></div>
</div>
<table>
  <thead>
    <tr>
      <th style="width:36px"></th>
      <th class="sortable" onclick="toggleSort('score')">Score<span class="arrow" id="arrow-score"></span></th>
      <th>Task</th>
      <th>Base</th>
      <th class="sortable" onclick="toggleSort('status')">Status<span class="arrow" id="arrow-status"></span></th>
      <th>Definition of Done</th>
      <th class="sortable" onclick="toggleSort('due_date')">Due<span class="arrow" id="arrow-due_date"></span></th>
      <th style="width:70px"></th>
    </tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>
<div class="loading" id="loading"><span class="spinner"></span><span class="loading-text">Loading tasks...</span></div>
<div class="error" id="error" style="display:none"></div>

<script>
let tasks = [];
let activeFilter = 'all';
let sortField = 'score';
let sortAsc = false;
let currentAssignee = 'aaron';

const BASE_LABELS = { personal: 'P', bb: 'BB', aitb: 'AITB' };

function statusClass(s) {
  return 'status-' + (s || '').toLowerCase().replace(/\\s+/g, '-');
}

function isOverdue(d) {
  if (!d) return false;
  return new Date(d + 'T23:59:59') < new Date();
}

function setFilter(f) {
  activeFilter = f;
  document.querySelectorAll('.controls button').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + f).classList.add('active');
  render();
}

function onAssigneeChange() {
  currentAssignee = document.getElementById('assignee-select').value;
  try { localStorage.removeItem('dp_tasks'); localStorage.removeItem('dp_refreshed'); } catch(e) {}
  tasks = [];
  render();
  refreshTasks();
  fetchHitlCount();
}

function toggleSort(field) {
  if (sortField === field) { sortAsc = !sortAsc; }
  else { sortField = field; sortAsc = false; }
  render();
}

function filtered() {
  let q = document.getElementById('search').value.toLowerCase();
  let list = tasks;
  if (!document.getElementById('chk-unassigned').checked) list = list.filter(t => !t._unassigned);
  if (activeFilter === 'flagged') list = list.filter(t => t.for_today);
  else if (['personal','bb','aitb'].includes(activeFilter)) list = list.filter(t => t.base === activeFilter);
  if (q) list = list.filter(t =>
    (t.task||'').toLowerCase().includes(q) ||
    (t.description||'').toLowerCase().includes(q) ||
    (t.project_name||'').toLowerCase().includes(q)
  );
  list.sort((a, b) => {
    if (a.for_today !== b.for_today) return a.for_today ? -1 : 1;
    let av = a[sortField] ?? '', bv = b[sortField] ?? '';
    if (sortField === 'score') { av = av || 0; bv = bv || 0; }
    if (av < bv) return sortAsc ? -1 : 1;
    if (av > bv) return sortAsc ? 1 : -1;
    return 0;
  });
  return list;
}

function renderRow(t, inGroup) {
  const blocked = (t.status||'').toLowerCase() === 'blocked';
  const cls = [t.for_today ? 'flagged' : '', blocked ? 'blocked' : '', t._unassigned ? 'unassigned' : '', inGroup ? 'deal-task' : ''].filter(Boolean).join(' ');
  const od = isOverdue(t.due_date) && !t.for_today ? ' overdue' : '';
  const dodHtml = t.description
    ? `<div class="dod">${esc(cleanText(t.description))}</div>`
    : '';
  return `<tr class="${cls}">
    <td><input type="checkbox" class="cb" data-id="${t.id}" data-base="${t.base}"
      ${t.for_today ? 'checked' : ''} onchange="toggle(this)"></td>
    <td class="score">${t.score || ''}</td>
    <td class="task-name"><a href="${t.airtable_url}" target="_blank">${formatTitle(t.task)}</a>
      ${t.project_name ? '<div class="project">' + esc(cleanText(t.project_name)) + '</div>' : ''}</td>
    <td><span class="base-tag base-${t.base}">${BASE_LABELS[t.base]}</span></td>
    <td><span class="status-tag ${statusClass(t.status)}">${esc(t.status)}</span></td>
    <td>${dodHtml}</td>
    <td class="due${od}">${t.due_date || ''}</td>
    <td class="actions">
      <button class="action-btn btn-done" title="Mark complete" onclick="markComplete(this,'${t.id}','${t.base}')">&#10003;</button>
      <button class="action-btn btn-delete" title="Delete" onclick="deleteTask(this,'${t.id}','${t.base}')">&#10005;</button>
      <button class="action-btn btn-launch" title="Launch in Pablo" data-ref="${t.base}:${t.id}" onclick="launchTask(this)">&#128640;</button>
    </td>
  </tr>`;
}

function render() {
  const list = filtered();
  const tbody = document.getElementById('tbody');
  document.getElementById('count').textContent =
    list.length + ' tasks (' + tasks.filter(t => t.for_today).length + ' flagged)';

  ['score','status','due_date'].forEach(f => {
    const el = document.getElementById('arrow-' + f);
    el.textContent = sortField === f ? (sortAsc ? ' \\u25B2' : ' \\u25BC') : '';
  });

  // Separate deal-grouped tasks from ungrouped
  const dealGroups = new Map();
  const ungrouped = [];
  for (const t of list) {
    const dealId = t.deal_ids && t.deal_ids[0];
    if (dealId) {
      if (!dealGroups.has(dealId)) {
        dealGroups.set(dealId, { name: t.campaign_name || dealId, url: t.campaign_url || '', tasks: [] });
      }
      dealGroups.get(dealId).tasks.push(t);
    } else {
      ungrouped.push(t);
    }
  }

  // Sort tasks within each deal group by touch sequence then score
  for (const g of dealGroups.values()) {
    g.tasks.sort((a, b) => touchSeq(a) - touchSeq(b) || (b.score || 0) - (a.score || 0));
  }

  let html = '';

  // Render deal groups first
  for (const [dealId, g] of dealGroups) {
    const collapsed = _collapsedDeals.has(dealId);
    const label = g.url
      ? `<a href="${esc(g.url)}" target="_blank" onclick="event.stopPropagation()" style="color:inherit;text-decoration:none;">${esc(g.name)}</a>`
      : esc(g.name);
    html += `<tr class="deal-group-header${collapsed ? ' collapsed' : ''}" onclick="toggleDealGroup('${dealId}')">
      <td colspan="8"><span class="deal-arrow">▼</span>🎯 ${label}<span class="deal-count">${g.tasks.length}</span></td>
    </tr>`;
    if (!collapsed) html += g.tasks.map(t => renderRow(t, true)).join('');
  }

  // Render ungrouped tasks
  html += ungrouped.map(t => renderRow(t, false)).join('');

  tbody.innerHTML = html;
}

function launchTask(btn) {
  const ref = btn.getAttribute('data-ref'); // "base:recId"
  window.open('http://localhost:19280/task/' + encodeURIComponent(ref), '_blank');
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function cleanText(s) {
  if (!s) return s;
  return s.replace(/\\^\\^([\\s\\S]*?)\\^\\^/g, '$1').replace(/==([\\s\\S]*?)==/g, '$1');
}

const PREFIX_ICONS = {
  'human_comm:': '💬',
  'research:': '🔍',
  'send_email:': '✉️',
  'review:': '👁️',
};
const TOUCH_SEQ = { 'research:': 1, 'send_email:': 2, 'human_comm:': 3, 'review:': 4 };

function formatTitle(s) {
  if (!s) return '';
  const icons = [];
  let rest = s;
  let matched = true;
  while (matched) {
    matched = false;
    const lower = rest.toLowerCase();
    for (const [p, icon] of Object.entries(PREFIX_ICONS)) {
      if (lower.startsWith(p)) {
        icons.push(icon);
        rest = rest.slice(p.length).trimStart();
        matched = true;
        break;
      }
    }
  }
  const prefix = icons.length ? icons.join('') + ' ' : '';
  return prefix + esc(cleanText(rest));
}

function touchSeq(t) {
  const lower = (t.task || '').toLowerCase();
  for (const [p, seq] of Object.entries(TOUCH_SEQ)) if (lower.startsWith(p)) return seq;
  return 99;
}

const _collapsedDeals = new Set();

function toggleDealGroup(dealId) {
  if (_collapsedDeals.has(dealId)) _collapsedDeals.delete(dealId);
  else _collapsedDeals.add(dealId);
  render();
}

let _searchTimer = null;
function scheduleRender() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(render, 120);
}

async function toggle(el) {
  const id = el.dataset.id;
  const base = el.dataset.base;
  const value = el.checked;
  el.disabled = true;

  try {
    const res = await fetch('/api/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, base, value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Unknown error');
    // Update local state
    const task = tasks.find(t => t.id === id);
    if (task) task.for_today = value;
    render();
  } catch (err) {
    el.checked = !value; // revert
    alert('Failed to update: ' + err.message);
  } finally {
    el.disabled = false;
  }
}

async function markComplete(btn, id, base) {
  if (!confirm('Mark this task complete?')) return;
  const row = btn.closest('tr');
  row.classList.add('completing');
  btn.disabled = true;
  try {
    const res = await fetch('/api/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, base })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Unknown error');
    tasks = tasks.filter(t => t.id !== id);
    localStorage.setItem('dp_tasks', JSON.stringify(tasks));
    render();
  } catch (err) {
    row.classList.remove('completing');
    btn.disabled = false;
    alert('Failed to complete: ' + err.message);
  }
}

async function deleteTask(btn, id, base) {
  if (!confirm('Delete this task permanently?')) return;
  const row = btn.closest('tr');
  row.classList.add('completing');
  btn.disabled = true;
  try {
    const res = await fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, base })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Unknown error');
    tasks = tasks.filter(t => t.id !== id);
    localStorage.setItem('dp_tasks', JSON.stringify(tasks));
    render();
  } catch (err) {
    row.classList.remove('completing');
    btn.disabled = false;
    alert('Failed to delete: ' + err.message);
  }
}

async function fetchHitlCount() {
  try {
    const res = await fetch('/api/hitl-count?assignee=' + encodeURIComponent(currentAssignee));
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById('hitl-badge');
    if (data.count > 0) {
      badge.textContent = data.count;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  } catch(e) {}
}

let lastRefreshed = null;

function updateRefreshedLabel() {
  const el = document.getElementById('last-refreshed');
  if (lastRefreshed) {
    el.textContent = 'Last refreshed: ' + lastRefreshed.toLocaleString();
  }
}

function loadFromCache() {
  try {
    const cached = localStorage.getItem('dp_tasks');
    const ts = localStorage.getItem('dp_refreshed');
    if (cached && ts) {
      tasks = JSON.parse(cached);
      lastRefreshed = new Date(ts);
      document.getElementById('loading').style.display = 'none';
      updateRefreshedLabel();
      render();
      return true;
    }
  } catch (e) {}
  return false;
}

function saveToCache() {
  try {
    localStorage.setItem('dp_tasks', JSON.stringify(tasks));
    localStorage.setItem('dp_refreshed', lastRefreshed.toISOString());
  } catch (e) {}
}

async function fetchTasks() {
  const res = await fetch('/api/tasks?assignee=' + encodeURIComponent(currentAssignee));
  if (!res.ok) throw new Error('HTTP ' + res.status);
  tasks = await res.json();
  lastRefreshed = new Date();
  saveToCache();
  updateRefreshedLabel();
  render();
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) return;
    const cfg = await res.json();
    currentAssignee = cfg.current_user || 'aaron';
    const sel = document.getElementById('assignee-select');
    sel.innerHTML = (cfg.people || [currentAssignee]).map(p =>
      `<option value="${p}" ${p === currentAssignee ? 'selected' : ''}>${p.charAt(0).toUpperCase() + p.slice(1)}</option>`
    ).join('');
  } catch(e) {}
}

async function load() {
  await loadConfig();
  const hadCache = loadFromCache();
  fetchHitlCount();
  try {
    await fetchTasks();
    document.getElementById('loading').style.display = 'none';
  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    if (!hadCache) {
      document.getElementById('error').style.display = 'block';
      document.getElementById('error').textContent = 'Failed to load: ' + err.message;
    }
  }
}

async function refreshTasks() {
  const btn = document.getElementById('btn-refresh');
  const tbody = document.getElementById('tbody');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:13px;height:13px;border-width:2px;margin-right:6px;border-top-color:#60a5fa"></span>Refreshing...';
  tbody.classList.add('refreshing');
  try {
    await fetchTasks();
    fetchHitlCount();
  } catch (err) {
    alert('Refresh failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '\\u21BB Refresh';
    tbody.classList.remove('refreshing');
  }
}

load();
</script>
</body>
</html>
"""

HITL_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HITL Review</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a; color: #e0e0e0;
    padding: 24px; max-width: 900px; margin: 0 auto;
  }
  .header {
    display: flex; align-items: center; gap: 16px; margin-bottom: 24px;
  }
  h1 { font-size: 20px; font-weight: 600; color: #fff; flex: 1; }
  .back-link {
    color: #888; text-decoration: none; font-size: 13px;
  }
  .back-link:hover { color: #e0e0e0; }
  .refresh-btn {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
  }
  .refresh-btn:hover { background: #252525; }
  .refresh-btn:disabled { opacity: 0.5; cursor: wait; }
  .filter-btn {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
  }
  .filter-btn:hover { background: #252525; }
  .filter-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }
  .assignee-select {
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    padding: 6px 10px; border-radius: 6px; font-size: 13px; cursor: pointer;
    text-transform: capitalize;
  }
  .assignee-select:focus { outline: none; border-color: #555; }
  .count { font-size: 13px; color: #888; }
  .card {
    background: #111; border: 1px solid #222; border-radius: 8px;
    margin-bottom: 16px; overflow: hidden;
  }
  .card-header {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px; border-bottom: 1px solid #1e1e1e;
  }
  .card.plan { border-left: 4px solid #3b5a7a; }
  .card.output { border-left: 4px solid #f59e0b; background: #131108; border-color: #2e2400; }
  .card.output .card-header { border-bottom-color: #2a2000; }
  .type-badge {
    font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    padding: 2px 7px; border-radius: 3px; text-transform: uppercase;
  }
  .type-plan { background: #141e2a; color: #4a7a9a; }
  .type-output { background: #3a2200; color: #f59e0b; }
  .section-divider {
    display: flex; align-items: center; gap: 12px;
    margin: 8px 0 20px;
  }
  .section-divider-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.8px;
    text-transform: uppercase; white-space: nowrap;
  }
  .section-divider-label.output { color: #f59e0b; }
  .section-divider-label.plan { color: #4a7a9a; }
  .section-divider-line { flex: 1; height: 1px; }
  .section-divider-line.output { background: #2e2400; }
  .section-divider-line.plan { background: #1a2530; }
  .task-link { font-weight: 600; color: #e0e0e0; text-decoration: none; font-size: 14px; flex: 1; }
  .task-link:hover { text-decoration: underline; }
  .campaign-tag {
    display: inline-flex; align-items: center; gap: 4px;
    background: #1a2a1a; border: 1px solid #2d5a2d; color: #6aad6a;
    border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;
    text-decoration: none; white-space: nowrap; flex-shrink: 0;
  }
  .campaign-tag:hover { background: #1f3a1f; border-color: #4ade80; color: #4ade80; }
  .base-tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 11px; font-weight: 600;
  }
  .base-personal { background: #1a3a2a; color: #4ade80; }
  .base-bb { background: #1a2a3a; color: #60a5fa; }
  .base-aitb { background: #2a1a3a; color: #c084fc; }
  .score { font-size: 12px; color: #666; }
  .project { font-size: 12px; color: #666; margin-left: auto; }
  .card-body { padding: 14px 16px; }
  .section-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    text-transform: uppercase; color: #555; margin-bottom: 4px;
  }
  .section-content {
    font-size: 13px; line-height: 1.6; color: #ccc;
    background: #0d0d0d; border-radius: 4px; padding: 8px 12px;
    word-wrap: break-word; margin-bottom: 8px; overflow-x: auto;
  }
  .section-content a { color: #60a5fa; text-decoration: underline; word-break: break-all; }
  .section-content a:hover { color: #93c5fd; }
  .section-content p { margin: 0 0 8px; }
  .section-content p:last-child { margin-bottom: 0; }
  .section-content h1, .section-content h2, .section-content h3,
  .section-content h4, .section-content h5, .section-content h6 {
    color: #e0e0e0; font-weight: 600; margin: 12px 0 6px; line-height: 1.3;
  }
  .section-content h1 { font-size: 16px; }
  .section-content h2 { font-size: 15px; }
  .section-content h3 { font-size: 14px; }
  .section-content ul, .section-content ol { padding-left: 20px; margin: 0 0 8px; }
  .section-content li { margin-bottom: 3px; }
  .section-content code {
    background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 3px;
    padding: 1px 5px; font-size: 12px; font-family: "SF Mono", Menlo, monospace; color: #e0e0e0;
  }
  .section-content pre {
    background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px;
    padding: 10px 12px; overflow-x: auto; margin: 0 0 8px;
  }
  .section-content pre code {
    background: none; border: none; padding: 0; font-size: 12px;
  }
  .section-content blockquote {
    border-left: 3px solid #333; padding-left: 12px; margin: 0 0 8px; color: #888;
  }
  .section-content hr { border: none; border-top: 1px solid #2a2a2a; margin: 10px 0; }
  .section-content strong { color: #e0e0e0; font-weight: 600; }
  .section-content em { font-style: italic; }
  /* Collapsible header sections */
  .section-content details.md-section { margin: 2px 0; }
  .section-content details.md-section > summary {
    cursor: pointer; list-style: none; display: flex; align-items: center;
    gap: 8px; padding: 4px 0; font-weight: 600; user-select: none;
  }
  .section-content details.md-section > summary::-webkit-details-marker { display: none; }
  .section-content details.md-section > summary::before {
    content: '▶'; font-size: 8px; color: #555; flex-shrink: 0;
    transition: transform 0.15s; display: inline-block;
  }
  .section-content details.md-section[open] > summary::before { transform: rotate(90deg); }
  .section-content details.md-h1 > summary { font-size: 16px; color: #e0e0e0; margin: 10px 0 4px; }
  .section-content details.md-h2 > summary { font-size: 15px; color: #ddd; margin: 8px 0 3px; }
  .section-content details.md-h3 > summary { font-size: 14px; color: #ccc; margin: 6px 0 2px; }
  .section-content details.md-h4 > summary { font-size: 13px; color: #bbb; }
  .section-content .md-section-body { padding-left: 12px; margin-top: 2px; }
  /* Interactive controls */
  .section-content input.md-cb,
  .section-content input.md-radio {
    accent-color: #6366f1; cursor: pointer; vertical-align: middle; margin-right: 4px;
  }
  .section-content label { cursor: pointer; }
  .response-area {
    width: 100%; min-height: 72px; max-height: 200px;
    background: #1a1a1a; border: 1px solid #333; color: #e0e0e0;
    border-radius: 4px; padding: 8px 10px; font-size: 13px;
    font-family: inherit; resize: vertical; display: block; margin-bottom: 10px;
  }
  .response-area:focus { outline: none; border-color: #555; }
  .response-area.error { border-color: #f87171; }
  .response-label { font-size: 12px; color: #666; margin-bottom: 6px; }
  .card-header-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
  .card-header-row { display: flex; align-items: center; gap: 8px; }
  .card-header-meta .score { padding-right: 7px; }
  .card-collapse-btn {
    background: none; border: none; color: #555; cursor: pointer;
    font-size: 10px; padding: 0 4px; flex-shrink: 0; transition: transform 0.15s;
  }
  .card.collapsed .card-collapse-btn { transform: rotate(-90deg); }
  .card.collapsed .card-body { display: none; }
  .deal-group-card { background: #111; border: 1px solid #222; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
  .deal-group-header { display: flex; align-items: center; gap: 10px; padding: 10px 16px; background: #0e0e0e; border-bottom: 1px solid #1e1e1e; }
  .deal-group-title { display: flex; align-items: center; gap: 8px; flex: 1; }
  .deal-touch-count { background: #1e1e3a; color: #888; border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600; }
  .touch-card { transition: opacity 0.4s; }
  .touch-header { display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; user-select: none; background: #0e0e0e; border-top: 1px solid #1e1e1e; }
  .touch-card:first-child .touch-header { border-top: none; }
  .touch-header:hover { background: #131313; }
  .touch-body { padding: 14px 16px; }
  .touch-card.collapsed .touch-body { display: none; }
  .touch-card.collapsed .card-collapse-btn { transform: rotate(-90deg); }
  .touch-card.done { opacity: 0.3; }
  .touch-score { font-size: 12px; color: #666; flex-shrink: 0; padding-left: 8px; }
  .card-actions { display: flex; align-items: center; gap: 10px; }
  .card-meta { display: flex; font-size: 11px; color: #555; gap: 14px; margin-left: auto; }
  .btn {
    padding: 7px 20px; border-radius: 6px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: 1px solid transparent; transition: all 0.15s;
  }
  .btn:disabled { opacity: 0.4; cursor: wait; }
  .btn-approve {
    background: #0a2a0a; border-color: #4ade80; color: #4ade80;
  }
  .btn-approve:hover:not(:disabled) { background: #0d3a0d; }
  .btn-decline {
    background: #2a0a0a; border-color: #f87171; color: #f87171;
  }
  .btn-decline:hover:not(:disabled) { background: #3a0d0d; }
  .empty { text-align: center; padding: 64px; color: #555; font-size: 15px; }
  .loading { text-align: center; padding: 64px; color: #666; }
  .loading-status { font-size: 12px; color: #444; margin-top: 10px; }
  .spinner {
    display: inline-block; width: 24px; height: 24px;
    border: 3px solid #333; border-top-color: #2563eb;
    border-radius: 50%; animation: spin 0.7s linear infinite;
    vertical-align: middle; margin-right: 10px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .error-msg { text-align: center; padding: 40px; color: #f87171; }
  .card.done { opacity: 0.3; pointer-events: none; }
  .last-refreshed { font-size: 12px; color: #555; }
</style>
</head>
<body>
<div class="header">
  <a href="/" class="back-link">&#8592; Work Queue</a>
  <h1>HITL Review</h1>
  <select id="assignee-select" class="assignee-select" onchange="onAssigneeChange()"></select>
  <button class="filter-btn active" id="btn-filter-all" onclick="setHitlFilter('all')">All</button>
  <button class="filter-btn" id="btn-filter-gtm" onclick="setHitlFilter('gtm')">GTM</button>
  <button class="filter-btn" id="btn-filter-no-gtm" onclick="setHitlFilter('no-gtm')">No GTM</button>
  <span class="count" id="count"></span>
  <span class="last-refreshed" id="last-refreshed"></span>
  <button class="refresh-btn" id="btn-refresh" onclick="refreshHitl()">&#8635; Refresh</button>
</div>
<div id="loading" class="loading"><span class="spinner"></span>Loading...<div id="loading-status" class="loading-status"></div></div>
<div id="error-msg" class="error-msg" style="display:none"></div>
<div id="cards"></div>
<div id="empty" class="empty" style="display:none">No items need review right now.</div>

<script>
let items = [];
let currentAssignee = 'aaron';
let hitlFilter = 'all';
const _collapsedCards = new Set();   // for solo cards
const _expandedTouch = new Map();    // dealId -> currently expanded touch id

function toggleCard(id) {
  const card = document.getElementById('card-' + id);
  if (!card) return;
  if (_collapsedCards.has(id)) {
    _collapsedCards.delete(id);
    card.classList.remove('collapsed');
  } else {
    _collapsedCards.add(id);
    card.classList.add('collapsed');
  }
}

function touchNumber(t) {
  const m = (t.task || '').match(/\\btouch\\s+(\\d+)\\b/i);
  return m ? parseInt(m[1]) : 999;
}

function sortTouches(touches) {
  return [...touches].sort((a, b) => touchNumber(a) - touchNumber(b) || (b.score || 0) - (a.score || 0));
}

function groupedTouches(dealId) {
  return sortTouches(items.filter(t => (t.deal_ids || [])[0] === dealId));
}

function toggleTouch(id, dealId) {
  const card = document.getElementById('card-' + id);
  if (!card) return;
  if (card.classList.contains('collapsed')) {
    const prevId = _expandedTouch.get(dealId);
    if (prevId && prevId !== id) {
      const prev = document.getElementById('card-' + prevId);
      if (prev) prev.classList.add('collapsed');
    }
    _expandedTouch.set(dealId, id);
    card.classList.remove('collapsed');
    const ta = document.getElementById('resp-' + id);
    if (ta) ta.focus();
  } else {
    _expandedTouch.set(dealId, null);
    card.classList.add('collapsed');
  }
}

const BASE_LABELS = { personal: 'P', bb: 'BB', aitb: 'AITB' };

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

function linkify(s) {
  if (!s) return '';
  const urlRegex = /(https?:\\/\\/[^\\s<>"]+)/g;
  const parts = (s + '').split(urlRegex);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      const safeUrl = esc(part);
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`;
    }
    return esc(part);
  }).join('');
}

function cleanText(s) {
  if (!s) return '';
  return s.replace(/\\^\\^([\\s\\S]*?)\\^\\^/g, '$1').replace(/==([\\s\\S]*?)==/g, '$1');
}

const PREFIX_ICONS = {
  'human_comm:': '💬',
  'research:': '🔍',
  'send_email:': '✉️',
  'review:': '👁️',
};

function formatTitle(s) {
  if (!s) return '';
  const icons = [];
  let rest = s;
  let matched = true;
  while (matched) {
    matched = false;
    const lower = rest.toLowerCase();
    for (const [p, icon] of Object.entries(PREFIX_ICONS)) {
      if (lower.startsWith(p)) {
        icons.push(icon);
        rest = rest.slice(p.length).trimStart();
        matched = true;
        break;
      }
    }
  }
  const prefix = icons.length ? icons.join('') + ' ' : '';
  return prefix + esc(cleanText(rest));
}

function preprocessInteractive(text, taskId) {
  const lines = text.split('\\n');
  let cbIdx = 0, rIdx = 0, rgIdx = 0, inRadio = false, radioGroup = '';
  return lines.map(line => {
    const rm = line.match(/^(\\s*(?:[-*+]\\s+)?)\\(([xX ])\\)\\s+(.*)$/);
    if (rm) {
      if (!inRadio) { inRadio = true; radioGroup = taskId + '-rg' + rgIdx++; }
      const id = taskId + '-r' + rIdx++;
      const chk = rm[2] !== ' ' ? ' checked' : '';
      return rm[1] + '<input type="radio" class="md-radio" id="' + id + '" name="' + radioGroup + '"' + chk + '> <label for="' + id + '">' + rm[3] + '</label>';
    }
    inRadio = false;
    const cm = line.match(/^(\\s*(?:[-*+]\\s+)?)\\[([xX ])\\]\\s+(.*)$/);
    if (cm) {
      const id = taskId + '-cb' + cbIdx++;
      const chk = cm[2] !== ' ' ? ' checked' : '';
      return cm[1] + '<input type="checkbox" class="md-cb" id="' + id + '" name="' + id + '"' + chk + '> <label for="' + id + '">' + cm[3] + '</label>';
    }
    return line;
  }).join('\\n');
}

function processNodes(nodes, insideH1) {
  let html = '';
  let i = 0;
  while (i < nodes.length) {
    const nd = nodes[i];
    if (nd.nodeType === 1 && /^H[1-4]$/.test(nd.tagName)) {
      const lvl = parseInt(nd.tagName[1]);
      const open = lvl === 1 || insideH1;
      const children = [];
      i++;
      while (i < nodes.length) {
        const nx = nodes[i];
        if (nx.nodeType === 1 && /^H[1-4]$/.test(nx.tagName) && parseInt(nx.tagName[1]) <= lvl) break;
        children.push(nx);
        i++;
      }
      const body = processNodes(children, lvl === 1 || insideH1);
      html += '<details' + (open ? ' open' : '') + ' class="md-section md-h' + lvl + '">' +
              '<summary>' + nd.innerHTML + '</summary>' +
              '<div class="md-section-body">' + body + '</div></details>';
    } else {
      html += nd.nodeType === 1 ? nd.outerHTML : esc(nd.textContent);
      i++;
    }
  }
  return html;
}

function wrapCollapsibleHeaders(html) {
  const d = document.createElement('div');
  d.innerHTML = html;
  return processNodes(Array.from(d.childNodes), false);
}

function collectInteractiveState(cardId) {
  const card = document.getElementById('card-' + cardId);
  if (!card) return '';
  const lines = [];
  card.querySelectorAll('input.md-cb').forEach(cb => {
    const lbl = card.querySelector(`label[for="${cb.id}"]`);
    lines.push('[' + (cb.checked ? 'x' : ' ') + '] ' + (lbl ? lbl.textContent.trim() : cb.name || cb.id));
  });
  const seen = new Set();
  card.querySelectorAll('input.md-radio').forEach(r => {
    if (!seen.has(r.name)) {
      seen.add(r.name);
      const sel = card.querySelector(`input.md-radio[name="${r.name}"]:checked`);
      if (sel) {
        const lbl = card.querySelector(`label[for="${sel.id}"]`);
        lines.push('(x) ' + (lbl ? lbl.textContent.trim() : sel.name || sel.id));
      }
    }
  });
  return lines.join('\\n');
}

const _mdCache = new Map();

function renderMarkdown(s, taskId) {
  if (!s) return '';
  const cacheKey = taskId ? taskId + '|' + s.length : null;
  if (cacheKey && _mdCache.has(cacheKey)) return _mdCache.get(cacheKey);
  const cleaned = cleanText(s);
  const processed = taskId ? preprocessInteractive(cleaned, taskId) : cleaned;
  let result;
  if (typeof marked !== 'undefined') {
    result = wrapCollapsibleHeaders(marked.parse(processed, { breaks: true }));
  } else {
    result = linkify(cleaned);
  }
  if (cacheKey) _mdCache.set(cacheKey, result);
  return result;
}

function setHitlFilter(f) {
  hitlFilter = f;
  document.getElementById('btn-filter-all').classList.toggle('active', f === 'all');
  document.getElementById('btn-filter-gtm').classList.toggle('active', f === 'gtm');
  document.getElementById('btn-filter-no-gtm').classList.toggle('active', f === 'no-gtm');
  render();
}

function filteredItems() {
  if (hitlFilter === 'gtm') return items.filter(t => t.is_gtm);
  if (hitlFilter === 'no-gtm') return items.filter(t => !t.is_gtm);
  return items;
}

function byScore(a, b) { return (b.score || 0) - (a.score || 0); }
function isLinkedIn(t) { return /linkedin/i.test(t.task || ''); }
function dealKey(t) { return (t.deal_ids || [])[0] || ''; }
function sortForDisplay(items) {
  const dealMaxScore = new Map();
  for (const t of items) {
    const k = dealKey(t);
    if (!k) continue;
    const s = t.score || 0;
    if (!dealMaxScore.has(k) || s > dealMaxScore.get(k)) dealMaxScore.set(k, s);
  }
  return items.slice().sort((a, b) => {
    const la = isLinkedIn(a), lb = isLinkedIn(b);
    if (la !== lb) return la ? -1 : 1;
    const ka = dealKey(a), kb = dealKey(b);
    const sa = ka ? dealMaxScore.get(ka) : (a.score || 0);
    const sb = kb ? dealMaxScore.get(kb) : (b.score || 0);
    if (sa !== sb) return sb - sa;
    if (ka !== kb) return ka < kb ? -1 : 1;
    return (b.score || 0) - (a.score || 0);
  });
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderTouchCard(t, dealId, isExpanded) {
  const isPlan = t.hitl_type === 'plan';
  const typeCls = isPlan ? 'type-plan' : 'type-output';
  const typeLabel = isPlan ? 'Plan Review' : 'Output Review';
  const approveLabel = isPlan ? '&#10003; Approve Plan' : '&#10003; Approve &amp; Complete';
  const responseHint = isPlan ? 'Optional note for Pablo...' : 'Feedback / revision request (required to decline)...';
  const briefSection = t.hitl_brief
    ? `<div class="section-label">HITL Brief</div><div class="section-content">${renderMarkdown(t.hitl_brief, t.id)}</div>`
    : '';
  const outputSection = !isPlan && t.task_output
    ? `<div class="section-label">Task Output</div><div class="section-content">${renderMarkdown(t.task_output, t.id + '-out')}</div>`
    : '';
  const metaHtml = (t.created_time || t.updated_time)
    ? `<div class="card-meta">${t.created_time ? `<span>Created ${fmtDate(t.created_time)}</span>` : ''}${t.updated_time ? `<span>Updated ${fmtDate(t.updated_time)}</span>` : ''}</div>`
    : '';
  return `<div class="touch-card${isExpanded ? '' : ' collapsed'}" id="card-${t.id}">
    <div class="touch-header" onclick="toggleTouch('${t.id}','${dealId}')">
      <button class="card-collapse-btn" onclick="event.stopPropagation();toggleTouch('${t.id}','${dealId}')">▼</button>
      <a class="task-link" href="${t.airtable_url}" target="_blank" onclick="event.stopPropagation()">${formatTitle(t.task)}</a>
      ${t.score ? `<span class="touch-score">${t.score}</span>` : ''}
    </div>
    <div class="touch-body">
      ${briefSection}
      ${outputSection}
      <div class="response-label">Response</div>
      <textarea class="response-area" id="resp-${t.id}" placeholder="${responseHint}">${esc(t.hitl_response || '')}</textarea>
      <div class="card-actions">
        <button class="btn btn-approve" onclick="respondTouch('${t.id}','${t.base}','${t.hitl_type}','${dealId}',true)">${approveLabel}</button>
        <button class="btn btn-decline" onclick="respondTouch('${t.id}','${t.base}','${t.hitl_type}','${dealId}',false)">&#10005; Decline</button>
        ${metaHtml}
      </div>
    </div>
  </div>`;
}

function renderDealGroup(dealId, touches) {
  const sorted = sortTouches(touches);
  if (!_expandedTouch.has(dealId)) _expandedTouch.set(dealId, sorted[0].id);
  const expandedId = _expandedTouch.get(dealId);
  const rep = sorted[0];
  const typeLabel = rep.hitl_type === 'output' ? 'Output Review' : 'Plan Review';
  const typeCls = rep.hitl_type === 'output' ? 'type-output' : 'type-plan';
  return `<div class="deal-group-card" id="deal-group-${dealId}">
    <div class="deal-group-header">
      <span class="type-badge ${typeCls}">${typeLabel}</span>
      <div class="deal-group-title">
        <span class="deal-touch-count">${sorted.length} touches</span>
      </div>
      <div class="card-header-meta">
        <div class="card-header-row">
          ${rep.campaign_name && rep.campaign_url ? `<a class="campaign-tag" href="${esc(rep.campaign_url)}" target="_blank" onclick="event.stopPropagation()">&#127937; ${esc(rep.campaign_name)}</a>` : ''}
          <span class="base-tag base-${rep.base}">${BASE_LABELS[rep.base] || rep.base}</span>
        </div>
        <div class="card-header-row">
          ${rep.project_name ? `<span class="project" style="margin-left:0">${esc(rep.project_name)}</span>` : ''}
        </div>
      </div>
    </div>
    <div class="deal-touches">
      ${sorted.map(t => renderTouchCard(t, dealId, t.id === expandedId)).join('')}
    </div>
  </div>`;
}

function renderCard(t) {
    const isPlan = t.hitl_type === 'plan';
    const typeLabel = isPlan ? 'Plan Review' : 'Output Review';
    const typeCls = isPlan ? 'type-plan' : 'type-output';
    const cardCls = isPlan ? 'plan' : 'output';

    const briefSection = t.hitl_brief
      ? `<div class="section-label">HITL Brief</div>
         <div class="section-content">${renderMarkdown(t.hitl_brief, t.id)}</div>`
      : '';

    const outputSection = !isPlan && t.task_output
      ? `<div class="section-label">Task Output</div>
         <div class="section-content">${renderMarkdown(t.task_output, t.id + '-out')}</div>`
      : '';

    const approveLabel = isPlan ? '&#10003; Approve Plan' : '&#10003; Approve &amp; Complete';
    const responseHint = isPlan
      ? 'Optional note for Pablo...'
      : 'Feedback / revision request (required to decline)...';

    const metaHtml = (t.created_time || t.updated_time)
      ? `<div class="card-meta">${t.created_time ? `<span>Created ${fmtDate(t.created_time)}</span>` : ''}${t.updated_time ? `<span>Updated ${fmtDate(t.updated_time)}</span>` : ''}</div>`
      : '';

    const isCollapsed = _collapsedCards.has(t.id);
    return `<div class="card ${cardCls}${isCollapsed ? ' collapsed' : ''}" id="card-${t.id}">
      <div class="card-header" style="cursor:pointer" onclick="toggleCard('${t.id}')">
        <button class="card-collapse-btn" onclick="event.stopPropagation();toggleCard('${t.id}')">▼</button>
        <span class="type-badge ${typeCls}">${typeLabel}</span>
        <a class="task-link" href="${t.airtable_url}" target="_blank" onclick="event.stopPropagation()">${formatTitle(t.task)}</a>
        <div class="card-header-meta">
          <div class="card-header-row">
            ${t.campaign_name && t.campaign_url ? `<a class="campaign-tag" href="${esc(t.campaign_url)}" target="_blank" title="Open campaign in Airtable" onclick="event.stopPropagation()">&#127937; ${esc(t.campaign_name)}</a>` : ''}
            <span class="base-tag base-${t.base}">${BASE_LABELS[t.base] || t.base}</span>
          </div>
          <div class="card-header-row">
            ${t.project_name ? `<span class="project" style="margin-left:0">${esc(t.project_name)}</span>` : ''}
            ${t.score ? `<span class="score">${t.score}</span>` : ''}
          </div>
        </div>
      </div>
      <div class="card-body">
        ${briefSection}
        ${outputSection}
        <div class="response-label">Response</div>
        <textarea class="response-area" id="resp-${t.id}" placeholder="${responseHint}">${esc(t.hitl_response || '')}</textarea>
        <div class="card-actions">
          <button class="btn btn-approve" onclick="respond('${t.id}','${t.base}','${t.hitl_type}',true)">${approveLabel}</button>
          <button class="btn btn-decline" onclick="respond('${t.id}','${t.base}','${t.hitl_type}',false)">&#10005; Decline</button>
          ${metaHtml}
        </div>
      </div>
    </div>`;
}

function divider(type, label) {
  return `<div class="section-divider">
    <span class="section-divider-label ${type}">${label}</span>
    <div class="section-divider-line ${type}"></div>
  </div>`;
}

function renderSection(sectionItems) {
  const dealGroups = new Map();
  const ungrouped = [];
  for (const t of sectionItems) {
    const dealId = (t.deal_ids || [])[0];
    if (dealId) {
      if (!dealGroups.has(dealId)) dealGroups.set(dealId, []);
      dealGroups.get(dealId).push(t);
    } else {
      ungrouped.push(t);
    }
  }
  let html = '';
  for (const [dealId, touches] of dealGroups) {
    html += touches.length >= 2 ? renderDealGroup(dealId, touches) : renderCard(touches[0]);
  }
  html += ungrouped.map(renderCard).join('');
  return html;
}

function render() {
  const visible = filteredItems();
  const container = document.getElementById('cards');
  document.getElementById('count').textContent = visible.length + ' item' + (visible.length !== 1 ? 's' : '');
  document.getElementById('empty').style.display = visible.length === 0 ? 'block' : 'none';

  const outputItems = sortForDisplay(visible.filter(t => t.hitl_type === 'output'));
  const planItems   = sortForDisplay(visible.filter(t => t.hitl_type !== 'output'));

  let html = '';
  if (outputItems.length) {
    html += divider('output', `Completed Work — ${outputItems.length} item${outputItems.length !== 1 ? 's' : ''}`);
    html += renderSection(outputItems);
  }
  if (planItems.length) {
    html += divider('plan', `Plan Approvals — ${planItems.length} item${planItems.length !== 1 ? 's' : ''}`);
    html += renderSection(planItems);
  }
  container.innerHTML = html;
}

async function _submitHitl(id, base, hitl_type, approved, response) {
  const res = await fetch('/api/hitl-respond', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, base, hitl_type, approved, response })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Unknown error');
  return data;
}

async function respond(id, base, hitl_type, approved) {
  const textarea = document.getElementById('resp-' + id);
  const textResponse = textarea ? textarea.value.trim() : '';
  const interactive = collectInteractiveState(id);
  const response = [interactive, textResponse].filter(Boolean).join('\\n\\n');
  if (!approved && !response) {
    textarea.classList.add('error'); textarea.focus();
    setTimeout(() => textarea.classList.remove('error'), 2000);
    return;
  }
  const card = document.getElementById('card-' + id);
  card.querySelectorAll('button').forEach(b => b.disabled = true);
  try {
    await _submitHitl(id, base, hitl_type, approved, response);
    card.classList.add('done');
    setTimeout(() => {
      items = items.filter(t => t.id !== id);
      localStorage.setItem('hitl_items', JSON.stringify(items));
      render();
    }, 400);
  } catch (err) {
    card.querySelectorAll('button').forEach(b => b.disabled = false);
    alert('Failed: ' + err.message);
  }
}

async function respondTouch(id, base, hitl_type, dealId, approved) {
  const textarea = document.getElementById('resp-' + id);
  const textResponse = textarea ? textarea.value.trim() : '';
  const interactive = collectInteractiveState(id);
  const response = [interactive, textResponse].filter(Boolean).join('\\n\\n');
  if (!approved && !response) {
    textarea.classList.add('error'); textarea.focus();
    setTimeout(() => textarea.classList.remove('error'), 2000);
    return;
  }
  const card = document.getElementById('card-' + id);
  card.querySelectorAll('button').forEach(b => b.disabled = true);
  try {
    await _submitHitl(id, base, hitl_type, approved, response);

    const sorted = groupedTouches(dealId);
    const idx = sorted.findIndex(t => t.id === id);
    const subsequent = sorted.slice(idx + 1);

    // Cascade decline all subsequent touches if this one was declined
    const cascadeIds = [];
    if (!approved && subsequent.length) {
      const cascadeMsg = 'Cascade declined: prior step in this sequence was declined.';
      for (const touch of subsequent) {
        try { await _submitHitl(touch.id, touch.base, touch.hitl_type, false, cascadeMsg); } catch(e) {}
        cascadeIds.push(touch.id);
      }
    }

    // Determine next touch to expand (first non-cascade remaining)
    const toRemove = new Set([id, ...cascadeIds]);
    const next = sorted.find(t => !toRemove.has(t.id));
    _expandedTouch.set(dealId, next ? next.id : null);

    card.classList.add('done');
    setTimeout(() => {
      items = items.filter(t => !toRemove.has(t.id));
      localStorage.setItem('hitl_items', JSON.stringify(items));
      render();
      if (next) {
        const nextTa = document.getElementById('resp-' + next.id);
        if (nextTa) nextTa.focus();
      }
    }, 400);
  } catch (err) {
    card.querySelectorAll('button').forEach(b => b.disabled = false);
    alert('Failed: ' + err.message);
  }
}

let lastRefreshed = null;

function updateRefreshedLabel() {
  const el = document.getElementById('last-refreshed');
  if (lastRefreshed) el.textContent = 'Last refreshed: ' + lastRefreshed.toLocaleString();
}

const HITL_CACHE_VERSION = '2';

function loadFromCache() {
  try {
    const ver = localStorage.getItem('hitl_version');
    if (ver !== HITL_CACHE_VERSION) {
      localStorage.removeItem('hitl_items');
      localStorage.removeItem('hitl_refreshed');
      localStorage.setItem('hitl_version', HITL_CACHE_VERSION);
      return false;
    }
    const cached = localStorage.getItem('hitl_items');
    const ts = localStorage.getItem('hitl_refreshed');
    if (cached && ts) {
      items = JSON.parse(cached);
      lastRefreshed = new Date(ts);
      document.getElementById('loading').style.display = 'none';
      updateRefreshedLabel();
      render();
      return true;
    }
  } catch(e) {}
  return false;
}

function saveToCache() {
  try {
    localStorage.setItem('hitl_items', JSON.stringify(items));
    localStorage.setItem('hitl_refreshed', lastRefreshed.toISOString());
    localStorage.setItem('hitl_version', HITL_CACHE_VERSION);
  } catch(e) {}
}

function onAssigneeChange() {
  currentAssignee = document.getElementById('assignee-select').value;
  try { localStorage.removeItem('hitl_items'); localStorage.removeItem('hitl_refreshed'); } catch(e) {}
  items = [];
  render();
  refreshHitl();
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) return;
    const cfg = await res.json();
    currentAssignee = cfg.current_user || 'aaron';
    const sel = document.getElementById('assignee-select');
    sel.innerHTML = (cfg.people || [currentAssignee]).map(p =>
      `<option value="${p}" ${p === currentAssignee ? 'selected' : ''}>${p.charAt(0).toUpperCase() + p.slice(1)}</option>`
    ).join('');
  } catch(e) {}
}

async function fetchHitlItems() {
  const statusEl = document.getElementById('loading-status');
  return new Promise((resolve, reject) => {
    let settled = false;
    const settle = (fn) => { if (!settled) { settled = true; fn(); } };
    const es = new EventSource('/api/hitl-tasks-stream?assignee=' + encodeURIComponent(currentAssignee));
    es.addEventListener('status', e => {
      try { if (statusEl) statusEl.textContent = JSON.parse(e.data); } catch(_) {}
    });
    es.addEventListener('done', e => {
      es.close();
      settle(() => {
        try { items = JSON.parse(e.data); } catch(err) { reject(err); return; }
        lastRefreshed = new Date();
        saveToCache();
        updateRefreshedLabel();
        render();
        resolve();
      });
    });
    es.addEventListener('error', e => {
      if (!e.data) return; // connection-level error handled by onerror
      es.close();
      try { settle(() => reject(new Error(JSON.parse(e.data).error || 'Stream error'))); } catch(_) {}
    });
    es.onerror = () => settle(() => { es.close(); reject(new Error('Connection failed')); });
  });
}

async function refreshHitl() {
  const btn = document.getElementById('btn-refresh');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:13px;height:13px;border-width:2px;margin-right:6px;border-top-color:#60a5fa"></span>Refreshing...';
  document.getElementById('error-msg').style.display = 'none';
  _mdCache.clear();
  try {
    await fetchHitlItems();
  } catch(err) {
    alert('Refresh failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '&#8635; Refresh';
  }
}

async function load() {
  await loadConfig();
  try { localStorage.removeItem('hitl_items'); localStorage.removeItem('hitl_refreshed'); } catch(e) {}
  try {
    await fetchHitlItems();
    document.getElementById('loading').style.display = 'none';
  } catch(err) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error-msg').style.display = 'block';
    document.getElementById('error-msg').textContent = 'Failed to load: ' + err.message;
  }
}

load();
setInterval(() => { if (!document.hidden) refreshHitl(); }, 60000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5151, debug=False)
