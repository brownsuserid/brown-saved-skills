# Today's Priorities

> Scripts: `~/.openclaw/skills/managing-projects/scripts/setting-todays-priorities/`

## Overview

This skill lets Aaron interactively review and commit daily priority selections to Airtable's "For Today" checkbox across all 3 bases (Personal, AITB, BB). The morning briefing recommends top tasks read-only; this skill is the interactive write companion.

The workflow has 4 phases: Gather Context, Present to Aaron, Aaron Confirms, Set For Today.

---

## Phase 1: Gather Context

Fetch current For Today flags and top task recommendations.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/setting-todays-priorities/fetch_for_today.py --assignee aaron --max-recommendations 10
```

This returns JSON with:
- `current_for_today`, tasks already flagged For Today (across all bases)
- `recommendations`, top tasks by score that are NOT already flagged
- `summary`, counts of each

If the script errors on a base, note which base failed and continue with available data.

---

## Phase 2: Present to Aaron

Display two tables for quick scanning.

### Current For Today Tasks

Number these 1, 2, 3... for easy reference. Present each task as a card with full context:

```
CURRENT FOR TODAY ({count} tasks)
---

1. Task name | Score: 85 | personal | In Progress | Due: 2025-02-10
   Link: airtable_url
   Definition of Done: {description text, or "None" if empty}
   Notes: {notes text, or "None" if empty}

2. Task name | Score: 72 | aitb | Not Started | Due: --
   Link: airtable_url
   Definition of Done: {description text}
   Notes: {notes text}
```

If none are flagged, say: "No tasks currently flagged For Today."

### Recommendations

Letter these A, B, C... for easy reference, same card format:

```
RECOMMENDATIONS (top {count} by score)
---

A. Task name | Score: 91 | personal | In Progress | Due: 2025-02-08
   Link: airtable_url
   Definition of Done: {description text}
   Notes: {notes text}

B. Task name | Score: 88 | aitb | Not Started | Due: --
   Link: airtable_url
   Definition of Done: {description text}
   Notes: {notes text}
```

Rules:
- Show task name as plain text on the first line, with the Airtable link on its own "Link:" line below
- Show "--" for missing due dates
- Flag tasks due today or overdue
- Truncate notes longer than 200 characters with "..."
- No emoji

---

## Phase 3: Aaron Confirms

Ask Aaron what changes to make. Accept natural language instructions:

**Examples of valid input:**
- "keep all, add A and C", keep current flags, also flag recommendations A and C
- "clear 2, add B", unset #2, add recommendation B
- "clear all, set A B C", unset all current, flag A, B, and C
- "keep all", no changes needed
- "add A", keep current, add recommendation A
- "search for [term]", search for a task not in either list

### Handling Search Requests

If Aaron wants to add a task not in the lists, run the search script:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py --base all --assignee aaron --query "<search term>" --max 10
```

Present search results with a new letter series (S1, S2, S3...) and let Aaron include them in selections.

### Parse the Instructions

From Aaron's input, build the change set:
- **SET**, tasks that will have For Today = true (newly flagged)
- **UNSET**, tasks that will have For Today = false (previously flagged, now removed)
- **UNCHANGED**, tasks that remain flagged (no API call needed)

---

## Phase 4: Set For Today

### 4a. Show the Diff

Present a clear summary of what will change:

```
CHANGES TO APPLY
---
SET:    Task A (personal), Task C (bb)
UNSET:  Task 2 (aitb)
KEEP:   Task 1 (personal), Task 3 (bb)
```

If there are no changes, say "No changes to apply" and end.

### 4b. Confirm

Ask Aaron: "Apply these changes?"

Do NOT proceed without explicit confirmation.

### 4c. Execute

Build the records JSON and run the set script:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/setting-todays-priorities/set_for_today.py --records '[{"id":"recXXX","base":"personal","value":true},{"id":"recYYY","base":"aitb","value":false}]'
```

Only include records that are changing (SET or UNSET). Do not include UNCHANGED records.

### 4d. Report Results

Show the outcome from the script's JSON output:

```
RESULTS
---
Updated {successful} of {total_requested} tasks.
- Task A, For Today: SET
- Task 2, For Today: UNSET

{If errors: "Failed: Task X, error message"}
```

---

## Guardrails

- **Never auto-clear** previous For Today flags without Aaron's explicit instruction
- **Always confirm** before writing to Airtable (Phase 4b)
- **Graceful degradation**: If a base errors during fetch, show available data and note the failure
- **No hardcoded tokens**: Auth uses `AIRTABLE_TOKEN` env var via `_config.py`
- **Continue on failure**: If individual record updates fail, report errors and continue with remaining records
- **Read before write**: Always fetch current state (Phase 1) before making changes

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `fetch_for_today.py` | Fetch current flags + recommendations | `--assignee NAME --max-recommendations N` |
| `set_for_today.py` | Set/unset For Today on records | `--records '[JSON array]'` |
| `managing-projects/scripts/executing-tasks/search_tasks.py` | Ad-hoc task search | `--base all --assignee NAME --query TEXT --max N` |

---

## Integration

- **Shared infrastructure**: Reuses `_shared/_config.py` for base configs, API helpers, and people IDs
- **Morning briefing companion**: Morning briefing recommends tasks read-only; this skill commits the selections
- **Airtable field**: Uses the "For Today" checkbox field on all 3 bases' Tasks tables
