# Authority Matrix

Defines how each planned action gets assigned — who does it, what status it starts at, and whether human approval is required before execution.

---

## Authority Levels

| Level | Name | Task Status | Assignee | Review Required | Use When |
|-------|------|-------------|----------|-----------------|----------|
| A | Autonomous | Not Started | Executor | No | Standard outreach per campaign plan, no deviations |
| B | Autonomous + Notify | Not Started | Executor | No (notify only) | Actions the owner should know about but need not approve |
| C | Propose and Wait | Human Review | Owner | Yes, before execution | Deviations from plan, sensitive topics, escalations |
| D | Assign to Human | Not Started | Owner | N/A — human executes | Personal calls, executive outreach, relationship-sensitive actions |
| S | System/Automation | N/A | N/A | N/A | Automated triggers — no task created |

**Level C task names must be prefixed with `"Review: "`.**

---

## Default Authority by Action Type

| Action Type | Default Level | Notes |
|-------------|---------------|-------|
| First cold email | A | Standard campaign touch |
| Follow-up email (in sequence) | A | Per campaign plan |
| LinkedIn connection request | A | Standard prospecting |
| LinkedIn message (in sequence) | A | Per campaign plan |
| Phone call (non-executive) | C | Requires talking points approval |
| Phone call (executive / C-suite contact) | D | Human executes |
| Custom / off-script message | C | Any deviation from template |
| Response to objection | B | Notify owner; executor handles |
| Meeting scheduling | B | Notify owner; executor handles |
| Pricing discussion | C | Requires approval |
| Contract or legal topics | D | Human handles directly |
| Human Communication (to owner) | D | Always assigned to owner, never executor |
| Research task | A | Standard information gathering |

---

## Conservative Fallback

If the campaign plan is unavailable, system defaults are missing, or the correct authority level is unclear:

**Default ALL tasks to Level C (Propose and Wait).**

This prevents autonomous execution of actions that haven't been reviewed. Never assume a lower authority level when in doubt.

---

## Escalation Rules

Escalate the default authority level by one step when any of the following apply:

| Trigger | Escalation |
|---------|-----------|
| Contact is C-suite (CEO, CTO, CFO, etc.) | Escalate all actions one level (A→B, B→C, C→D) |
| Contact has previously expressed concern or frustration | Escalate to at least Level C |
| Deal value is above the configured threshold | Escalate to at least Level C |
| First contact with a new stakeholder | Minimum Level C |
| Action deviates from the campaign plan | Minimum Level C |
| Contact is a referral from a known relationship | Minimum Level B |

When multiple triggers apply, use the highest resulting level.

---

## Human Communication Tasks

Human Communication tasks (messages to the deal owner) are always:
- **Authority Level D** — assigned to the deal owner
- **Never assigned to the executor**
- Created whenever the executor needs the owner to know something, decide something, or take an action themselves

Types of Human Communication tasks:

| Type | When to Use |
|------|-------------|
| question | Executor needs information or clarification before proceeding |
| recommendation | Executor has a suggestion for the owner to consider |
| authority_request | Executor needs explicit approval before executing a Level C action (use when the Level C task itself isn't sufficient) |
| blocker | Something is preventing progress; owner must resolve it |
