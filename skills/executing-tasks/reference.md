# Pablo Task Execution

> Scripts: `~/.openclaw/skills/managing-projects/scripts/executing-tasks/`
> Field reference: `~/.openclaw/skills/managing-projects/references/airtable-field-reference.md`

## Overview

This skill defines how Pablo executes Airtable tasks through a **7-phase workflow** with **two human-in-the-loop gates**:
1. **Plan approval gate** — Pablo writes a plan, Aaron reviews and approves it before execution begins.
2. **Work review gate** — Pablo submits the completed deliverable, Aaron reviews and closes the task.

**HITL principle:** Pablo plans. Aaron approves. Pablo executes. Aaron reviews. No execution without plan approval. No completion without work sign-off.

---

## HITL Fields

Every task has four HITL fields used to manage the approval flow:

| Field | Who Writes | Purpose |
|-------|-----------|---------|
| **HITL Brief** | Pablo | Execution plan (pre-approval) or completion summary (post-execution) |
| **HITL Response** | Aaron | Approval, feedback, or rejection |
| **HITL Status** | Both | Tracks where the task is in the HITL cycle |
| **Task Output** | Pablo | The deliverable: draft, research doc, link, etc. |

### HITL Status Values

| Value | Meaning | Who Sets |
|-------|---------|----------|
| `Pending Review` | Waiting for Aaron (work review) | Pablo |
| `Response Submitted` | Aaron has responded with feedback, Pablo can proceed | Aaron |
| `Processed` | Pablo has written a plan or acted on Aaron's response | Pablo |
| `Completed` | HITL cycle is done | Aaron |

---

## Full Lifecycle

```
Not Started
  |
  v
In Progress ------> Pablo researches and writes plan to HITL Brief
  |                  HITL Status: Processed
  |                  action: WAIT_APPROVAL  (Pablo STOPS here, does NOT execute)
  |
  |   HUMAN GATE 1: Aaron reads plan in HITL Brief
  |                 Aaron sets HITL Status: Response Submitted to approve
  |
  v
In Progress ------> Pablo picks up approved plan (--phase pick-up)
  |                  Pablo executes plan, stores deliverable in Task Output
  v
Human Review ------> HITL Status: Pending Review (work review)
  |   HUMAN GATE 2: Aaron reads Task Output + HITL Brief summary
  |                 Aaron sets HITL Status: Completed
  v                 Aaron sets Status: Completed
Completed
```

---

## Phase 1: Understand Context

**ALWAYS start here.** Before doing any work, fetch the full task context.

1. Run `get_task.py` to fetch the task with linked records:
   ```bash
   python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/get_task.py --base <base> --id <recordId>
   ```
2. Read and internalize:
   - **Task:** title, description, notes, status, due date, score
   - **Project:** name, status, description (what is this task part of?)
   - **Goal:** what objective does this project serve?
   - **Deal/Organization:** (BB and AITB only) client context
3. Summarize the context before proceeding:
   - "This task is part of [Project] which serves [Goal]. The task asks me to [action]."
4. If the task description is vague or missing, check Notes for additional context.
5. If still unclear, flag as blocked with a note explaining what's needed and notify Aaron.

---

## Phase 2: Understand Stakeholders

If the task involves people, understand who they are before acting.

1. **Named people in the task** -> run the `looking-up-contacts` skill
2. **Linked contacts in Airtable** -> fetch those records
3. Understand:
   - Who is this person? What's their role/relationship?
   - Any prior interactions or context?
   - What's the appropriate tone/channel?
4. **Skip** if the task is purely internal/organizational (e.g., "Archive old notes").

---

## Phase 3: Write Plan

Create a concrete execution plan and save it.

### 3a. Start Planning

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base <base> --id <recordId> --phase start
```

Output tells you the next step: write your plan.

### 3b. Write Plan & Save

Write your execution plan to the **HITL Brief** field. The plan should include:
- What you will do, step by step
- Which tools/skills you will use
- What the deliverable will be
- Any assumptions or open questions

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base <base> --id <recordId> --phase plan-ready \
  --hitl-brief "Plan:\n1. Research contact via looking-up-contacts skill\n2. Search Gmail for prior threads\n3. Draft follow-up email using BB style guide\n4. Create Gmail draft for Aaron to review\n\nDeliverable: Gmail draft ready to send"
```

This keeps Status=In Progress and sets HITL Status=Processed. The task's `action` hint is now `WAIT_APPROVAL`.

> **STOP. Do NOT execute yet.** Aaron must read the plan and set HITL Status=`Response Submitted` to approve it. Move to the next task.

---

## Phase 4: Execute (Only After Plan Approval)

