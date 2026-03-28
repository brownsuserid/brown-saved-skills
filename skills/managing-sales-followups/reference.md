# Managing Sales Tasks

> Output: Prioritized sales task dashboard + drafted follow-ups
> Cadence: **On-demand** or morning briefing integration

## Overview

Surfaces ALL open sales tasks from the BB pipeline assigned to Aaron, organized by priority and deal. Follow-up intent tasks are tagged separately for quick identification. Enriches selected tasks with deal, contact, and interaction history for informed action.

When drafting follow-up emails, read and apply the companion references:
- [bb-email-style-guide.md](bb-email-style-guide.md): Aaron's voice, tone, structure, signature phrases
- [bb-email-approaches.md](bb-email-approaches.md): Five approach frameworks + selection guide + objection handling
- [bb-case-studies.md](bb-case-studies.md): Anonymized case studies, proof points, matching rules

**Use cases:**
- "What sales tasks do I have?"
- "Walk me through my pipeline tasks"
- "What needs doing on deals?"
- "What follow-ups are overdue?"
- "Which deals haven't been touched in 2 weeks?"
- "Draft a follow-up email for Jon Fernandez"
- "Surface all stale deals in the pipeline"

---

## Phase 1: Scan Sales Tasks

Run the scan script to find all deal-linked tasks in BB assigned to Aaron:

```bash
# All sales tasks (default)
python3 ~/.openclaw/skills/managing-finances/scripts/managing-sales-followups/scan_sales_tasks.py

# Follow-up intent tasks only (legacy behavior)
python3 ~/.openclaw/skills/managing-finances/scripts/managing-sales-followups/scan_sales_tasks.py --follow-ups-only
```

**What it finds:** Every open task assigned to Aaron that is linked to an open deal. Tasks linked to closed deals (Closed Won/Lost) are excluded.

**Task categorization:**
- `follow_up`: Task name matches follow-up keywords (see below)
- `action_item`: Everything else (SOWs, demos, proposals, reviews, etc.)

**Follow-up keyword detection** (task name contains any of):
- "follow up", "follow-up", "followup"
- "send email", "send proposal", "send materials", "send docs", "send demo"
- "reach out", "reach-out"
- "schedule call", "schedule zoom", "schedule meeting"
- "check in", "check-in"
- "send to", "forward to", "send final", "send written", "send partnership"

**Filters:**
- Assigned to Aaron (`recXgsS1kw8xdSFSW` in BB)
- Status is NOT Completed, Archived, Cancelled
- Linked to at least one deal
- Deal is NOT in a terminal stage (Signed Proposal Won/Lost, Disqualified)
- Base: BB only

**Staleness tiers:**
- **Critical**: 14+ days stale
- **Warning**: 7-13 days stale
- **Watch**: 3-6 days stale
- **Fresh**: 0-2 days (included in default mode, excluded in `--follow-ups-only`)

**Output JSON:**
```json
{
  "generated_at": "2026-02-24T10:00:00Z",
  "summary": {
    "total_tasks": 35,
    "by_category": { "follow_up": 22, "action_item": 13 },
    "by_priority": { "critical": 8, "warning": 9, "watch": 5, "fresh": 13 }
  },
  "tasks": [
    {
      "task_id": "recCQ5jPKYc7vncdT",
      "task_name": "Follow Up with Jon Fernandez",
      "status": "Not Started",
      "category": "follow_up",
      "is_followup": true,
      "priority": "critical",
      "days_stale": 18,
      "deal_name": "TUSD Discovery",
      "deal_stage_name": "08-Reviewing Proposal",
      "deal_org": "Tucson Unified School District",
      "airtable_task_url": "https://airtable.com/..."
    }
  ]
}
```

---

## Phase 2: Review Dashboard

Present tasks grouped by priority tier, with deal context. Follow-up tasks get a `[F]` marker.

