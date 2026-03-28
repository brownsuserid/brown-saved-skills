# Creating Projects

> Scripts: `~/.openclaw/skills/managing-projects/scripts/executing-tasks/`
> Quality standard: Every project created by Pablo must meet the **Acceptable** quality level or higher.

## Overview

This reference defines the quality standard for Airtable project creation across all bases. Every project Pablo creates must have, at minimum: a specific name, Definition of Done, goal linkage, and a driver. Project priority feeds into task score calculation, poorly defined projects hurt task prioritization across the board.

**Scope:**
- Personal: Projects table
- AITB: Projects table
- BB: Rocks (7d) table (BB tasks link to Rocks, not Projects)

---

## Quality Levels

| Level | Fields Required | When to Use |
|-------|----------------|-------------|
| **Complete** | Name + Definition of Done + Goal linkage + Driver + Status | Full project setup, Pablo's target |
| **Acceptable** | Name + Definition of Done + Goal linkage + Driver | Standard project creation, Pablo's minimum bar |
| **Draft** | Name only | Manual capture by Aaron, MUST be fleshed out before tasks are linked |

Pablo should always aim for **Complete**. **Acceptable** is the minimum. **Draft** is only for Aaron's manual quick-capture, Pablo never creates Draft projects.

---

## Field-by-Field Guidance

### Name

Specific, outcome-oriented. Include scope and timeframe when relevant.

**Good names:**
- "Q2 AITB Sponsor Outreach"
- "Victoria School Enrollment 2026-27"
- "F|Staff AI Teammates Integration"

**Bad names:**
- "Sponsors", too vague
- "Meeting stuff", no specificity
- "New thing", not outcome-oriented

### Definition of Done (--description)

What does project completion look like? Observable, verifiable outcome.

**Good:**
- "Done when 5 sponsor commitments are signed for Q2 events with payment received"
- "Done when Victoria is enrolled and first-day logistics are confirmed"
- "Done when AI Teammates are deployed to F|Staff with training documentation delivered"

**Bad:**
- "Do the project", not observable
- "Sponsors", not a condition
- "Work on this", no verifiable outcome

### Goal Linkage (--goal)

Links the project to strategy. Pass the goal record ID.

| Base | Field | What to Link |
|------|-------|-------------|
| Personal | `1yr Goals` | Annual goal record ID |
| BB | `Mountains` | Mountain (30d) record ID, chains up to Objectives |
| AITB | *(no goal field on Projects table)* | Document in notes which objective it serves |

**How to find the goal record ID:**
```bash
python3 ~/.openclaw/skills/managing-projects/scripts/routing-airtable-tasks/query_goals.py --base <personal|bb> --type <annual|monthly>
```

For AITB, since there's no goal field on the Projects table, include the objective reference in the `--notes` field: "Supports objective: [objective name]"

### Driver (--driver)

Who is accountable for this project's completion.

| Base | Field | Available |
|------|-------|-----------|
| Personal | *(no Driver field)* | Document in notes if relevant |
| AITB | `Driver` | `pablo`, `aaron`, `juan`, or record ID |
| BB | `Driver` | `pablo`, `aaron`, `juan`, or record ID |

For Personal, the `--driver` flag will be ignored with a warning. Use `--notes` to document accountability if needed.

### Status (--status)

Default: "Not Started". Same values as tasks.

| Value | When |
|-------|------|
| Not Started | Default, project defined but work hasn't begun |
| In Progress | Active work underway |
| Human Review | Awaiting Aaron's review |
| Validating | Aaron actively reviewing |
| Blocked | Waiting on external dependency |
| Completed | Definition of Done met |
| Cancelled | Abandoned, document why in notes |

---

## Per-Base Differences

| Aspect | Personal (Projects) | AITB (Projects) | BB (Rocks 7d) |
|--------|---------------------|------------------|----------------|
| Name field | `Project` | `Project Name` | `Project name` |
| Description field | `Definition of Done` | `Definition of Done` | `Definition of Done` |
| Status field | `Status` | `Status` | `Status` |
| Goal linkage field | `1yr Goals` | *(none)* | `Mountains` |
| Driver field | *(none)* | `Driver` | `Driver` |

---

## Project Creation Command

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_project_rock.py \
  --base <personal|aitb|bb> \
  --name "Q2 AITB Sponsor Outreach" \
  --description "Done when 5 sponsor commitments are signed for Q2 events with payment received" \
  --driver aaron \
  --goal <goalRecordId> \
  --status "Not Started" \
  --notes "Supports objective: Sustainable Funding. Target sponsors: Acme, Globex, Initech."
```

---

## Quality Checklist

Before creating any project, Pablo verifies:

1. **Name is specific and outcome-oriented?** (not vague like "Sponsors")
2. **Definition of Done is observable and verifiable?** ("Done when [condition]")
3. **Goal is linked?** (record ID for Personal/BB, documented in notes for AITB)
4. **Driver is set?** (AITB/BB: --driver flag, Personal: notes if relevant)
5. **Status is appropriate?** (default Not Started)
6. **Notes include context?** (AITB goal reference, background, constraints)

Items 1-4 are required. Items 5-6 are situational.

---

## Integration with Workflows

| Workflow | Reference | How projects are created |
|----------|-----------|------------------------|
| Task routing, no match | [routing-airtable-tasks.md](routing-airtable-tasks.md) Step 5 | Auto-create when routing identifies "new project needed" with sufficient confidence |
| Inbox review | [airtable-inbox-review.md](airtable-inbox-review.md) | Flag unrouted tasks that need new projects |
| Ad-hoc request | Direct from Aaron | "Create a project for X" → use this standard |
