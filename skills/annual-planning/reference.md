# Annual Planning

> Scripts: `~/.openclaw/skills/managing-projects/scripts/annual-planning/`
> Cadence: **Late December or early January** (~3-4 hour guided session, can split across 2 days)
> Obsidian Life Roadmap: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/2-Areas of Responsibility/Mental/Life, 10-Year, 5-Year, Current Year Goals.md`
> Obsidian Annual Goals: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/1-Projects/Annual Goals {YEAR}/`
> Obsidian Annual Wrap-up Template: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/Extras/Templates/Annual Wrap-up Template.md`

## Overview

Guided annual planning session across all 3 Airtable bases and Obsidian. Pablo gathers data from the past year, guides Aaron through deep reflection and life roadmap review, then facilitates goal-setting across 7 life categories, creating Objectives in Airtable and detailed goal documents in Obsidian.

**Outcome**: Annual Objectives created in all 3 Airtable bases, linked to long-term goals. Obsidian goal docs written for each category. Annual GPS ("One Thing") selected. Bucket list reviewed. Ready for first monthly planning session.

**Annual planning feeds monthly planning**: Objectives created here become the parent goals that Mountains (30d) link to during [monthly planning](monthly-planning.md).

---

## Life Categories and Base Mapping

Aaron tracks goals across 7 categories. Each maps to an Airtable base:

| Category | Primary Base | Airtable Table | Notes |
|----------|-------------|----------------|-------|
| Mental | Personal | 1yr Goals | Journaling, emotional intelligence, self-awareness |
| Physical | Personal | 1yr Goals | Exercise, nutrition, health metrics |
| Community | AITB | Objectives (1y) | AITB growth, apprentices, WCGB hours |
| Work | Personal / BB | 1yr Goals / Objectives (1y) | Career goals, BB revenue, consulting |
| Financial | Personal | 1yr Goals | Burn rate, savings, trading, income independence |
| Key Relationships | Personal | 1yr Goals | Family, friends, networking |
| Personal | Personal | 1yr Goals | Travel, bucket list, hobbies, growth |

**Note**: Some goals span bases. Financial goals with BB revenue targets should have corresponding BB Objectives. Community goals that involve BB clients may need both AITB and BB Objectives.

---

## Phase 1: Gather Data (~automated, 5 min)

Pablo runs the data gathering script to compile the annual briefing.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/annual-planning/gather_annual_data.py
```

**Output** (JSON): Current annual goals/objectives from all 3 bases, mountain completion rates, project completion stats, and goal statuses.

Also read the Obsidian Life Roadmap document for long-term context:

```bash
cat ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/2nd\ Brain\ \(I\)/2-Areas\ of\ Responsibility/Mental/Life,\ 10-Year,\ 5-Year,\ Current\ Year\ Goals.md
```

Present to Aaron as a structured briefing:
- Vision Statement from Life Roadmap
- Per-category summary: this year's goals, status, mountains completed, mountains remaining
- Goals that were "Done" vs "Not Started" vs "Off Track"
- Per-base stats: total objectives, completion rate

---

## Phase 2: Year in Review (~30 min, guided conversation)

### Quantitative Review

For each category, present:
- Goals set at start of year
- Current status (Done / On Track / Off Track / Not Started)
- Mountains completed under each goal
- Projects completed under each goal

### Qualitative Reflection

Guide Aaron through the Annual Wrap-up Template prompts:

1. **How did I do against each annual goal?**, Walk through every goal, celebrate wins, acknowledge misses
2. **What measurable impact did I have?**, Number of people positively impacted, specific outcomes
3. **What went well this year?**, Patterns, habits that stuck, breakthroughs
4. **What could have gone better?**, Recurring frustrations, dropped balls, energy drains
5. **What did I learn?**, About myself, work, relationships, money, health
6. **How did I play or recharge?**, Vacations, hobbies, rest, fun

### Annual Metrics

Capture key metrics for the year:
- BB revenue total
- Burn rate average
- Exercise consistency
- Journaling consistency
- Relationship touchpoints (calls, dates, visits)

