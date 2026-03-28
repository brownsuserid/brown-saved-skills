# Task Quality Audit

> Scripts: `~/.openclaw/skills/managing-projects/scripts/auditing-task-quality/`
> Skills catalog: `build_skills_catalog.py`
> Roadmap output: `~/.openclaw/skills/plans/skill-gaps-roadmap.md`

## Overview

Audits outstanding tasks across all 3 Airtable bases. For each task: checks quality (DoD, project, deal), researches context to fill gaps, maps an execution plan using existing skills, writes findings to task Notes, and documents skill gaps in the roadmap. Produces a summary task per assignee listing all their flagged items.

---

## Phase 1: Build Skills Catalog

Generate the current skills inventory:

```bash
source ~/.zshrc 2>/dev/null
python3 ~/.openclaw/skills/managing-projects/scripts/auditing-task-quality/build_skills_catalog.py
```

Read the JSON output. Internalize:
- Every skill name, description, and layer
- Every reference (sub-skill) and what it handles
- Decision tree patterns (what triggers each skill)

This is your capability map. A task is "covered" if an existing skill or reference can execute it end-to-end.

---

## Phase 2: Fetch Outstanding Tasks

Pull **all Not Started tasks** across all 3 bases, regardless of assignee. This audit covers everyone: Aaron, Pablo, Juan Ortiz, Josh Brown, and unassigned tasks.

```bash
# All bases, all assignees, Not Started only
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py --base all --status "Not Started" --max 200
```

**Scope:** Not Started tasks only. Skip In Progress, Blocked, Human Review, and completed tasks. Those are already in motion and don't need execution plans.

For each task, note: record ID, base, title, description (Definition of Done), notes, assignee, project.

---

## Phase 3: Quality Checks

Before mapping skills, check each task for quality issues. Flag any of:

### 3a. Definition of Done Quality

| Quality Level | Description | Action |
|---------------|-------------|--------|
| **Good** | Clear, measurable, verifiable outcome | No flag |
| **Weak** | Restates the title, vague ("done", "completed"), or just "tbd" | Flag + research context |
| **Missing** | Empty DoD field | Flag + research context |

### 3b. Missing Project

Task has no linked project. Check routing notes for project references. If found, note the suggested project. If not, flag for routing.

### 3c. Missing Deal (BB and AITB only)

Tasks involving external contacts or organizations should have a linked deal. If the task mentions a person/company but has no deal, flag it. Check notes for "DEAL NEEDED" markers from prior routing.

### 3d. Status Mismatch

Notes indicate the work is already done but status is still Not Started. Flag for assignee to confirm completion.

---

## Phase 4: Research Context for Vague Tasks

When a task has a **weak or missing DoD**, research context to propose a better one. Check these sources in order:

### 4a. Task Notes and Linked Records

```bash
# Get full task context including project, goal, deal
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/get_task.py --base <base> --id <recordId>
```

The linked project description and goal often clarify what "done" means for a task.

### 4b. Gmail Threads

Search for related email threads that may have originated the task:

```bash
# Search by contact name or task subject keywords
gog gmail messages search "<contact name OR task keywords>" --max 5 --account <relevant account>
```

Email threads often contain the original request, context, and implicit acceptance criteria.

### 4c. Obsidian Daily Notes

Check recent daily notes for mentions of the task, project, or related contacts:

```bash
# Search in Obsidian vault
grep -r "<keywords>" ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/2nd\ Brain\ \(I\)/3-Resources/Daily\ Notes/ --include="*.md" -l
```

Daily notes from Pablo Activity sections and meeting notes often capture context.

### 4d. Meeting Transcripts

If the task references a meeting or was created after one, check Google Drive for transcripts:

```bash
gog drive search "<meeting topic or contact name> transcript" --max 3
```

### 4e. Propose Improved DoD

Based on research, propose a concrete DoD in the quality flags. Format:

```
SUGGESTED DoD: Done when [specific, observable outcome]. [Additional criteria if found in context.]
```

**Do NOT update the Description/DoD field.** Only write suggestions to Notes. The assignee decides whether to adopt them.

---

## Phase 5: Match Tasks to Skills

For each task, determine the execution path:

### 5a. Classify the Task

| Category | Meaning |
|----------|---------|
| **Fully Covered** | An existing skill/reference handles this end-to-end |
| **Partially Covered** | Some skills apply but gaps remain (manual steps needed) |
| **Not Covered** | No existing skill can execute this task |
| **Needs Clarification** | Task is too vague to assess even after context research |

### 5b. Build the Execution Plan

For **Fully Covered** and **Partially Covered** tasks, build a step-by-step plan referencing specific skills. This plan will be written to the **HITL Brief** field (not Notes).

**Format:**
```
EXECUTION PLAN (auto-generated by task-quality-audit YYYY-MM-DD):
1. [skill-name/reference-name] Action description
2. [skill-name/reference-name] Next action
3. [skill-name/reference-name] Final action
GAP: [description of any manual step not covered by a skill]
```

