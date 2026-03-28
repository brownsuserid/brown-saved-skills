# Morning Briefing

> Scripts: `~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/`

## Overview

This skill produces a daily morning briefing from 4 data sources:

1. **Calendar**, events from 3 Google calendars (BB, Family, AITB) + Intuit Work calendar
2. **Tasks**, top tasks by score + all blocked tasks from Airtable (Personal, AITB, BB bases)
3. **Reminders**, incomplete Intuit reminders from macOS Reminders
4. **Daily Note**, Obsidian daily note creation with briefing content

The skill runs 4 phases in order: Gather Data, AI Analysis, Format Output, Daily Note.

---

## Phase 1: Gather Data

Run the 4 gather scripts. Each outputs structured JSON to stdout.

### 1a. Calendar

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/gather_calendar.py [--date YYYY-MM-DD]
```

Returns: events array with time, title, source, link, start/end ISO timestamps, response_status (accepted/tentative/declined/needsAction/unknown); stats with total_events, meeting_hours, conflicts, and no_buffer pairs.

**response_status values:**
- `accepted` - confirmed attendance
- `tentative` - unsure, on calendar as backup
- `declined` - not attending
- `needsAction` - no response yet
- `unknown` - status unavailable (common for Exchange/Outlook events via Apple Calendar)

### 1b. Tasks

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/gather_top_tasks.py --assignee aaron --max 10
```

Returns:
- `top_tasks` - Aaron's top 10 tasks by score across all bases (excludes blocked, human review, validating)
- `blocked_on_aaron` - Union of: (1) blocked tasks where Notes mention "aaron", (2) ALL of Pablo's blocked tasks, and (3) Human Review tasks assigned to aaron, pablo, or juan. Deduplicated by task ID, sorted by score.
- `all_blocked`, every blocked task with Notes enriched

### 1c. Reminders

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/gather_reminders.py --list Intuit
```

Returns: array of incomplete reminders with title.

### 1d. Rocks / Projects (This Week)

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_projects.py --base personal
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_projects.py --base bb
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_projects.py --base aitb
```

Filter output to projects where `for_this_week == true`. Returns: name, status, description, linked_goals.

This gives Aaron a reminder of his weekly rocks/goals at the top of each briefing to frame the day's priorities.

---

## Phase 2: AI Analysis

Using the gathered JSON, analyze and produce insights for the briefing:

### Rocks Analysis
- List all rocks/projects flagged "For This Week" grouped by base (Personal, BB, AITB)
- Note any rocks that appear stale (old week numbers in the name, e.g. `[wk8]` when current week is 13)
- Flag rocks with no linked tasks in the top 10 or For Today list (risk of being neglected)

### Calendar Analysis
- **Attendance status**: Group events by response_status. Tentative events are backup/optional meetings. Declined events can be excluded from meeting hour counts. Distinguish firm commitments from tentative holds.
- **Conflicts**: List any overlapping events from the `stats.conflicts` array. If one event is tentative and the other accepted, note the tentative one is the backup.
- **Buffer warnings**: List back-to-back meetings from `stats.no_buffer` array
- **Meeting load**: Report total events and meeting hours; flag if > 5 hours. Show separate counts for accepted vs tentative.
- **Focus blocks**: Identify gaps >= 60 minutes as available deep work time. Tentative slots are potential focus blocks if skipped.
- **High-priority meetings**: Flag external meetings or ones with unfamiliar names that may need prep

### Task Prioritization
- Show top 10 tasks by score in a table
- Recommend "For Today" top 5 tasks with 1-sentence reasoning per pick
- Consider: score, due date proximity, whether the task unblocks others (check if task appears in blocked_on_aaron), and today's calendar load (heavy meeting day = favor quick tasks)
- Note tasks due today or overdue

### Blocked Task Intelligence
- **Blocked on Aaron**: List tasks from `blocked_on_aaron`, which includes tasks whose Notes mention Aaron, all of Pablo's blocked tasks, AND all tasks in Human Review status (awaiting Aaron's review)
- **HITL categorization**: For Human Review tasks, use HITL fields to distinguish:
  - `hitl_status=Pending Review` + empty `task_output` = **Plan Approval** (Aaron should read HITL Brief and approve/reject the plan)
  - `hitl_status=Pending Review` + populated `task_output` = **Work Review** (Aaron should review the deliverable in Task Output)
  - Show the HITL Brief snippet (first 100 chars) so Aaron can triage without opening Airtable
- **Quick wins vs deep work**: Categorize blocked tasks by effort (scan Notes for clues)
- **Stale blockers**: Flag any blocked task with no recent Notes activity
- **High-score blocked**: Call out blocked tasks with score > 70

### Reminder Insights
- Report total count
- Flag if count > 10 (suggest triage)

---

## Phase 3: Format Output

Format the briefing as a markdown message. Use this structure:

