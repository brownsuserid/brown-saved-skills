# Airtable Field Reference

Detailed field mappings, status values, and linked record structure for each base.
Used by the executing-tasks scripts in `scripts/`.

All field names verified against live Airtable data (2026-02-06).

---

## Base IDs

| Base | ID | Purpose |
|------|----|---------|
| Personal OS | `appvh0RXcE3IPCy6X` | Family, health, personal goals |
| AI Trailblazers (AITB) | `appweWEnmxwWfwHDa` | Meetups, workshops, nonprofit |
| Brain Bridge (BB) | `appwzoLR6BDTeSfyS` | Consulting, B2B clients |

---

## Tasks Table

### Table IDs

| Base | Table ID |
|------|----------|
| Personal | `tblxAXXXCOc18a31C` |
| AITB | `tbl5k5KqzkrKIewvq` |
| BB | `tblmQBAxcDPjajPiE` |

### Task Field Names Per Base

| Field | Personal | AITB | BB |
|-------|----------|------|----|
| Title | `Task` | `Task` | `Task` |
| Status | `Status` | `Status` | `Status` |
| Description | `Definition of Done` | `Definition of Done` | `Definition of Done` |
| Notes | `Notes` | `Notes` | `Notes` |
| Assignee | `Assignee` | `Assignee` | `Assignee` |
| Due Date | `Deadline` | `Deadline` | `Deadline` |
| Score | `Score` | `Score` | `Score` |
| Project link | `Project` | `Project` | `Rock` |
| Deals link | *(none)* | `Sponsor Deals` | `Deals` |
| Size | `Size` | `Size` | `Size` |

**Common fields (all bases):** `Date Complete` (date, auto-set by Airtable automation when Status→Completed, also set by update_task.py as backup)

**BB-specific fields:** `Rock This Week`, `Assignee Email`, `Manual sort`, `Project Due Date`, `Recurrence`, `Interval`

**Personal-specific fields:** `Is Overdue`, `Is Complete`, `Order`, `Recurrence`, `Predecessors`

### Status Values (same across all bases)

| Semantic | Value |
|----------|-------|
| `not_started` | Not Started |
| `in_progress` | In Progress |
| `human_review` | Human Review |
| `validating` | Validating |
| `complete` | Completed |
| `blocked` | Blocked |
| `cancelled` | Cancelled |

### Done Statuses (filtered out by default)

| Base | Done Statuses |
|------|---------------|
| Personal | Completed, Cancelled |
| AITB | Completed, Cancelled, Archived |
| BB | Completed, Cancelled |

### HITL Fields (same across all bases)

| Field | Type | Purpose |
|-------|------|---------|
| `HITL Brief` | richText | Pablo writes execution plan (pre-approval) or completion summary (post-execution) |
| `HITL Response` | richText | Aaron writes approval, feedback, or rejection |
| `HITL Status` | singleSelect | Tracks position in the approval cycle |
| `Task Output` | richText | Pablo stores the deliverable (draft, research doc, link, etc.) |

### HITL Status Values

| Value | Meaning | Who Sets |
|-------|---------|----------|
| `Pending Review` | Waiting for Aaron (plan approval or work review) | Pablo |
| `Response Submitted` | Aaron has responded, Pablo can proceed | Aaron |
| `Processed` | Pablo has read Aaron's response and acted on it | Pablo |
| `Completed` | HITL cycle is done | Aaron |

### HITL + Status Combinations

| Status | HITL Status | Task Output | Meaning |
|--------|-------------|-------------|---------|
| Human Review | Pending Review | Empty | Plan approval: Aaron should read HITL Brief |
| Human Review | Pending Review | Populated | Work review: Aaron should read Task Output |
| In Progress | Response Submitted | -- | Aaron approved, Pablo should pick up and execute |
| In Progress | Processed | -- | Pablo is actively executing |
| Completed | Completed | -- | Done, Aaron signed off |

---

## Projects Table

Personal and AITB use a table named `Projects`.
BB tasks link to `Rocks (7d)` instead of Projects directly.

### Field Names Per Base

| Field | Personal (Projects) | AITB (Projects) | BB (Rocks 7d) |
|-------|----------|------|----|
| Name | `Project` | `Project Name` | `Project name` |
| Description | `Definition of Done` | `Definition of Done` | `Definition of Done` |
| Status | `Status` | `Status` | `Status` |
| Goals link | `1yr Goals` | *(none)* | *(none)* |
| Mountain link | *(none)* | *(none)* | `Mountains` |
| Tasks link | *(none)* | `Tasks` | `Tasks` |
| Driver | *(none)* | `Driver` | `Driver` |