> **Gate:** Only begin Phase 4 when the task's `action` hint is `EXECUTE NOW` (HITL Status=`Response Submitted`). If the action is `WAIT_APPROVAL`, do not proceed — Aaron has not yet approved the plan.

Run `--phase pick-up` first, then execute the plan. Document progress in the **Notes** field as you work.

---

## Phase 5: Submit for Work Review

After execution is complete, submit the work for Aaron's review in one call:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base <base> --id <recordId> --phase work-done \
  --hitl-brief "Completed:\n- Researched Dan via CRM, last interaction Dec meetup\n- Found prior email thread from Jan 15\n- Drafted follow-up referencing partnership discussion\n- Gmail draft ready in aaron@brainbridge.app" \
  --task-output "Gmail draft created. Subject: 'Following up on partnership discussion'\nDraft ID: r-12345\nAccount: aaron@brainbridge.app"
```

This sets Status=Human Review + HITL Status=Pending Review in one call. Output tells you: **STOP. Wait for Aaron.**

### 5c. How Work Review Works (Aaron's Side)

Aaron finds tasks with `Status=Human Review` + `HITL Status=Pending Review` + `Task Output` populated. For each:
- Reads **Task Output** (the deliverable)
- Reads **HITL Brief** (the completion summary)
- Writes feedback in **HITL Response** (or confirms approval)
- Sets **HITL Status** to `Completed`
- Sets **Status** to `Completed`

If Aaron rejects or requests changes: sets **HITL Status** to `Response Submitted`, sets **Status** to `In Progress`, and Pablo picks it back up at Phase 3e.

---

## Phase 6: Journal to Obsidian — SKIP

**Journaling is handled centrally by the Daily Completed Tasks Sync cron (runs nightly at 11pm).** Do NOT write to the Obsidian daily note during task execution. The sync cron captures all task activity automatically.

---

## Phase 7: Follow-Up Tasks

When a completed task generates new work, **create a new task**, never modify the original.

**Quality standard:** Follow-ups must meet the **Acceptable** quality level, see [creating-tasks.md](creating-tasks.md). Every follow-up needs: actionable title, Definition of Done, assignee, and project.

### Creating Follow-Ups

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py --base <base> \
    --title "Follow-up: Check for reply from Dan on partnership proposal" \
    --description "Done when Dan's reply is received and next steps are documented in task notes. If no reply after 3 days, escalate to Aaron." \
    --project <sameProjectId> \
    --linked-task <originalTaskId> \
    --assignee pablo \
    --due-date "2026-02-17" \
    --notes "Original outreach sent via Gmail on 2/14. Thread ID: abc123"
```

### Field Guidance for Follow-Ups

- **Title:** Start with "Follow-up:" + specific action verb + context
- **Description:** Derive from follow-up context, what specifically needs to happen and what "done" looks like
- **Project:** Same project as the original task (already resolved)
- **Assignee:** Set explicitly, pablo for automatable, aaron for manual/approval-gated
- **Due date:** Set when there's a clear timeline (e.g., "check for reply in 3 days" -> due date 3 days out)
- **Linked task:** Always pass the original task's record ID for traceability

### Rules

- **ALWAYS** create a new task for follow-up work
- **NEVER** add follow-up notes to the original task's Definition of Done
- Link to the same project as the original task
- Assign appropriately (Pablo, Aaron, or specific person)
- Set original task to Human Review, new task to Not Started

### When to Create Follow-Ups

- Draft needs Aaron's review -> task stays In Progress (not a follow-up)
- After Aaron sends email, need to check for reply in 3 days -> create follow-up
- Research reveals new action items -> create follow-up per item
- Task scope expanded beyond original intent -> complete original, create new task

---

## Status Transitions

| From | To | When | Who |
|------|----|------|-----|
| Not Started | In Progress | Starting work (Phase 3a) | Pablo |
| In Progress | Human Review | Work complete, ready for review (Phase 5) | Pablo |
| Human Review | Completed | Aaron approves work (Phase 5c) | Aaron |
| Human Review | In Progress | Aaron requests changes (Phase 5c) | Aaron |
| In Progress | Blocked | Waiting on someone/something | Pablo |
| Blocked | In Progress | Blocker resolved | Pablo |

---

## Task Notes Field Rules