```
Morning Briefing - {Day of week}, {Month} {Day}, {Year}

THIS WEEK'S ROCKS
---
{Group by base: Personal, BB, AITB}
{For each rock flagged for_this_week: rock name}
{Flag stale rocks (old week numbers) with a note}

CALENDAR ({total_events} events, {meeting_hours}h meetings)
---
{For each event: time range | title (linked if Google) | source | status badge}

Status badges: show (tentative), (declined), (needs response) after the source. Omit for accepted/unknown.
Tentative events are backup meetings - note this context in calendar analysis.

{If conflicts: "Conflicts: event_a overlaps event_b by Xmin"}
{If no_buffer: "No buffer: event_a -> event_b (Xmin gap)"}
{If focus blocks found: "Focus blocks: time-time (Xh Xmin)"}

TOP TASKS (10)
---
{Table: # | Task Name | Score | Base | Status | Due}
{Below each row: Link: airtable_url}

FOR TODAY (top 5 AI recommended)
1. {task name}, {1-sentence reason}
   Link: {airtable_url}
2. ...

NEEDS AARON ({count} tasks)
---

PLAN APPROVALS ({count})
{For Human Review tasks with HITL Status=Pending Review and empty Task Output}
{For each: task name | base | score | assignee}
  Plan: {first 100 chars of HITL Brief}
  Link: {airtable_url}

WORK REVIEWS ({count})
{For Human Review tasks with HITL Status=Pending Review and populated Task Output}
{For each: task name | base | score | assignee}
  Summary: {first 100 chars of HITL Brief}
  Link: {airtable_url}

BLOCKED ({count})
{For blocked tasks}
{For each: task name | base | score | status | due | brief note from Notes field}
  Link: {airtable_url}
{Flag quick wins and high-score items}

REMINDERS ({count})
---
{Bullet list of reminder titles}

---
Daily note: {obsidian_uri}
Generated {timestamp}

Ready to set your priorities for today? Say "yes" to run Today's Priorities now.
```

Rules:
- No emoji in the output
- **EXACT NAMES ONLY**: Always use the exact task title and rock/project name from Airtable verbatim. NEVER paraphrase, shorten, or reword them.
- Always show both the task name as plain text AND the Airtable URL on a separate "Link:" line so both are visible
- For Google calendar events, use markdown links: [Event](link)
- Keep it scannable, no paragraphs, use tables and bullet lists
- Include the Obsidian daily note URI in the footer

---

## Phase 4: Daily Note

After formatting the briefing, save it to a temp file and create/update the Obsidian daily note:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/create_daily_note.py \
    --briefing-file /path/to/briefing.md \
    [--date YYYY-MM-DD]
```

This will:
1. Create the daily note from template if it doesn't exist (will NOT overwrite an existing note)
2. Replace the `%%meetings%%` placeholder with the briefing content
3. Return the Obsidian URI for inclusion in the message footer

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `gather_calendar.py` | Fetch events from 4 calendars, detect conflicts/buffer | `--date YYYY-MM-DD` |
| `gather_top_tasks.py` | Fetch top tasks + all blocked tasks, enrich with Notes | `--assignee NAME --max N` |
| `gather_for_today_tasks.py` | Fetch tasks flagged "For Today" across all 3 bases | `--assignee NAME` · `--include-in-progress` · `--include-blocked` · `--include-human-review` · `--include-all` |
| `gather_reminders.py` | Fetch incomplete reminders via remindctl | `--list NAME` |
| `query_projects.py` | Fetch rocks/projects (filter to `for_this_week`) | `--base NAME` (run for each base) |
| `create_daily_note.py` | Create daily note, populate %%meetings%% | `--briefing-file PATH --date YYYY-MM-DD` |

### Fetching "For Today" Tasks Outside the Morning Briefing

`gather_for_today_tasks.py` is the right tool any time Aaron (or Pablo) needs to see the current For Today task list — not just at morning briefing time.

```bash
# Default: Not Started tasks only (clean, actionable list)
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/gather_for_today_tasks.py --assignee aaron

# Full picture: include In Progress, Blocked, and Human Review
python3 ~/.openclaw/skills/managing-projects/scripts/generating-morning-briefing/gather_for_today_tasks.py --assignee aaron --include-all
```

Use this whenever Aaron says "what are my tasks for today", "let's knock out my tasks", or asks for his current work queue mid-day. The default view excludes non-actionable statuses (In Progress, Blocked, Human Review) so Aaron sees only tasks he can start. Use `--include-all` to see everything active.

**Display format**: The script's JSON output includes a `display_format` field. Follow it. Key rules:
- Numbered list sorted by score (highest first), no grouping by status
- Exact task names only (never paraphrase or shorten)
- Each task shows: number, bold task name, score, base, status, due date (if set)
- Next line: definition of done (from the definition_of_done field)
- Both Airtable and Pablo links on separate lines below the definition of done
- Separate each task with a `---` horizontal rule for readability
- No emoji
- Aaron refers to tasks by number, so numbering must be sequential and stable within a response

---

## Guardrails

- **Read-only**: Never modify Airtable data, scripts only read
- **Graceful degradation**: If any script fails, produce the briefing with available data and note what failed
- **No hardcoded tokens**: Airtable auth uses `AIRTABLE_TOKEN` env var via `_config.py`
- **Idempotent daily note**: Won't overwrite an existing daily note; will only fill %%meetings%% if the placeholder exists
- **Shared infrastructure**: Task scripts reuse `_shared/_config.py`, `search_tasks.py`, and `get_task.py`

---

## Integration

- **Cron**: Runs daily at 5:15 AM Arizona time via openclaw cron
- **Delivery**: In-chat output + Telegram group chat (1586059256:208299) + Obsidian daily note
- **Reused config**: All Airtable base IDs, people IDs, and API helpers come from `_shared/_config.py`
