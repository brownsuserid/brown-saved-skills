# Monthly Planning

> Scripts: `~/.openclaw/skills/managing-projects/scripts/monthly-planning/`
> Cadence: **1st of each month** (~90 min guided session)
> Existing SOP: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/3-Resources/SOPs/Automation/Monthly Review.md`

## Overview

Guided monthly planning session across all 3 Airtable bases (Personal, AITB, BB). Pablo gathers data, presents analysis, guides Aaron through reflection and goal-setting, then creates/archives monthly goals (Mountains) and projects in Airtable.

**Outcome**: Updated monthly goals linked to annual objectives across all bases, with clear focus areas, "One Thing" selected, and Airtable populated for the month ahead.

**Goal hierarchy (all bases):**
```
Objectives (1y) → Mountains (30d) → Rocks/Projects (7d) → Tasks
```

Personal: `1yr Goals` → `Mountains (30d)` → `Projects` → `Tasks`
AITB: `Objectives (1y)` → `Mountains (30d)` → `Rocks (7d)` → `Tasks`
BB: `Objectives (1y)` → `Mountains (30d)` → `Rocks (7d)` → `Tasks`

---

## Phase 1: Gather Data (~automated, 2 min)

Pablo runs the data gathering script to compile the monthly briefing.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/monthly-planning/gather_monthly_data.py
```

**Output** (JSON): Annual goals + current Mountains + active projects + task completion stats across all bases.

Present to Aaron as a structured briefing:
- Annual goals by base with status (On Track / At Risk / Not Started)
- Active Mountains by base with status and linked Objective
- Project counts per base (active / completed last 30d)
- Task completion summary (completed / cancelled / still open per base)

---

## Phase 2: Retrospective (~15 min, guided conversation)

Before planning forward, reflect on the past month. Present the data from Phase 1, then guide Aaron through:

### Questions to Ask

1. **What went well this month?**, Celebrate wins, completed goals, shipped work
2. **What could have gone better?**, Missed targets, stalled projects, recurring friction
3. **What did I learn?**, Insights about process, priorities, energy management
4. **How did I play or recharge?**, Work-life balance check
5. **Any commitments to prune?**, Projects, meetings, or recurring tasks that should stop
6. **How is the operating system working?**, Are the tools (Airtable, OpenClaw, calendars) serving you well? Any friction?

### Capture

Record key takeaways from the retrospective. These inform Phase 4 goal-setting.

---

## Phase 3: Annual Goal Review (~10 min)

For each base, review annual goals against current status.

### Per-Base Review

**For each annual goal, assess:**
- Current status (On Track / At Risk / Done / Not Started)
- Are Mountains (monthly goals) feeding this goal effectively?
- Does this goal need more or fewer Mountains next month?
- Should the goal status be updated?

### Identify Focus Areas

Based on the review, Aaron selects **2-3 annual goals per base** to focus on this month. These drive Mountain creation in Phase 4.

**Red flags to surface:**
- Annual goals with no active Mountains (stalled)
- Annual goals marked "At Risk" with no mitigation plan
- Mountains that completed but didn't meaningfully advance their Objective
- Bases with no annual goals populated (especially AITB, needs initial Objectives)

---

## Phase 4: Monthly Goal Setting (~20 min)

### Mountain Lifecycle

For each base, run the full Mountain lifecycle:

#### 4a. Archive Completed Mountains

Review each Mountain with status "Complete" or that has achieved its Definition of Done. Archive it:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/monthly-planning/update_mountain.py \
  --base <personal|aitb|bb> \
  --id <mountainRecordId> \
  --status archived
```

#### 4b. Review Carry-Over Mountains

Mountains that are still active (On Track, At Risk, On Hold) carry over. For each:
- Is it still relevant? If not, archive or cancel
- Does the status need updating? (On Track → At Risk, etc.)
- Does the priority need adjusting?

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/monthly-planning/update_mountain.py \
  --base <personal|aitb|bb> \
  --id <mountainRecordId> \
  --status on_track \
  --priority 8
```

#### 4c. Create New Mountains

For each focus area identified in Phase 3, create a Mountain:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/monthly-planning/create_goal_mountain.py \
  --base <personal|aitb|bb> \
  --title "Specific, outcome-oriented monthly goal" \
  --description "Done when [observable, verifiable outcome]" \
  --objective <objectiveRecordId> \
  --priority <1-10> \
  --status on_track