**Good notes** (context that doesn't fit elsewhere):
- "Blocked on Aaron to review NDA, sent via email 2/6"
- "Draft includes updated pricing from Q1 proposal"
- "Contact found in AITB CRM, last interaction was Dec meetup"

**Bad notes** (redundant with status or HITL fields):
- "Started working on this task" -> that's what In Progress means
- "Task is complete" -> that's what Complete means
- "Need to follow up" -> create a new task instead
- "Plan: ..." -> use HITL Brief, not Notes

**NEVER put status updates in the Definition of Done field.** Definition of Done is for acceptance criteria (what "done" looks like). Use the **Notes** field for progress updates and **HITL Brief** for plans/summaries.

---

## Guardrails

### NEVER Do:
- Send emails directly (drafts only)
- Send iMessage/SMS to external contacts
- Delete emails or files permanently
- Post to social media
- Make financial transactions
- Sign legal documents
- Share private data externally
- Execute work without first writing a plan to HITL Brief
- Mark tasks as Completed (only Aaron can)

### Deliverable Storage Rules (CRITICAL)

Where you store output depends on **who needs it** and **what format**:

| Deliverable Type | Where It Goes | How |
|-----------------|---------------|-----|
| **Email drafts** | Gmail | `python3 ~/.openclaw/skills/using-gog/scripts/draft_email.py --account <personal\|bb\|aitb> --to <email> --subject "..." --body "..."` |
| **Aaron-only docs** (research, audits, plans, internal notes) | Obsidian | Write to `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/1-Projects/[ProjectName]/` |
| **Shared docs** (task mentions another person who needs it) | Google Drive | `gog drive upload <file>` or `gog docs create` |
| **Binary files** (PDF, audio, images, video) | Google Drive | Never store locally. Never download ML models. |
| **Short output** (<500 chars, IDs, links, confirmations) | Airtable Task Output field | Pass directly via `--task-output` |
| **Temp/scratch files** | `~/.openclaw/workspace/tmp/<run-name>/` | Clean up after run completes |

**Decision rule:** If the task names a person other than Aaron, the deliverable likely needs to be shared. Use Google Drive.

**NEVER:**
- Write files to `~/.openclaw/workspace/` root or create new subdirectories there
- Create `drafts/`, `deliverables/`, or any ad-hoc output directories
- Store email drafts as `.md` files anywhere (always Gmail)
- Use `~/clawd/drafts` (deprecated)
- Download large binaries or ML models to the workspace

**Airtable Task Output** should always contain a reference to where the real deliverable lives:
- `"Gmail draft created. Subject: 'Re: Partnership'. Draft ID: r-12345. Account: aaron@brainbridge.app"`
- `"Research doc: Obsidian 1-Projects/Startup Zones/tucson-tech-meetups.md"`
- `"Uploaded to Google Drive: [filename]. Shared with Peter Mantas."`

### ALWAYS Do:
- Write execution plan to HITL Brief before starting work
- Store deliverables per the rules above
- Draft external communications for Aaron review
- Use `trash` instead of `rm` for file deletion
- Cite sources for research
- Log significant work to memory
- Ask when uncertain

---

## Integration with Other Skills

| Task Type | Tool / Command |
|-----------|----------------|
| Draft email | `python3 ~/.openclaw/skills/using-gog/scripts/draft_email.py --account <personal\|bb\|aitb> --to <email> --subject "..." --body "..."` |
| Read email | `gog gmail get <messageId>` or `gog gmail get <messageId> --json` |
| Read thread | `gog gmail thread get <threadId>` |
| Search email | `gog gmail messages search "<query>" --max 10` |
| Reply to email | `python3 ~/.openclaw/skills/using-gog/scripts/draft_email.py --account <personal\|bb\|aitb> --to <email> --subject "Re: ..." --body "..." --reply-to-message-id <msgId>` |
| Calendar: view | `gog calendar events --today` or `--week` or `--days 7` |
| Calendar: create | `gog calendar create primary --summary "..." --from <iso> --to <iso>` |
| Calendar: search | `gog calendar search "<query>" --from today --to friday` |
| Read Google Doc | `gog docs cat <docId>` or `gog docs export <docId> --mime text/plain` |
| Research contact | looking-up-contacts skill |
| Create skill | skill-creator skill |
| Airtable routing | routing-airtable-tasks, see [routing-airtable-tasks.md](routing-airtable-tasks.md) |
| File operations | Standard shell (trash > rm) |

**gog approval required:** `gog gmail send`, `gog gmail drafts send`, `gog calendar delete`, `gog calendar create --attendees`, `gog chat messages send`. Always draft, never send directly.

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `get_task.py` | Fetch task with full context | `--base`, `--id`, `--no-resolve-links` |
| `search_tasks.py` | Search/filter tasks | `--base`, `--assignee`, `--status`, `--query`, `--max` |
| `update_task.py` | Update task fields | `--base`, `--id`, `--status`, `--notes`, `--assignee`, `--hitl-brief`, `--hitl-response`, `--hitl-status`, `--task-output` |
| `create_task.py` | Create follow-up tasks | `--base`, `--title`, `--description`, `--project`, `--assignee`, `--due-date`, `--for-today`, `--linked-task` |

See `~/.openclaw/skills/managing-projects/references/airtable-field-reference.md` for detailed field mappings and status values per base.
