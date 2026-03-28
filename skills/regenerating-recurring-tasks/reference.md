# Recurring Tasks

> Scripts: `~/.openclaw/skills/managing-projects/scripts/regenerating-recurring-tasks/`

## Why This Exists

Recurring tasks (weekly reviews, monthly reports, daily standups) need to regenerate automatically when completed. Without this, Aaron or Pablo would need to manually recreate tasks every time one finishes, and habits would silently decay.

The design keeps completed instances as historical records (you can see "I did my weekly review 47 times this year") while automatically spawning the next instance. This is intentionally better than "resetting" a single task to Not Started, which would lose completion history and break score/timeline tracking.

## What It Does

When a recurring task is marked as "Completed" in Airtable, this skill creates a new instance of that task with:
- Status reset to "Not Started"
- Due date calculated based on recurrence pattern
- All other fields preserved (assignee, project, definition of done, notes)

The completed original stays as-is. It is never modified.

## Usage

```bash
source ~/.zshrc 2>/dev/null
~/.openclaw/skills/managing-projects/scripts/regenerating-recurring-tasks/sync-recurring-tasks.sh
```

## Two-Phase Process

### Phase 1: Automatic (sync-recurring-tasks.sh)

The shell script queries Airtable for recently completed tasks with a Recurrence field, then pipes each through `parse_recurrence.py` to calculate the next due date.

| Category | Examples |
|----------|----------|
| Canonical | Daily, Weekly, Bi-weekly, Monthly, Quarterly, Annually |
| Natural language | "every other Tuesday", "every 3 months", "every Friday" |
| Frequency | "4x weekly", "twice a month", "2x monthly" |
| Calendar | "1st and 15th", "end of month" |

Before creating a new instance, the script checks whether an active (non-completed, non-archived) instance already exists. This prevents duplicates, which was the root cause of a previous race condition when two cron jobs overlapped.

### Phase 2: Manual fallback

Read the script output. For any task with `WARNING: Could not parse recurrence`:

1. Look up the task (record ID is in the warning)
2. Read the recurrence text and task context
3. Determine the correct next due date
4. Create the new task instance using `create_task.py` with the right `--due-date`

This is not optional. Unrecognized patterns are your responsibility, not a skip-and-forget. If the pattern is common enough to recur, add support for it in `parse_recurrence.py` so it's handled automatically next time.

## Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `sync-recurring-tasks.sh` | Orchestrator: queries, parses, creates | None (reads Airtable) | Telegram report |
| `parse_recurrence.py` | Parses recurrence text to next date | Recurrence string (argv) | JSON: `{next_date, canonical}` or `{error}` or `{skip, reason}` |

`parse_recurrence.py` exit codes: 0 = success (next_date or skip), 1 = unrecoverable parse error.

## Bases Checked

| Base | ID |
|------|-----|
| Personal | appvh0RXcE3IPCy6X |
| AITB | appweWEnmxwWfwHDa |

**Note:** BB (Brain Bridge) base is excluded per Aaron's request.

## How It Works

1. **Query**: Finds tasks with `Status='Completed'` AND `Recurrence` is set AND `Last Modified` within last 25 hours
2. **Check for active instance**: Searches for an existing task with the same title that's still active (not completed/archived). Skips creation if found.
3. **Parse recurrence**: `parse_recurrence.py` interprets the recurrence text and calculates the next due date
4. **Create new instance**: POSTs a new task via the Airtable API with the calculated due date and all fields from the original
5. **Preserve completed task**: The completed task stays as "Completed", it is NOT modified

The 25-hour window (not 24) provides a buffer for tasks completed late in the day, ensuring they're caught by the next morning's run.

## Stopping a Recurring Task

To stop a recurring task from regenerating:
- **Archive it**: the script only looks for `Status='Completed'`, so archived tasks are ignored
- **Clear the Recurrence field**: tasks without a recurrence pattern are ignored

This design lets you keep a history of completed recurring tasks while controlling which ones continue to regenerate.

## Cron Job

| Job | Schedule | Purpose |
|-----|----------|---------|
| Recurring Tasks | 0 6 * * * | Daily sync at 6am |

Previously two cron jobs (midnight + 6am) caused duplicate task creation due to race conditions. Consolidated to a single 6am run, combined with the active-instance check, to eliminate duplicates.

## Output

Reports to Telegram with:
- Number of new tasks created
- Number skipped (duplicates/existing)
- Any parse failures (with record IDs for Phase 2 follow-up)

## Integration

- Runs before the morning briefing in the Morning Workflow (see SKILL.md)
- Uses `create_task.py` from executing-tasks for the actual task creation
- Morning briefing then picks up the freshly created recurring tasks in its task gathering
