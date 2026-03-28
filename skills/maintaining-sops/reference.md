# Weekly SOP Maintenance Skill

Scans SOPs directory weekly and reports any that need attention.

## What It Does

1. **Scan** SOPs directory for all `.md` files
2. **Parse** frontmatter for review dates and metadata
3. **Check** if any SOPs are overdue for review
4. **Report** findings (overdue SOPs, new SOPs without review dates)

## Paths

**Obsidian vault:** `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/`

**SOPs directory:** `3-Resources/SOPs/`

**SOP index:** `3-Resources/SOPs/_INDEX.md`

## Expected SOP Frontmatter

Each SOP should have this frontmatter format:

```yaml
---
title: "SOP Name"
last-reviewed: 2026-01-15
next-review: 2026-04-15
owner: aaron
status: active
---
```

**Fields:**
- `title` -- Human-readable SOP name
- `last-reviewed` -- Date of last review (YYYY-MM-DD)
- `next-review` -- When the next review is due (YYYY-MM-DD)
- `owner` -- Who is responsible for the SOP
- `status` -- `active`, `draft`, or `deprecated`

SOPs missing `next-review` are flagged as needing attention.

## Usage

### Via Agent

**Steps:**
1. Read this reference
2. Run scan script:
   ```
   python3 ~/.openclaw/skills/maintaining-systems/scripts/maintaining-sops/scan_sops.py
   ```
3. Review output JSON for overdue/missing review dates
4. If overdue SOPs exist, notify via Telegram
5. Exit silently if everything is current

## Cron Job

**Schedule:** Sunday 10:00 AM
**Expression:** `0 10 * * 0`

## Script Output

The scan script outputs JSON:

```json
{
  "total": 12,
  "scanned_at": "2026-02-07",
  "sops": [
    {
      "file": "Contact-Research.md",
      "title": "Contact Research",
      "owner": "aaron",
      "status": "active",
      "last_reviewed": "2026-01-15",
      "next_review": "2026-04-15",
      "state": "ok"
    },
    {
      "file": "Onboarding.md",
      "title": "Onboarding",
      "owner": "aaron",
      "status": "active",
      "last_reviewed": "2025-06-01",
      "next_review": "2025-09-01",
      "state": "overdue"
    },
    {
      "file": "New-SOP.md",
      "title": null,
      "owner": null,
      "status": null,
      "last_reviewed": null,
      "next_review": null,
      "state": "missing_frontmatter"
    }
  ],
  "summary": {
    "ok": 10,
    "overdue": 1,
    "missing_frontmatter": 1
  }
}
```

**States:**
- `ok` -- Next review date is in the future
- `overdue` -- Next review date has passed
- `missing_frontmatter` -- No `next-review` field found

## Output

Reports to Telegram (only if action needed):
- Number of SOPs found
- Any SOPs needing review (overdue)
- Any SOPs missing review metadata

Exit silently if nothing needs attention.
