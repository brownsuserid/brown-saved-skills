---
name: managing-projects-bb
description: BB-scoped project management. Route BB task CRUD, routing, morning briefing, inbox review, PR-FAQ, and weekly rock setup requests.
---

# Project Management (BB)

BB-scoped router for project management requests.

---

## Decision Tree

| Request pattern | Reference to read |
|-----------------|-------------------|
| "Create BB task", "new BB task" | [creating-tasks](.claude/skills/creating-tasks/reference.md) |
| "BB project", "new BB rock" | [creating-projects](.claude/skills/creating-projects/reference.md) |
| "Onboard a customer", "solo onboarding", "create from template", "project template" | [creating-projects](.claude/skills/creating-projects/reference.md) (see Template-Based Project Creation section) |
| "Execute BB task", "work on BB task" | [executing-tasks](.claude/skills/executing-tasks/reference.md) |
| "BB priorities", "BB for today" | [setting-todays-priorities](.claude/skills/setting-todays-priorities/reference.md) |
| "BB morning briefing" | [generating-morning-briefing](.claude/skills/generating-morning-briefing/reference.md) |
| "BB inbox", "what's new in BB" | [airtable-inbox-review](.claude/skills/airtable-inbox-review/reference.md) |
| "Route BB task" | [routing-airtable-tasks](.claude/skills/routing-airtable-tasks/reference.md) |
| "Set up BB rocks", "BB weekly rocks", "roll BB tasks" | [setting-up-weekly-rocks](.claude/skills/setting-up-weekly-rocks/reference.md) |
| "Draft PR-FAQ", "write PR-FAQ", "working backwards" | [drafting-pr-faqs](.claude/skills/drafting-pr-faqs/reference.md) |

---

## Guardrails

- Always read the relevant reference file before executing
- When composing workflows, respect each reference's guardrails
- If a step fails mid-workflow, report what succeeded and what failed