**Example:**
```
EXECUTION PLAN (auto-generated by task-quality-audit 2026-03-05):
1. [maintaining-relationships/looking-up-contacts] Look up Dan's contact info
2. [using-gog] Search Gmail for prior thread with Dan
3. [maintaining-relationships/messaging] Draft follow-up via Beeper
GAP: None - fully covered
```

**Example with gap:**
```
EXECUTION PLAN (auto-generated by task-quality-audit 2026-03-05):
1. [managing-projects/executing-tasks] Fetch full task context
2. GAP: No skill exists for LinkedIn CSV import to Airtable
3. [maintaining-relationships/looking-up-contacts] Verify imported contacts exist
```

### 5c. Matching Rules

1. **Read the task title and DoD carefully.** The DoD defines what "done" looks like.
2. **Check decision trees first.** Meta-skill SKILL.md files have pattern-matching tables.
3. **Check references second.** Sub-skill references often handle specific task types.
4. **Consider skill composition.** Many tasks need 2-3 skills chained together.
5. **Check the existing roadmap.** `~/.openclaw/skills/plans/next-skills-roadmap-2026-02-22.md` documents known gaps. If a task falls into a known gap, reference the proposed skill.

---

## Phase 6: Write Audit Results to Task

For each task, write results in two places: quality flags go to **Notes**, and the execution plan goes to **HITL Brief**. Both updates can be done in a single `update_task.py` call.

### For tasks with an execution plan (Fully Covered or Partially Covered)

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base <base> --id <recordId> \
  --notes "<existing notes>\n\n---\n<quality flags block>" \
  --hitl-brief "<execution plan block>" \
  --hitl-status "Response Submitted"
```

### For tasks with no execution plan (Not Covered or Needs Clarification)

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base <base> --id <recordId> \
  --notes "<existing notes>\n\n---\n<quality flags block>"
```

### Notes Block Format (quality flags only)

```
---
TASK AUDIT (YYYY-MM-DD):

QUALITY FLAGS:
- [DoD: Missing/Weak/Good] <details>
- [Project: Missing/Linked] <details>
- [Deal: Missing/N/A/Linked] <details>
- [Status: OK/Mismatch] <details>
SUGGESTED DoD: <proposed DoD if researched, omit if DoD is already good>
COVERAGE: Fully Covered / Partially Covered / Not Covered / Needs Clarification
```

### HITL Brief Format (execution plan only)

```
EXECUTION PLAN (auto-generated by task-quality-audit YYYY-MM-DD):
1. [skill/reference] Action
2. [skill/reference] Action
GAP: <description or "None - fully covered">
```

**Rules:**
- **Notes: preserve existing content.** Always append, never overwrite.
- **Use the separator** `---` before the audit block in Notes.
- **HITL Brief: overwrite is acceptable.** It's a plan field, not a history field.
- **HITL Status: only set `Response Submitted`** for tasks where a new execution plan was written to HITL Brief. Do not set it for Not Covered or Needs Clarification tasks.
- **Skip tasks that already have a `TASK AUDIT` block** in their Notes (idempotent).
- **Omit sections that don't apply.** If DoD is good, omit SUGGESTED DoD. If no issues, QUALITY FLAGS can just say "All clear."

---

## Phase 7: Create Summary Tasks per Assignee

After processing all tasks, create one summary task per assignee that has flagged items. This ensures people actively see their quality issues rather than discovering them passively in Notes.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py \
  --base <assignee's primary base> \
  --title "Review task quality flags (N tasks) - YYYY-MM-DD audit" \
  --description "Done when all flagged tasks below have been reviewed and quality issues resolved (DoD clarified, projects linked, deals created, status mismatches fixed)." \
  --assignee <assignee> \
  --notes "<checklist of flagged tasks>"
```

### Summary Notes Format

```
Task Quality Audit - YYYY-MM-DD
Flagged N of M tasks reviewed.

DoD Issues (N):
- [ ] "Task title" (recXXX) - Missing/Weak DoD. Suggested: <suggestion>
- [ ] "Task title" (recXXX) - Missing DoD, no context found.

Missing Projects (N):
- [ ] "Task title" (recXXX) - Needs routing to a project

Missing Deals (N):
- [ ] "Task title" (recXXX) - Needs deal for <contact/org>

Status Mismatches (N):
- [ ] "Task title" (recXXX) - Notes say complete, status says Not Started
```

**Rules:**
- **One task per assignee.** Group all flags for Aaron into one task, all for Pablo into one, etc.
- **Only create if there are flags.** Don't create empty summary tasks.
- **Base selection:** Use the base where the assignee has the most flagged tasks. If tied, use BB for Aaron/Josh, AITB for community tasks.

---

## Phase 8: Document Skill Gaps

Collect all gaps discovered during the audit and write them to the roadmap file.

**Output file:** `~/.openclaw/skills/plans/skill-gaps-roadmap.md`

**Format:**
```markdown
# Skill Gaps Roadmap
**Last updated:** YYYY-MM-DD
**Tasks audited:** N across 3 bases

## Summary