---

## Phase 3: Life Roadmap Review (~20 min)

Review and optionally update the long-term vision.

### Vision Statement Check
Read the current Vision Statement. Ask: Does this still resonate? Any adjustments?

### 10-Year Goals Check
For each category, review 10-year goals. Ask: Am I on track for these? Any that need revision?

### 5-Year Goals Check
For each category, review 5-year goals. Ask: Am I closer? What needs to shift?

### Life Summary Sentence
From the Annual Wrap-up Template: Refine the "Life Summary Sentence."

### Update Obsidian
If any changes are needed to the Life Roadmap doc, update it now.

---

## Phase 4: Annual Goal Setting (~60 min, category by category)

For each of the 7 categories, walk through:

### 4a. Review What Exists

Look at last year's goals in that category. What carries over? What's done? What's dropped?

### 4b. Set New Goals

For each category, Aaron defines 1-3 goals for the year. Each goal needs:
- **Name**: Specific, measurable outcome
- **Measurements**: How do we know it's done? (quantitative where possible)
- **Area of Focus**: The category (Mental, Physical, etc.)
- **Priority**: 1-5 stars (Personal base only)
- **Status**: Not Started (default for new goals)

**Goal quality standard:**
- Specific and measurable (not "get healthier" but "Exercise 4x/week, tracked")
- Includes input metrics (actions I control) not just outcome metrics
- Connected to 5-year goals from Life Roadmap
- Has at least one concrete project or habit to start immediately

### 4c. Create in Airtable

For each goal, create the Objective/Goal in the appropriate base:

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/annual-planning/create_objective.py \
  --base <personal|aitb|bb> \
  --name "Specific annual goal" \
  --description "Measurements: [how we know it's done]" \
  --category <mental|physical|community|work|financial|relationships|personal> \
  --year 2027 \
  --priority <1-5> \
  --status not_started
```

**Personal-specific fields**: Area of Focus, Year, Priority (rating 1-5), 5yr Goals link
**BB-specific fields**: Years, Organization (BB or SBAI)
**AITB**: Name + Notes only (simplest structure)

### 4d. Create Obsidian Goal Docs

For each category, create or update the detailed Obsidian goal document in `1-Projects/Annual Goals {YEAR}/`. These docs contain:
- Detailed context and "why"
- Habits and systems to support the goal
- Tracking tables
- Action items and projects
- Connections to values

Pablo can draft these based on the conversation, then Aaron reviews and refines.

---

## Phase 5: Annual GPS (~10 min)

From the Annual Wrap-up Template: **"What is the one thing I can accomplish this year that will make my 5-year goals easier or unnecessary?"**

This is Aaron's single most important focus for the year. It should:
- Connect to a 5-year goal
- Be achievable in 12 months
- Have cascading positive effects across categories
- Guide monthly "One Thing" selections

Document the Annual GPS prominently in the summary.

---

## Phase 6: Bucket List & Experiences (~10 min)

Quick review from the Annual Wrap-up Template:
- Review the full Bucket List
- Schedule 1-2 bucket list items for this year
- Plan family experiences (trips, adventures)
- Update the Story Catcher with anything from last year

---

## Phase 7: Action Setup (~15 min)

### Summary Document

Pablo compiles the annual plan into a summary:

```
Annual Plan - {Year}

ANNUAL GPS: {one thing for the year}
VISION: {vision statement}

PERSONAL BASE ({N} goals)
  Mental:
    - {Goal name} (Priority: {N}), {Measurements}
  Physical:
    - {Goal name} ...
  Financial:
    - {Goal name} ...
  Key Relationships:
    - {Goal name} ...
  Personal:
    - {Goal name} ...

AITB BASE ({N} objectives)
  Community:
    - {Objective name}, {Notes}

BB BASE ({N} objectives)
  Work/Revenue:
    - {Objective name}, {Description}

YEAR IN REVIEW TAKEAWAYS:
- {key insight 1}
- {key insight 2}

BUCKET LIST FOR THE YEAR:
- {item 1}
- {item 2}

