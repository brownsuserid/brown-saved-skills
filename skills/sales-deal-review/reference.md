# Sales Deal Review

## Overview

This skill queries both Brain Bridge (BB) and AI Trailblazers (AITB) Airtable bases for open deals, checks if each deal has incomplete tasks assigned to Aaron, and generates a report of deals that need attention.

**BB deals** are categorized by type: New Customer, Existing Customer, Partner.
**AITB deals** are sponsor deals for the nonprofit.

The skill runs twice weekly (Tuesdays and Thursdays at 12:00 PM MST) and delivers a report via Telegram.

---

## Phase 1: Gather Deals

Run the gather script to fetch deals from both bases.

```bash
python3 ~/.openclaw/skills/managing-finances/scripts/sales-deal-review/gather_deals.py
```

### BB Deal Filters
- Assignee includes Aaron's ID (`recXgsS1kw8xdSFSW`)
- All deal types included: New Business, Existing Business, Partner
- Status is NOT "Closed Won", "Closed Lost", or "Closed Lost to Competitor"

### AITB Deal Filters
- All open sponsor deals (no assignee filter, all are relevant)
- Stage is NOT "Closed - Won" or "Closed - Lost"

**Returns JSON structure:**
```json
{
  "deals": [
    {
      "id": "recABC123",
      "name": "Deal Name",
      "status": "Qualification",
      "type": "New Customer",
      "base": "bb",
      "organization_name": "Company Inc",
      "primary_contact_name": "John Doe",
      "task_ids": ["recTASK1"],
      "task_names": ["Follow up on proposal"],
      "has_active_tasks": true,
      "airtable_url": "https://airtable.com/appwzoLR6BDTeSfyS/tblw6rTtN2QJCrOqf/recABC123"
    }
  ],
  "summary": {
    "total_deals": 12,
    "deals_with_tasks": 8,
    "deals_without_tasks": 4,
    "bb": {
      "total": 9,
      "by_type": {
        "New Customer": {"total": 5, "without_tasks": 2},
        "Existing Customer": {"total": 3, "without_tasks": 1},
        "Partner": {"total": 1, "without_tasks": 0}
      },
      "without_tasks": 3
    },
    "aitb": {
      "total": 3,
      "without_tasks": 1
    }
  }
}
```

---

## Phase 2: Gather Tasks per Deal

The script automatically queries the Tasks table in each base to find incomplete tasks assigned to Aaron for each deal.

**Task filter criteria:**
- Linked to the deal (BB: `Deals` field, AITB: `Sponsor Deals` field)
- Assigned to Aaron
- Status is NOT "Completed", "Archived", or "Cancelled"

---

## Phase 3: Format Report

Format the output as a Telegram-friendly message with base sections and BB type grouping:

```
Deal Review - Day, Month Day, Year

SUMMARY
---
Total open deals: 12
  BB: 9 (needing action: 3)
  AITB: 3 (needing action: 1)

BB breakdown:
  New Customer: 5 (needing action: 2)
  Existing Customer: 3 (needing action: 1)
  Partner: 1 (needing action: 0)

========================================
BRAIN BRIDGE
========================================

-- New Customer (5) --

NEEDS NEXT ACTION (2)

| Company | Contact | Stage |
|---------|---------|-------|
| Company A | John Doe | Qualification |
| Company B | Jane Smith | Interest Expressed |

Details:

  Company A (Qualification)
  Contact: John Doe
  https://airtable.com/.../recABC
  ...

HAS ACTIVE TASKS (3)
  Company C (Proposal/Price Quote): Draft SOW, Schedule review
  ...

-- Existing Customer (3) --
...

-- Partner (1) --
...

========================================
AI TRAILBLAZERS (Sponsors)
========================================

NEEDS NEXT ACTION (1)
...

HAS ACTIVE TASKS (2)
...

---
Generated 2026-02-14 12:00:00 MST
```

---

## Phase 4: Deliver

Standard OpenClaw Telegram delivery:
- Target: Telegram group chat (1586059256:208299)
- Save draft report to file for review before sending

---

## Phase 2b: Retrieve Meeting Notes for a Deal

When reviewing a specific deal interactively, fetch meeting notes to inform next-step decisions. Use **both** sources, Airtable notes are summaries, Google Drive has full transcripts.

### Source 1: Airtable Deal Notes (summaries)

1. Fetch the deal record and read its `Notes` field (array of linked record IDs)
2. Fetch each note from the **Notes** table (by name, not table ID) in the same base
3. The note's `Title` field contains a brief meeting summary
4. Sort by `Created` date to find the most recent note