```

**Mountain quality standard:**
- **Title**: Specific, measurable outcome for the month. Prefix with category tag for BB/AITB: `[S]` Sales, `[P]` Product, `[O]` Operations
- **Definition of Done**: Observable outcome, "Done when [condition]"
- **Objective link**: Must link to an annual Objective
- **Priority**: 1-10 scale (10 = highest)

**Aim for 3-5 Mountains per base per month.** More than 5 means insufficient focus.

### Select the "One Thing"

From all new and carry-over Mountains across bases, Aaron picks **one** that would make everything else easier or unnecessary. Document this, it guides daily prioritization for the month.

### Select Habit Focus

Choose one habit to focus on forming or strengthening this month. This can link to a Personal annual goal (e.g., "Exercise 4x weekly", "Track food 4x weekly").

---

## Phase 5: Relationship & Network Planning (~5 min)

Quick review:
- Who should I reconnect with this month?
- Any pending meeting follow-ups?
- Networking activities planned?
- LinkedIn or community engagement targets?

Capture any resulting tasks using [creating-tasks.md](creating-tasks.md).

---

## Phase 6: Action Setup (~10 min)

### Summary Document

Pablo compiles the monthly plan into a summary:

```
Monthly Plan - {Month} {Year}

ONE THING: {selected focus}
HABIT FOCUS: {selected habit}

PERSONAL ({N} Mountains)
  Annual Goal: {goal} ({status})
    - {Mountain title} (Priority: {N}), {Definition of Done}
  ...

AITB ({N} Mountains)
  Objective: {objective} ({status})
    - {Mountain title} (Priority: {N}), {Definition of Done}
  ...

BB ({N} Mountains)
  Objective: {objective} ({status})
    - {Mountain title} (Priority: {N}), {Definition of Done}
  ...

RETROSPECTIVE TAKEAWAYS:
- {key insight 1}
- {key insight 2}

RELATIONSHIPS:
- {reconnect / follow-up items}

COMMITMENTS PRUNED:
- {items removed}
```

### Calendar Blocking

Suggest time blocks for the month's focus areas based on calendar review.

### Update Obsidian Monthly Review SOP

Confirm the SOP checklist items are completed. The SOP covers financial review and other items not in this skill, remind Aaron to complete those separately if not already done.

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `gather_monthly_data.py` | Fetch annual goals, Mountains, projects, task stats from all bases | *(none, fetches everything)* |
| `create_goal_mountain.py` | Create a Mountain (30d goal) in any base | `--base --title --description --objective --priority --status --month` |
| `update_mountain.py` | Update Mountain status, priority | `--base --id --status --priority --title --description` |

Also uses from executing-tasks:
| `create_project_rock.py` | Create projects/rocks when new Mountains need downstream projects | See [creating-projects.md](creating-projects.md) |
| `create_task.py` | Create tasks from relationship/action items | See [creating-tasks.md](creating-tasks.md) |

---

## Mountain Status Values

| Semantic | Value |
|----------|-------|
| `not_started` | Not Started |
| `on_track` | On Track |
| `at_risk` | At Risk |
| `on_hold` | On Hold |
| `complete` | Complete |
| `archived` | Archived |

---

## First-Run Setup

If a base has no annual goals/objectives populated (common for AITB), Phase 3 should include creating initial Objectives before Mountains can be linked. Use Airtable directly for Objective creation since it's a one-time setup.

---

## Guardrails

- **Confirmation gate**: Always present the full plan to Aaron before creating/archiving Mountains in Airtable
- **No auto-archive**: Only archive Mountains Aaron explicitly confirms are complete
- **Quality over quantity**: 3-5 Mountains per base. Push back if Aaron tries to set more
- **Link required**: Every Mountain must link to an annual Objective, no orphaned Mountains
- **Retrospective first**: Never skip Phase 2, reflection informs better planning
- **Financial review separate**: This skill does not cover financial review, that's in the Obsidian SOP

---

## Integration

| Workflow | How it connects |
|----------|----------------|
| Morning Briefing | Mountains feed into daily task prioritization, higher priority Mountains = higher task scores |
| Task Routing | New Mountains create natural project homes for incoming tasks |
| Weekly Retro | Weekly retros aggregate into monthly retrospective input |
| Daily Retro | Daily micro-retros feed weekly, which feeds monthly |
| Recurring Tasks | Regeneration ensures monthly-cadence tasks appear on schedule |
