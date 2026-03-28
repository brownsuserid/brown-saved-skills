# Creating Tasks

> Scripts: `~/.openclaw/skills/managing-projects/scripts/executing-tasks/`
> Quality standard: Every task created by Pablo must meet the **Acceptable** quality level or higher.

## Overview

This reference defines the quality standard for Airtable task creation across all workflows. Every task Pablo creates must have, at minimum: an actionable title, Definition of Done, assignee, and project linkage. Project linkage is the #1 priority because score is a calculated field (due date proximity + project priority), tasks without a project have broken scores and sink to the bottom of priority lists.

---

## Quality Levels

| Level | Fields Required | When to Use |
|-------|----------------|-------------|
| **Complete** | Title + Definition of Done + Assignee + Project + Due Date | Tasks with external deadlines or time-sensitive work |
| **Acceptable** | Title + Definition of Done + Assignee + Project | Standard task creation, Pablo's minimum bar |
| **Draft** | Title only | Manual capture by Aaron, MUST be triaged before execution |

Pablo should always aim for **Complete**. **Acceptable** is the minimum. **Draft** is only for Aaron's manual quick-capture, Pablo never creates Draft tasks.

---

## Field-by-Field Guidance

### Title

Must start with an action verb. Be specific about the object.

**Good verbs:** Create, Send, Review, Fix, Schedule, Draft, Research, Set up, Follow up, Update, Migrate, Archive, Analyze, Configure, Prepare

**Good titles:**
- "Draft follow-up email to Dan re: partnership proposal"
- "Review and merge PR #42 for auth refactor"
- "Schedule Q2 planning meeting with AITB board"

**Bad titles:**
- "Look into X", vague, no clear outcome
- "Think about Y", not actionable
- "Dan", no verb, no context
- "Meeting stuff", no specificity

### Definition of Done (--description)

Specific, observable outcome. Use the template: **"Done when [specific verifiable condition]"**

**Good:**
- "Done when follow-up email draft is in Gmail with pricing attachment"
- "Done when competitor analysis doc is in Obsidian with 5+ companies, pricing, and positioning"
- "Done when recurring task sync script handles BB base exclusion"

**Bad:**
- "Research competitors", no observable outcome
- "Follow up", follow up how? with whom? about what?
- "Done", not a condition

### Assignee (--assignee)

Always set explicitly. Never rely on defaults in workflow documentation.

| Assignee | When |
|----------|------|
| `pablo` | Automatable work: drafts, research, data gathering, task management |
| `aaron` | Manual action, approval-gated, external meetings, financial decisions |
| `juan` | Development work, code changes, infrastructure |

### Project (--project)

**CRITICAL**, always link to a project. Without a project, score calculation is broken (score = due date proximity + project priority). The task will sink to the bottom of priority lists.

- If you know the project: pass the record ID directly
- If unsure which project: route via `routing-airtable-tasks` first, see [routing-airtable-tasks.md](routing-airtable-tasks.md)
- Never leave a task in Inbox long-term without a project

**Acceptable exceptions** (document in task notes why project is N/A):
- ShadowTrader operational tasks (ST: Close/Adjust), short-lived same-day tasks that bypass project scoring
- Temporary triage tasks created during inbox review that will be routed immediately after

### Score

**Calculated field**, not settable directly. Derived from due date proximity + project priority.

To influence score:
- Set a due date (increases urgency component)
- Link to a high-priority project (increases priority component)

### Size

**Set during "For Today" selection**, not at creation time. Part of the priority-setting workflow.

| Value | Meaning |
|-------|---------|
| S | < 30 minutes |
| M | 30 min - 2 hours |
| L | 2+ hours |

### Due Date (--due-date)

Set when there's an external deadline or time-sensitive trigger. Format: `YYYY-MM-DD`.

- External deadlines: meeting dates, submission deadlines, expiry dates
- Follow-up timing: "check for reply in 3 days" → set due date 3 days out
- Same-day operational tasks: use today's date
- **Do not fabricate deadlines**, only set when there's a real reason

Due date directly impacts score calculation.

### For Today (--for-today)

Sets the "For Today" checkbox. Use for tasks that need same-day attention.

- ShadowTrader close/adjust tasks, always For Today
- High-priority email-derived tasks, when urgency is clear
- Follow-ups that are already overdue

### Notes (--notes)

Source URLs, context, reference material. Not for status updates.

**Good notes:**
- "Source: https://mail.google.com/mail/u/0/#inbox/abc123"
- "Diffs:\n  13 FEB 26 PUT 52: DB=0, PDF=4"
- "Related to conversation with Dan at Dec meetup"

**Bad notes:**
- "Started working on this", that's what In Progress status means
- "Task is complete", that's what Complete status means

---

## Task Creation Command

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py \
  --base <personal|aitb|bb> \
  --title "Draft partnership proposal for AITB Q2 sponsor" \
  --description "Done when proposal doc is in Google Drive with pricing tiers, deliverables, and timeline. Shared with Aaron for review." \
  --assignee pablo \
  --project <projectRecordId> \
  --due-date "2026-02-20" \
  --for-today \
  --notes "Source: email from Dan on 2/14 re: sponsorship interest"
```

---

## Quality Checklist

Before creating any task, Pablo verifies:

1. **Title starts with an action verb?** (Create, Send, Review, Fix, etc.)
2. **Definition of Done is specific and observable?** ("Done when [condition]")
3. **Assignee is set explicitly?** (pablo, aaron, or juan)
4. **Project is linked?** (record ID passed, or routed first)
5. **Due date set if there's a real deadline?** (don't fabricate)
6. **For Today set if same-day urgency?**
7. **Notes include source/context?** (email URL, prior task link, etc.)

Items 1-4 are required. Items 5-7 are situational.

---

## Integration with Workflows

| Workflow | Reference | Key additions |
|----------|-----------|---------------|
| Task follow-ups | [executing-tasks.md](executing-tasks.md) Phase 6 | `--description` derived from context, `--due-date` when timeline exists |
| Email-derived tasks | [airtable-inbox-review.md](airtable-inbox-review.md) Phase 6 | `--assignee` explicit, `--due-date` from email, `--for-today` for high-priority |
| ST report tasks | [analyzing-shadowtrader-reports.md](../../managing-finances/references/analyzing-shadowtrader-reports.md) Phase 3 | `--due-date` today, `--for-today` always, project N/A (documented exception) |