**Note:** Airtable notes are short summaries only. For full meeting content, always check Google Drive.

### Source 2: Google Drive Meeting Transcripts (full content)

Search Google Drive for meeting transcripts using the deal name, company name, or contact names:

```bash
# Search BB account Drive for meeting transcripts
gog drive search "Company Name OR Contact Name" --account aaron@brainbridge.app --max 10 --json

# Read a Google Doc transcript
gog docs cat <docId> --account aaron@brainbridge.app
```

Transcripts are auto-generated from meetings and contain full conversation text with timestamps and speaker attribution. They are the primary source for identifying actionable next steps.

**Best practice:** Always search Google Drive transcripts when reviewing a deal interactively. Airtable notes alone may not capture the full context.

**Note fields (Airtable):**
| Field | Type | Description |
|-------|------|-------------|
| Title | singleLineText | Brief meeting summary text |
| Created | dateTime | When the note was created |
| Deals | multipleRecordLinks | Linked deals |
| Last Modified | dateTime | Last edit timestamp |

---

## Airtable Schema Reference

### BB Deals Table (tblw6rTtN2QJCrOqf)

| Field | Name | Type |
|-------|------|------|
| Name | Name | singleLineText |
| Status | Status | singleSelect |
| Organization | Organization | multipleRecordLinks |
| Deal Contacts | Deal Contacts | multipleRecordLinks (junction to `tblxdCIQQ7Uu0g1qS`) |
| Tasks | Tasks | multipleRecordLinks |
| Notes | Notes | multipleRecordLinks |
| Assignee | Assignee | multipleRecordLinks |
| Type | Type | singleSelect |
| Description | Description | longText |
| Pain Points | Pain Points | longText |
| Stakeholder Map | Stakeholder Map | longText |

**BB Status values:** Contacted, Qualification, Interest Expressed, Empathy Interview, Demo/Inspiration Session, Proposal/Price Quote, Negotiation/Review, Closed Won (excluded), Closed Lost (excluded), Closed Lost to Competitor (excluded)

**BB Type values:** New Business (displayed as "New Customer"), Existing Business ("Existing Customer"), Partner ("Partner")

### AITB Deals Table (tblRb57pOJaYsW6u5)

| Field | ID | Type |
|-------|-----|------|
| Project Title | fldw9di4HKxXMzqjl | singleLineText |
| Stage | fld8GoFIebWqTFtzM | singleSelect |
| Contact | fldZAAn0wL3DSDqMA | multipleRecordLinks |
| Organization Name | fldq5hMs05LMWuzNG | multipleLookupValues |
| Contact Full Name | fldiS4yKYLZBuqbwT | multipleLookupValues |
| Tasks | fldPTUSoPk667JBLO | multipleRecordLinks |
| Deal Value | fld4FUpnYDpzup9S9 | currency |
| Description | fldKuZLYQ6MLSwrQy | singleLineText |

**AITB Stage values:** Backlog, Interest Expressed, Empathy Interview, Scope Identified, Budged Identified, Closed - Won (excluded), Closed - Lost (excluded)

**AITB Type:** All deals are sponsor deals (no Type field).

---

## Guardrails

- **Read-only by default**: Script only reads data; no modifications
- **No modifications without confirmation**: Report is for review only
- **No hardcoded tokens**: Airtable auth uses `AIRTABLE_TOKEN` env var via `_shared/_config.py`
- **Graceful degradation**: If one base fails, report still includes the other

---

## Integration

- **Cron**: Runs Tuesday/Thursday at 12:00 PM MST via openclaw cron
- **Delivery**: Telegram group chat (1586059256:208299)
- **Storage**: Saves draft report to `~/.openclaw/skills/managing-finances/output/sales-deal-review/`
- **Shared config**: Uses `_shared/_config.py` for base IDs, people IDs, API helpers

---

## Scripts Reference

| Script | Purpose | Dependencies |
|--------|---------|-------------|
| `gather_deals.py` | Fetch deals from BB + AITB and check for active tasks | `_shared/_config.py`, AIRTABLE_TOKEN |
| `generate_report.py` | Format deal data as markdown report with type grouping | None |
| `run_review.sh` | Orchestrate gather, report, deliver pipeline | gather_deals.py, generate_report.py |

---

## Scheduling

**Schedule:** Tuesday/Thursday at 12:00 PM MST (UTC-7, no DST -- Arizona)
**Cron expression:** `0 19 * * 2,4`

**Manual run:**
```bash
~/.openclaw/skills/managing-finances/scripts/sales-deal-review/run_review.sh
```