```
## Sales Tasks, 2026-02-24

Summary: 35 tasks (22 follow-ups, 13 action items)
Critical: 8 | Warning: 9 | Watch: 5 | Fresh: 13

### CRITICAL (14+ days), 8 tasks

1. [F] Follow Up with Jon Fernandez, 18 days
   Deal: TUSD Discovery (08-Reviewing Proposal) | Tucson Unified SD
   [View task](https://airtable.com/...)

2. [F] Send partnership docs to Kirsten, 21 days
   Deal: BCS Partnership (07-Proposal Meeting Booked)
   [View task](https://airtable.com/...)

3. Draft SOW for Pinnacle, 16 days
   Deal: Pinnacle AI Assessment (06-Aligning Scope) | Pinnacle Corp
   [View task](https://airtable.com/...)

### WARNING (7-13 days), 9 tasks
...

### WATCH (3-6 days), 5 tasks
...

### FRESH (0-2 days), 13 tasks
...
```

**APPROVAL GATE:** Present dashboard and ask Aaron which tasks to act on. Do NOT draft emails without selection.

---

## Phase 3: Enrich Selected Task

Run the enrich script for a selected task to gather full context:

```bash
python3 ~/.openclaw/skills/managing-finances/scripts/managing-sales-followups/enrich_followup.py \
  --task-id recCQ5jPKYc7vncdT

# Also fetch linked deal notes (slower but more context):
python3 ... --task-id recCQ5jPKYc7vncdT --include-notes
```

**Data sources pulled:**

### Airtable (BB base)
- Full task record (name, notes, definition of done, deadline)
- Linked deal record (status, type, pain points, description, stakeholder map)
- Contact via Deal Contacts junction table (`tblxdCIQQ7Uu0g1qS`): name, email, phone, title, LinkedIn
- Organization (name, website, industry)
- Contact Activity Logs (`tblgf9zD001tj6mL5`): up to 10 most recent interaction records
- Deal notes (if `--include-notes`): most recent 3

### Gmail (all 3 accounts, last 30 days)
- `aaroneden77@gmail.com` (personal)
- `aaron@brainbridge.app` (BB)
- `aaron@aitrailblazers.org` (AITB)
- Uses `gog gmail messages search` with contact name

### Meeting Transcripts
- Searches BB and AITB Google Drive transcript folders via `search_transcripts.py`
- Returns up to 5 matching transcripts with title, date, and URL

### Beeper Messages
- Searches all Beeper networks for contact name via `beeper-find.sh`
- Returns matching chats and message previews

**Contact resolution:** Deals link to contacts through the Deal Contacts junction table (`tblxdCIQQ7Uu0g1qS`), not a direct field. The script follows: Deal -> Deal Contacts -> Contact record. Contact fields use `Email (Work)`, `Email (Personal)`, `Phone (Mobile)`, `Phone (Work)`.

**Output:** JSON with full context for drafting. External searches are gated on having a resolved contact name and each has a 30s timeout with graceful fallback.

---

## Phase 4: Draft Follow-Up

Using the enriched context from Phase 3, draft the follow-up directly. Do NOT use draft_followup.py.

**Before drafting, read:**
1. [bb-email-style-guide.md](bb-email-style-guide.md) for Aaron's voice and structure
2. [bb-email-approaches.md](bb-email-approaches.md) to select the right approach framework
3. [bb-case-studies.md](bb-case-studies.md) if including social proof

**Drafting workflow:**
1. Review enriched context (deal stage, pain points, last interaction, contact role)
2. Select approach framework based on deal context (see selection guide in bb-email-approaches.md)
3. If last interaction involved an objection, check the objection handling table
4. Draft email following Aaron's style guide (structure, tone, signature phrases)
5. If relevant, include a case study that matches 2 of 3: industry, role, pain point
6. Present draft to Aaron for review

**Email defaults:**
- From: `aaron@brainbridge.app`
- 3-5 sentences max
- Include Calendly link: `calendly.com/aaroneden/1-on-1` (or `/20min` for intros, `/1-on-1-call-45m-pri` for sales)
- Sign-off: "Best,"