### BB Projects Table (actual Projects)

BB also has a `Projects` table with different fields:

| Field | Name |
|-------|------|
| Name | `Name` |
| Description | `Project Overview` |
| Status | `Status` |
| Driver | `Driver` |
| Tasks | `Tasks` |
| Deal | `Deal` |

---

## BB Linkage Chain

BB uses a hierarchical structure different from Personal/AITB:

```
Task → Rock (7d) → Mountain (30d) → Objective (1y)
                 → Project (via separate linkage)
```

**Important:** BB tasks link to Rocks via the `Rock` field, NOT directly to Projects.
The Rock's `Project name` field is a lookup/computed value, not a direct link.

---

## Goals Table

| Base | Table | Name Field | Type |
|------|-------|------------|------|
| Personal | `1yr Goals` | `Name` | annual |
| AITB | `Objectives (1y)` | `Name` | annual |
| BB | `Objectives (1y)` | `Objective` | annual |

### Goal Hierarchy (AITB and BB)

```
Objectives (1y) → Mountains (30d) → Rocks (7d) → Tasks
```

Personal only has annual goals linked to projects.

---

## People Record IDs

### Pablo

| Base | Record ID |
|------|-----------|
| Personal | `recVET2m8HSdXH15s` |
| AITB | `recx5OwIK3J1zLsH6` |
| BB | `reczmMqbyd9EGNAL4` |

### Aaron

| Base | Record ID |
|------|-----------|
| Personal | `recqfhZKB6O5C3No1` |
| AITB | `recQcvtMt34CXBV4p` |
| BB | `recXgsS1kw8xdSFSW` |

---

## Deals Table (BB)

Table name: `Deals`

| Field | Name |
|-------|------|
| Name | `Name` |
| Status | `Status` |
| Organization | `Organization` (linked record) |
| Deal Contacts | `Deal Contacts` (linked via junction table `tblxdCIQQ7Uu0g1qS`) |
| Notes | `Notes` |
| Tags | `Tags 2` |
| Type | `Type` |

---

## Contacts & Organizations Tables

| Base | Contacts Table ID | Organizations Table ID |
|------|-------------------|----------------------|
| Personal | *(not yet mapped)* | *(none)* |
| AITB | `tbloW7bNtSGI4E3A7` | `tblPEqGDvtaJihkiP` |
| BB | `tbllWxmXIVG5wveiZ` | `tblPEqGDvtaJihkiP` |

---

## Inbox Project IDs

Used by the task router for unassigned tasks:

| Base | Inbox Project ID |
|------|-----------------|
| Personal | `recoKsIgNYclIvkn7` |
| AITB | `recxe26n7EqX8vZsm` |
| BB | *(none)* |

---

## Airtable URL Pattern

```
https://airtable.com/{base_id}/{table_id}/{record_id}
```

Example:
```
https://airtable.com/appwzoLR6BDTeSfyS/tblmQBAxcDPjajPiE/rec6YhmsGI0IsUPil
```

---

## Linked Record Structure

### Personal / AITB
```
Task
 ├── Project (linked record → Projects table)
 │    ├── Name, Description, Status
 │    └── 1yr Goals (linked record, Personal only)
 │         └── Name, Status, Priority
 ├── Assignee (linked record → People table)
 └── Sponsor Deals (AITB only, linked record → Deals table)
```

### BB
```
Task
 ├── Rock (linked record → Rocks (7d) table)
 │    ├── Project name, Definition of Done, Status
 │    └── (links up to Mountains (30d) → Objectives (1y))
 ├── Assignee (linked record → People table)
 ├── Deals (linked record → Deals table)
 │    └── Organization (linked record → Organizations table)
 └── Organization (direct link, if present)
```

---

## Filter Formula Examples

### Tasks assigned to Pablo in BB (not done)
```
AND(
  FIND('reczmMqbyd9EGNAL4', ARRAYJOIN({Assignee})),
  {Status}!='Completed',
  {Status}!='Cancelled',
  {Status}!='Human Review',
  {Status}!='Validating'
)
```

### Tasks linked to a specific Rock (BB)
```
FIND('recXXX', ARRAYJOIN({Rock}))
```

### Tasks linked to a specific Project (Personal/AITB)
```
FIND('recXXX', ARRAYJOIN({Project}))
```

### Text search in title
```
FIND(LOWER('search term'), LOWER({Task}))
```

### Tasks due this week
```
AND(
  IS_BEFORE({Deadline}, DATEADD(TODAY(), 7, 'days')),
  IS_AFTER({Deadline}, DATEADD(TODAY(), -1, 'days'))
)
```