IMMEDIATE ACTIONS:
- {first project or habit to start}
- {second project or habit to start}
```

### Trigger First Monthly Planning

Annual planning naturally flows into the first monthly planning session of the year. After completing annual planning, immediately run [monthly-planning.md](monthly-planning.md) to create the first month's Mountains linked to the new Objectives.

### Update Obsidian Annual Wrap-up

Create the annual wrap-up note from template if it doesn't exist. Fill in the review sections completed during Phase 2.

---

## Objective Table Details

### Personal: 1yr Goals (tbll1AUS4uBF9Cgnh)

| Field | Type | Values |
|-------|------|--------|
| Name | singleLineText | Goal name |
| Measurements | multilineText | How we measure success |
| Status | singleSelect | Not Started, On Track, Done, Off Track |
| Area of Focus | singleSelect | Community, Financial, Key Relationships, Mental, Personal, Physical, Work/Intuit |
| Year | singleSelect | 2024, 2025, 2026, 2027 |
| Priority | rating | 1-5 stars |
| Projects | multipleRecordLinks | Linked projects |
| 5yr Goals | multipleRecordLinks | Linked 5-year goals |

### AITB: Objectives (1y) (tblZIpLbkqFjAniNR)

| Field | Type | Values |
|-------|------|--------|
| Name | singleLineText | Objective name |
| Notes | multilineText | Description and context |
| Status | singleSelect | Todo, In progress, Done |
| Mountains (30d) | multipleRecordLinks | Linked monthly goals |

### BB: Objectives (1y) (tblAYaj2ZYhZtgp2a)

| Field | Type | Values |
|-------|------|--------|
| Objective | multilineText | Objective name/description |
| Description | multilineText | Detailed description |
| Status | singleSelect | Not Started, On Track, Completed, At Risk, Archived |
| Years | singleSelect | 2024, 2025 (add new years as needed) |
| Organization | singleSelect | BB, SBAI |
| Notes | richText | Additional context |
| Mountains | multipleRecordLinks | Linked monthly goals |

---

## Scripts Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `gather_annual_data.py` | Fetch all objectives/goals from all bases with completion stats | *(none, fetches everything)* |
| `create_objective.py` | Create an annual Objective/Goal in any base | `--base --name --description --category --year --priority --status` |
| `update_objective.py` | Update Objective status | `--base --id --status --name --description` |

Also uses from monthly-planning:
| `create_goal_mountain.py` | Create first month's Mountains during action setup | See [monthly-planning.md](monthly-planning.md) |

---

## Objective Status Values Per Base

| Semantic | Personal | AITB | BB |
|----------|----------|------|-----|
| `not_started` | Not Started | Todo | Not Started |
| `on_track` | On Track | In progress | On Track |
| `done` | Done | Done | Completed |
| `off_track` | Off Track | *(n/a)* | At Risk |
| `archived` | *(n/a)* | *(n/a)* | Archived |

---

## Guardrails

- **Confirmation gate**: Present all goals to Aaron before creating anything in Airtable
- **Quality over quantity**: 1-3 goals per category. Push back on more, too many goals = no focus
- **Must connect up**: Every goal should trace to a 5-year or 10-year goal from the Life Roadmap
- **Measurements required**: No goals without specific, measurable success criteria
- **Retrospective first**: Never skip Phase 2, understanding the past year informs better goals
- **Obsidian + Airtable**: Goals live in both systems. Airtable for operational tracking, Obsidian for deep context
- **Annual GPS non-negotiable**: The "One Thing" question must be answered, it guides the entire year

---

## Integration

| Workflow | How it connects |
|----------|----------------|
| Monthly Planning | Objectives created here are the parents for Mountains (30d). First monthly planning immediately follows |
| Morning Briefing | Task scores derive from project priority, which derives from Mountain priority, which derives from Objective focus |
| Task Routing | New Objectives create natural project homes for incoming tasks |
| Weekly/Daily Retros | Retros feed into monthly planning which feeds back to annual goal progress |
| Obsidian | Detailed goal docs complement the operational Airtable records |