**After approval:**
- Create Gmail draft:
  ```bash
  python3 ~/.openclaw/skills/using-gog/scripts/draft_email.py \
    --account bb \
    --to <contact_email> \
    --subject "<subject>" \
    --body "<approved draft body>" \
    --no-signature  # body already includes sign-off from drafting workflow
  ```
- Update task notes: "Draft created {date}"

---

## Airtable Schema

### BB Tasks (tblmQBAxcDPjajPiE)

| Field | Description |
|-------|-------------|
| Task | Task name, used for keyword matching |
| Status | Not Started / In Progress / Blocked / Completed / Archived / Cancelled |
| Assignee | Linked to People table |
| Deals | Linked deals |
| Definition of Done | Task instructions/context |
| Notes | Additional notes |
| Created | Creation timestamp |
| Deadline | Optional due date |

### BB Deals (tblw6rTtN2QJCrOqf)

See [sales-deal-review.md](sales-deal-review.md) for full schema. Key fields used here:
- Name, Status, Type, Description, Pain Points, Stakeholder Map, Organization, Deal Contacts, Notes

### BB Deal Contacts junction (tblxdCIQQ7Uu0g1qS)

| Field | Description |
|-------|-------------|
| Deal | Linked deal record |
| Contact | Linked contact record |
| Deal Stage | Current deal stage |
| Link | Display formula: "{deal} - {contact} - ({ID})" |

### BB Contact Activity Logs (tblgf9zD001tj6mL5)

| Field | Description |
|-------|-------------|
| Contact | Linked contact record |
| Activity Type | Meeting Attended, Email Sent, Phone Call Attended, etc. |
| Details | Rich text with interaction summary |
| Created | Timestamp |
| Hash | Dedup key (e.g. "note:recXXX") |

---

## Guardrails

- **Never send emails automatically**, always draft for Aaron's review
- **Skip blocked tasks** unless blocked 14+ days with an expired time-based block
- **Skip closed deals**, never follow up on terminal-stage deals
- **Approval gate**, always present dashboard before drafting; wait for Aaron to select specific tasks
- **Missing email**, if contact has no email, print draft body for manual use; do not fail silently
- **Read companion references** before drafting. Do not draft from memory or generic patterns.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scan_sales_tasks.py` | Find ALL deal-linked tasks in BB assigned to Aaron, calculate staleness, categorize |
| `scan_stale_followups.py` | Legacy: follow-up intent tasks only (use `scan_sales_tasks.py --follow-ups-only` instead) |
| `enrich_followup.py` | Pull full context for a task: deal, contact (via junction), org, activity logs, emails, transcripts, Beeper |

### Companion References (read before drafting)

| Reference | Purpose |
|-----------|---------|
| [bb-email-style-guide.md](bb-email-style-guide.md) | Aaron's and Josh's email voice, tone, structure, signature phrases |
| [bb-email-approaches.md](bb-email-approaches.md) | Five outreach approach frameworks, selection guide, objection handling |
| [bb-case-studies.md](bb-case-studies.md) | Anonymized case studies, proof points, industry matching rules |

### External scripts used by enrich

| Script | Location | Purpose |
|--------|----------|---------|
| `search_transcripts.py` | `skills/maintaining-relationships/scripts/searching-meeting-transcripts/` | Search meeting transcripts in Google Drive |
| `beeper-find.sh` | `skills/maintaining-relationships/scripts/using-beeper/` | Search Beeper messages across all networks |

---

## Integration

- **Trigger:** On-demand ("what sales tasks do I have?", "walk through my pipeline") or morning briefing section
- **Base:** BB only
- **Depends on:** `_shared/_config.py`, `AIRTABLE_TOKEN`, `gog` CLI, `BEEPER_TOKEN`
- **Cron (optional):** Add to morning briefing, run scan, append Critical/Warning section to briefing output
