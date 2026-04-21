"""
Live HITL data builder.

Queries Airtable on demand and returns the same JSON shape as
hitl_real_data.json, so the prototype can treat it as a drop-in
replacement for the embedded static snapshot.

Cached for 60 seconds to keep rapid refreshes cheap. The cache is
invalidated whenever a successful HITL write lands (wired from app.py).

Endpoint: GET /api/hitl-live-data (defined in app.py)
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_CACHE_TTL_SEC = 60.0
_cache_lock = threading.Lock()
_cache: dict[str, Any] = {"payload": None, "built_at": 0.0}


def invalidate_cache() -> None:
    """Force a rebuild on the next request. Call this after a successful write."""
    with _cache_lock:
        _cache["payload"] = None
        _cache["built_at"] = 0.0


# ---------------------------------------------------------------------------
# Parsing helpers (ported from merge_sven_juan.py)
# ---------------------------------------------------------------------------

_SITUATION_RE = re.compile(
    r"##\s*Situation\s*\n([^|\n]+?)\s*(?:\||\n)", re.IGNORECASE
)
_TOUCH_RE = re.compile(r'"touch_number"\s*:\s*(\d+)')
_AUTHORITY_RE = re.compile(r'"authority_level"\s*:\s*"([A-E])"')


def _parse_contact_org(brief: str) -> tuple[str | None, str | None]:
    if not brief:
        return (None, None)
    m = _SITUATION_RE.search(brief)
    if not m:
        return (None, None)
    parts = m.group(1).strip().rsplit(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), None


def _parse_notes_meta(notes: str) -> dict[str, Any]:
    if not notes:
        return {"touch_number": None, "authority_level": None}
    out: dict[str, Any] = {"touch_number": None, "authority_level": None}
    m = _TOUCH_RE.search(notes)
    if m:
        out["touch_number"] = int(m.group(1))
    m = _AUTHORITY_RE.search(notes)
    if m:
        out["authority_level"] = m.group(1)
    return out


# ---------------------------------------------------------------------------
# Airtable fetch helpers
# ---------------------------------------------------------------------------

def _airtable_list_all(url_base: str, formula: str, headers: dict[str, str]) -> list[dict]:
    """Paginate through all records matching a filter formula."""
    records: list[dict] = []
    offset: str | None = None
    while True:
        params: dict[str, Any] = {"pageSize": 100}
        if formula:
            params["filterByFormula"] = formula
        if offset:
            params["offset"] = offset
        url = f"{url_base}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def _airtable_fetch_many(
    url_base: str,
    ids: set[str],
    headers: dict[str, str],
) -> dict[str, dict]:
    """Batch-fetch specific record ids. Airtable has no batch-GET so we use
    filterByFormula OR(...) in groups of 10 ids per call."""
    out: dict[str, dict] = {}
    if not ids:
        return out
    uniq = [rid for rid in ids if rid and isinstance(rid, str) and rid.startswith("rec")]
    for i in range(0, len(uniq), 10):
        chunk = uniq[i : i + 10]
        formula = "OR(" + ",".join(f"RECORD_ID()='{rid}'" for rid in chunk) + ")"
        recs = _airtable_list_all(url_base, formula, headers)
        for rec in recs:
            out[rec["id"]] = rec.get("fields", {}) or {}
    return out


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

# Hardcoded BB-base table IDs. The prototype only targets BB; if we ever
# support multiple bases we can lift these into config lookups.
_BB_BASE_ID = "appwzoLR6BDTeSfyS"
_BB_TASKS_TABLE = "tblmQBAxcDPjajPiE"
_BB_DEALS_TABLE = "tblw6rTtN2QJCrOqf"
_BB_CAMPAIGNS_TABLE = "tbljjeRqnEj2faFvR"
_BB_STAGES_TABLE = "tblzWQfkNzKLFrhse"


def build_live_data(
    airtable_config_mod: Any,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Build the full live-data payload in the shape of hitl_real_data.json.

    Caches for _CACHE_TTL_SEC. Pass force=True to bypass the cache.
    """
    now = time.time()
    with _cache_lock:
        if not force and _cache["payload"] and (now - _cache["built_at"]) < _CACHE_TTL_SEC:
            return _cache["payload"]

    headers = airtable_config_mod.api_headers()
    tasks_url = airtable_config_mod.api_url(_BB_BASE_ID, _BB_TASKS_TABLE)
    deals_url = airtable_config_mod.api_url(_BB_BASE_ID, _BB_DEALS_TABLE)
    campaigns_url = airtable_config_mod.api_url(_BB_BASE_ID, _BB_CAMPAIGNS_TABLE)
    stages_url = airtable_config_mod.api_url(_BB_BASE_ID, _BB_STAGES_TABLE)

    # --- 1. Fetch all HITL-pending tasks (plan + output) ---
    plan_formula = "AND({Status}='In Progress', {HITL Status}='Processed')"
    plans = _airtable_list_all(tasks_url, plan_formula, headers)
    for t in plans:
        t["__hitl_type"] = "plan"
    output_formula = "AND({Status}='Human Review', {HITL Status}='Pending Review')"
    outputs = _airtable_list_all(tasks_url, output_formula, headers)
    for t in outputs:
        t["__hitl_type"] = "output"
    raw_tasks = plans + outputs

    # --- 2. Collect linked ids for batch resolution ---
    deal_ids: set[str] = set()
    for t in raw_tasks:
        for did in (t.get("fields", {}).get("Deals") or []):
            deal_ids.add(did)
    deals = _airtable_fetch_many(deals_url, deal_ids, headers)

    stage_ids: set[str] = set()
    campaign_ids: set[str] = set()
    for d in deals.values():
        for sid in (d.get("Status") or []):  # Status on Deal = linked pipeline stage
            stage_ids.add(sid)
        for cid in (d.get("Campaigns") or []):
            campaign_ids.add(cid)

    stages = _airtable_fetch_many(stages_url, stage_ids, headers)
    campaigns_by_id = _airtable_fetch_many(campaigns_url, campaign_ids, headers)

    # --- 3. Build slim tasks with enrichment ---
    slim_tasks: list[dict[str, Any]] = []
    for t in raw_tasks:
        f = t.get("fields", {}) or {}
        notes_meta = _parse_notes_meta(f.get("Notes", ""))
        contact_name, org_name = _parse_contact_org(f.get("HITL Brief", ""))

        deal_list = f.get("Deals") or []
        deal_id = deal_list[0] if deal_list else None
        deal_fields = deals.get(deal_id or "", {}) or {}

        deal_name = deal_fields.get("Name", None)

        stage_id_list = deal_fields.get("Status") or []
        first_stage_id = stage_id_list[0] if stage_id_list else None
        stage_name = None
        if first_stage_id:
            stage_name = stages.get(first_stage_id, {}).get("Stage Name")

        camp_id_list = deal_fields.get("Campaigns") or []
        camp_names = [
            campaigns_by_id.get(cid, {}).get("Name", "") for cid in camp_id_list
        ]

        # Assignee email may arrive as a list (lookup) or a string
        ae = f.get("Assignee Email")
        if isinstance(ae, list):
            assignee_email = ae[0] if ae else None
        else:
            assignee_email = ae or None

        # Contact identity:
        # Prefer the "## Situation" name from HITL Brief; fall back to Deal
        # Name. Composite key includes deal_id so that two different deals
        # with the same contact stay separate clusters.
        effective_contact = contact_name or deal_name or "(Unknown)"
        contact_key = f"{deal_id or t['id']}::{effective_contact}"

        slim_tasks.append({
            "id": t["id"],
            "task": f.get("Task", "") or "",
            "task_type": f.get("Task Type", "") or "",
            "status": f.get("Status", "") or "",
            "hitl_status": f.get("HITL Status", "") or "",
            "hitl_type": t.get("__hitl_type", "output"),
            "hitl_brief": f.get("HITL Brief", "") or "",
            "def_of_done": f.get("Definition of Done", "") or "",
            "score": f.get("Score", 0) or 0,
            "urgency": f.get("Urgency Score", 0) or 0,
            "due_date": f.get("Due Date", "") or "",
            "created": t.get("createdTime", "") or "",
            "assignee_email": assignee_email,
            "deal_id": deal_id,
            "deal_stage_name": stage_name,
            "contact_id": contact_key,
            "contact_name": effective_contact,
            "org_name": org_name,
            "campaign_ids": camp_id_list,
            "campaign_names": camp_names,
            "touch_number": notes_meta.get("touch_number"),
            "authority_level": notes_meta.get("authority_level"),
        })

    # --- 4. Aggregate contacts + campaigns + stats ---
    contacts_by_key: dict[str, dict[str, Any]] = {}
    by_assignee_global: dict[str, int] = defaultdict(int)
    campaigns_used: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "name": "",
            "description": "",
            "tasks": [],
            "contacts": set(),
            "byAssignee": defaultdict(int),
        }
    )

    for t in slim_tasks:
        ck = t["contact_id"]
        if ck not in contacts_by_key:
            # Re-derive dealName from the first task's deal
            dname = None
            if t["deal_id"]:
                dname = deals.get(t["deal_id"], {}).get("Name")
            contacts_by_key[ck] = {
                "id": ck,
                "name": t["contact_name"],
                "org": t.get("org_name"),
                "dealId": t["deal_id"],
                "dealName": dname,
                "dealStageName": t.get("deal_stage_name"),
                "campaignIds": t.get("campaign_ids", []),
                "campaignNames": t.get("campaign_names", []),
                "taskIds": [],
                "assigneeEmails": set(),
                "pendingTaskCount": 0,
            }
        c = contacts_by_key[ck]
        c["taskIds"].append(t["id"])
        c["pendingTaskCount"] = len(c["taskIds"])
        if t["assignee_email"]:
            c["assigneeEmails"].add(t["assignee_email"])
            by_assignee_global[t["assignee_email"]] += 1

        for cid, cname in zip(t.get("campaign_ids", []), t.get("campaign_names", [])):
            camp = campaigns_used[cid]
            camp["id"] = cid
            camp["name"] = cname or "(unnamed)"
            camp["description"] = (
                campaigns_by_id.get(cid, {}).get("Description", "") or ""
            )
            camp["tasks"].append(t["id"])
            camp["contacts"].add(ck)
            if t["assignee_email"]:
                camp["byAssignee"][t["assignee_email"]] += 1

    contacts_final: list[dict[str, Any]] = []
    for ck, c in contacts_by_key.items():
        c["assigneeEmails"] = sorted(c["assigneeEmails"])
        contacts_final.append(c)

    campaigns_final: list[dict[str, Any]] = []
    for cid, c in campaigns_used.items():
        campaigns_final.append({
            "id": cid,
            "name": c["name"],
            "description": c["description"],
            "taskCountTotal": len(c["tasks"]),
            "contactCount": len(c["contacts"]),
            "byAssignee": dict(c["byAssignee"]),
        })
    campaigns_final.sort(key=lambda c: -c["taskCountTotal"])

    payload = {
        "tasks": slim_tasks,
        "contacts": contacts_final,
        "campaigns": campaigns_final,
        "stats": {
            "totalTasks": len(slim_tasks),
            "totalContacts": len(contacts_final),
            "totalCampaigns": len(campaigns_final),
            "byAssignee": dict(by_assignee_global),
        },
        "built_at": now,
        "ttl_sec": _CACHE_TTL_SEC,
    }

    with _cache_lock:
        _cache["payload"] = payload
        _cache["built_at"] = time.time()

    return payload
