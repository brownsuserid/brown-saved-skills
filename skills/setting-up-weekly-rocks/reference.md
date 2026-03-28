# Setting Up Weekly Rocks

> Scripts: `~/.openclaw/skills/managing-projects/scripts/setting-up-weekly-rocks/`
> Related: [creating-projects.md](creating-projects.md), [creating-tasks.md](creating-tasks.md)

## Overview

This workflow sets up the rocks (7-day projects) for the current week. It runs at the start of each week — usually Monday or Tuesday morning — and does five things:

1. **Discover** which rocks are stale or flagged for this week
2. **Create** any new rocks needed (with proper DoD, mountain linkage, and due date)
3. **Interview** Aaron about each rock to discover remaining work, using recent meeting transcripts to surface suggestions
4. **Roll** all incomplete tasks from old rocks into the new week's rocks
5. **Validate** that old rocks are fully drained

---

## Phase 1: Discover Stale and Active Rocks

There are two sources of rocks to deal with:

### 1a. Stale rocks (old week tag, not yet completed)
Query all active BB rocks and identify any whose name contains a `[wk##]` tag older than the current week. These need their incomplete tasks rolled forward.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_projects.py \
  --base bb
```

Filter the results locally: a rock is stale if:
- Its name matches the pattern `[wk\d+]` AND the week number is less than the current ISO week
- Its `Status` is not `Completed` or `Cancelled`

**Current ISO week and due date calculation:**
```python
import datetime
today = datetime.date.today()
week = today.isocalendar()[1]
year = today.isocalendar()[0]
# Due date defaults to Sunday end-of-week.
# IMPORTANT: Aaron sometimes specifies "3/16" or a different date explicitly — always
# use Aaron's stated date if provided. Only compute from the formula when not specified.
days_until_sunday = (6 - today.weekday()) % 7
# If today IS Sunday, days_until_sunday = 0 — use today as due date.
due_date = (today + datetime.timedelta(days=days_until_sunday)).isoformat()
```

### 1b. Rocks flagged "For This Week"
Also fetch any rock with `For This Week = True` that doesn't yet have the current week tag — these are ongoing rocks that should also be updated and dated.

Use the Airtable API directly:
```python
formula = "AND({For This Week}=TRUE(), {Status}!='Completed', {Status}!='Cancelled')"
```

**Combine both lists** and deduplicate by record ID. This is the complete set to work with.

---

## Phase 2: Create New Rocks (where needed)

For each rock type that needs a new week version, create it using `create_project_rock.py`.

**Naming convention:** `[P|S|O][wk##] Rock Name`
- `P` = Product/delivery rocks
- `S` = Sales rocks
- `O` = Operations rocks

**Standard recurring rocks to check every week:**
| Rock Name Pattern | Base | Typical Mountain |
|---|---|---|
| `[S][wk##] Reach Outs and Proposals` | bb | Current sales mountain |
| `[S][wk##] Marketing/Sales Campaigns` | bb | Current sales mountain |
| `[P][wk##] <Customer> ...` | bb | Current delivery mountain for that customer |

For each new rock:
1. Carry forward the Mountain from the old rock (query `query_goals.py --base bb --type monthly` if needed)
2. Set a clear Definition of Done — carry forward from the old rock or author a new one based on the current state of that workstream
3. Set `Driver` — carry forward from old rock
4. Set `For This Week = True` and `Due Date` = Sunday of the current week (see calculation above)

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_project_rock.py \
  --base bb \
  --name "[S][wk11] Reach Outs and Proposals" \
  --description "Done when: all pipeline contacts have been nudged; ≥2 new sequences started; ≥1 meeting scheduled or proposal sent." \
  --goal <mountain_record_id> \
  --driver aaron
```

Then immediately PATCH the new rock record to set `For This Week` and `Due Date`:
```python
fields = {"For This Week": True, "Due Date": "YYYY-MM-DD"}
# PATCH: https://api.airtable.com/v0/{base_id}/Rocks%20(7d)/{rock_id}
```

---

## Phase 3: Interview Aaron About Each Rock

For each rock (new and existing), run a brief interview to discover tasks that should be created. The goal is to surface work that's implied by recent conversations but hasn't been captured yet.

### Step 3a: Pull recent meeting transcripts

Before the interview, search for relevant transcripts to inform your suggestions.

> ⚠️ **You MUST use `search_transcripts.py`** — do NOT browse Google Drive in a browser, do NOT use `gog drive search` or `gog drive download` directly. The script is the only correct tool here.

```bash
python3 ~/.openclaw/skills/maintaining-relationships/scripts/searching-meeting-transcripts/search_transcripts.py \
  --query "<customer or topic, e.g. 'SciTech Tom' or 'FStaff Fuel' or 'weekly pulse'>" \
  --account bb \
  --max 5
```

Search tips:
- Use the customer name + key person: `"SciTech Tom"`, `"Cetera workshop"`, `"FStaff Fuel Jess"`
- For pipeline context: `"weekly pulse"`, `"BBI inbox"`, `"sales pulse"`
- Results are returned newest-first; read the most recent 1-2 matches

Once you have file IDs from the search results, read the transcript content:
```bash
gog docs cat <fileId> --account aaron@brainbridge.app
```

For AITB meetings use `--account aaron@aitrailblazers.org`.

### Step 3b: Propose tasks for Aaron's approval

For each rock, present:
1. **Tasks already in the rock** — brief summary of what's already queued
2. **Suggested new tasks** — based on transcript review and pattern-matching against the rock's DoD

Format:
```
Rock: [S][wk11] Reach Outs and Proposals
Existing tasks (5): Follow up with Abílio, Reach out to Ryan at ASU, ...

Suggested additions based on BBI pulse (Mar 5) and Sales Pulse (Mar 5):
  → Schedule follow-up with Erica Garrick (discussed next steps in Mar 10 meeting)
  → Send updated proposal to Nearform referral list
  → Add Dumitru Gushan to outreach sequence

Which of these should I create? (reply with numbers, "all", or "none")
```

Wait for Aaron's response and create only the approved tasks using `create_task.py`.

### Step 3c: Create approved tasks

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py \
  --base bb \
  --title "Schedule follow-up with Erica Garrick" \
  --description "Done when meeting is scheduled on calendar." \
  --project <new_rock_id> \
  --assignee pablo
```

---

## Phase 4: Roll Incomplete Tasks

For each stale rock with a new version created, roll all incomplete tasks using:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/setting-up-weekly-rocks/roll_project_tasks.py \
  --base bb \
  --from-rock <old_rock_id> \
  --to-rock <new_rock_id>
```

This script handles full Airtable pagination — it will scan every page of the tasks table regardless of size. Never use a single-page fetch for this purpose.

**Statuses rolled (default):** Not Started, In Progress, Blocked, Human Review, Validating
**Statuses left behind:** Completed, Cancelled, Archived

Use `--dry-run` first if you want to preview what will move before committing.

Works on **all bases** (`--base personal | aitb | bb`).

---

## Phase 5: Validate

After rolling, re-run a check to confirm each old rock is fully drained:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/setting-up-weekly-rocks/roll_project_tasks.py \
  --base bb \
  --from-rock <old_rock_id> \
  --to-rock <new_rock_id> \
  --dry-run
```

Output should read: `"No incomplete tasks found — nothing to roll."`

If tasks remain, they are likely in edge-case statuses or were recently created — inspect and move manually or re-run without `--dry-run`.

---

## Final Report

After completing the workflow, present a summary:

```
Weekly Rocks Setup — Wk11 (due 2026-03-16)
============================================
Rocks created (4):
  ✓ [S][wk11] Reach Outs and Proposals
  ✓ [S][wk11] Marketing/Sales Campaigns
  ✓ [P][wk11] F|Staff - Fuel TeamMate Next Steps
  ✓ [P][wk11] AIOS Admin - AI Teammate Live Config Working

Tasks rolled:
  [S][wk9] Reach Outs → [S][wk11]: 20 tasks
  [S][wk9] Marketing   → [S][wk11]: 5 tasks
  [P][wk8] Fuel        → [P][wk11]: 10 tasks

Tasks created (new, from interview):
  3 tasks added across 2 rocks

All flagged For This Week ✓  |  All due 2026-03-16 ✓
Old rocks fully drained ✓
```

---

## Guardrails

- **Always paginate** when fetching tasks from an old rock. Single-page fetches (maxRecords ≤ 100) will miss tasks in large bases. Use `roll_project_tasks.py` which handles this correctly.
- **Never roll Completed/Cancelled/Archived** tasks — they belong in the old rock as its history.
- **Don't create a new rock** without a Definition of Done and Mountain linkage — orphaned rocks break score calculation for all linked tasks.
- **Confirm task suggestions with Aaron** before creating them — don't auto-create from transcripts without approval.
- **Per-request timeouts** — all API calls should use `timeout=20` on `urlopen`. Pagination loops without timeouts will hang indefinitely on network failure.
- **Transcript search = script only** — always use `search_transcripts.py` to find meeting transcripts. Never use `gog drive search`, `gog drive download`, or a browser to open Google Drive directly. The script handles account routing, folder filtering, and date sorting correctly. Raw gog drive commands return unfiltered results from the wrong folder.
- **Due date = what Aaron says, else Sunday** — if Aaron specifies an explicit date (e.g. "3/16"), use that exact date. Only compute Sunday of the current ISO week as a fallback when no date is given.