- Fully Covered: N tasks (X%)
- Partially Covered: N tasks (X%)
- Not Covered: N tasks (X%)
- Needs Clarification: N tasks (X%)

## Gaps by Category

### [Gap Name]
**Tasks affected:** N
**Bases:** personal, bb, aitb
**Example tasks:**
- "Task title 1" (recXXX)
- "Task title 2" (recXXX)
**Proposed skill:** [name from existing roadmap, or new proposal]
**Priority:** [Critical/High/Medium/Low] based on task count and blocked status

### [Next Gap]
...

## Existing Roadmap Cross-Reference

Reference: `plans/next-skills-roadmap-2026-02-22.md`

| Proposed Skill | Tasks Found | Status |
|----------------|-------------|--------|
| researching-contacts | N | Planned |
| executing-email-campaigns | N | Planned |
| ... | ... | ... |

## New Gaps (Not in Existing Roadmap)

Any gaps discovered that aren't already in the skills roadmap go here with the same format as above.
```

**Rules:**
- **Overwrite the file each run.** This is a point-in-time snapshot, not an append log.
- **Cross-reference the existing roadmap.** Check `plans/next-skills-roadmap-*.md` files for already-planned skills.
- **Prioritize by task count and blocker status.** Tasks marked Blocked get higher priority.
- **Be specific about the gap.** "No LinkedIn automation" is better than "missing skill."

---

## Phase 9: Report and Update Triggering Task

### 9a. Report to Aaron in chat

After all phases, produce a summary for Aaron:

```
TASK QUALITY AUDIT COMPLETE
---
Tasks audited: N
Fully Covered: N (X%) - execution plans written to HITL Brief
Partially Covered: N (X%) - plans written with gaps noted
Not Covered: N (X%) - gaps documented in roadmap
Needs Clarification: N (X%) - flagged in task notes

Quality issues found:
- Missing/weak DoD: N tasks
- Missing project: N tasks
- Missing deal: N tasks
- Status mismatch: N tasks

Summary tasks created:
- [Assignee]: "Review task quality flags (N tasks)" in [base]

Top skill gaps:
1. [gap] - N tasks affected
2. [gap] - N tasks affected
3. [gap] - N tasks affected

Roadmap updated: ~/.openclaw/skills/plans/skill-gaps-roadmap.md
```

### 9b. Write summary to the triggering task's Notes

This audit is triggered by the "Run task quality audit" recurring task in the **Personal base**. After completing the audit, find that task and append the audit summary to its Notes:

```bash
# Find the triggering task
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/search_tasks.py \
  --base personal --title "task quality audit" --status "Not Started"

# Append audit summary to its Notes
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/update_task.py \
  --base personal --id <triggeringTaskRecordId> \
  --notes "<existing notes>\n\n---\nAUDIT RUN (YYYY-MM-DD HH:MM):\nTasks audited: N | Fully Covered: N | Partially Covered: N | Not Covered: N | Needs Clarification: N\nQuality issues: DoD N, Project N, Deal N, Status mismatch N\nSummary tasks created: [list assignees]\nTop gaps: [top 3 gaps]\nRoadmap: ~/.openclaw/skills/plans/skill-gaps-roadmap.md"
```

**Rules:**
- Always append; never overwrite the triggering task's existing Notes.
- If the triggering task cannot be found (e.g., already completed), skip this step and note it in the chat report.

---

## Guardrails

- **Not Started only.** Only audit tasks with status "Not Started". Skip In Progress, Blocked, Human Review, and completed.
- **All assignees.** Audit tasks for everyone: Aaron, Pablo, Juan Ortiz, Josh Brown, and unassigned.
- **Read-only for task status.** This skill never changes Status or Assignee. It updates Notes (quality flags), HITL Brief (execution plan), HITL Status, and the triggering task's Notes only.
- **Never update Definition of Done.** Suggestions go in Notes only. The assignee decides.
- **Idempotent.** Skip tasks that already have a `TASK AUDIT` block in notes.
- **Preserve existing notes.** Always append to Notes, never overwrite.
- **HITL Brief overwrite is acceptable.** It's a plan field, not a history field.
- **HITL Status `Response Submitted` only for covered tasks.** Only set it when an execution plan was written to HITL Brief (Fully/Partially Covered). Not Covered and Needs Clarification tasks do not get a HITL Status update.
- **Don't execute tasks.** This is an audit/planning skill, not an execution skill.
- **Context research is best-effort.** If Gmail/Obsidian/Drive searches turn up nothing, note "no additional context found" and move on. Don't block the audit.
- **Batch size.** Process up to 50 tasks per run to keep context manageable. If more exist, note the total and recommend running again.

---

## Integration

| Pairs With | How |
|------------|-----|
| executing-tasks | Plans written here are followed during execution |
| routing-airtable-tasks | Unrouted tasks should be routed before auditing |
| setting-todays-priorities | Audit results inform which tasks are ready to execute |
| creating-tasks | "Needs Clarification" tasks may need DoD added |
| maintaining-relationships/looking-up-contacts | Context research for people-related tasks |
| using-gog | Gmail and Drive searches for task origin context |
