---
name: planning-outreach
description: Create and manage per-deal outreach plans for Brain Bridge deals. Use when asked to plan outreach, update an outreach plan, manage outreach tasks, or process research into a deal's contact and org records.
---

# Planning Outreach (BB)

Creates and manages structured, per-deal outreach plans using Airtable as the system of record. Reference-only skill — no scripts. All actions use MCP Airtable tools directly.

---

## Workflow Overview

| Step | Name | Purpose |
|------|------|---------|
| 0 | Enrich Records | Process completed research tasks → update Airtable records |
| 1 | Create/Update Outreach Plan | Read deal context → write 8-section plan into Deal record |
| 2 | Manage Tasks | Archive obsolete tasks → create new action tasks |

Always run steps in order. If a step produces no work (e.g., no completed research tasks), skip it and move on.

---

## Step 0: Enrich Records from Research

Before planning, scan for completed Research tasks on the deal and extract any structured data from their outputs.

**What to extract:**
- Contact: name, title, email, phone, LinkedIn URL
- Organization: industry, size, location, website, tech stack signals
- Any referrals or new stakeholder names

**Update rules:**
- Update Contact, Organization, or Deal records in Airtable with extracted data
- Only ADD or UPDATE — never DELETE existing values
- If new data conflicts with existing data, keep the existing value and note the discrepancy
- NEVER update "Do Not Contact", "Do Not Email", opt-out, or compliance-related fields under any circumstances
- After processing, append the following marker to the Task Output field of each processed task:

```
--- PLANNER ENRICHMENT ---
Processed: <date>
Fields updated: <list of field names updated>
```

---

## Step 1: Create/Update Outreach Plan

### 1a. Gather Context

Retrieve all of the following before writing or updating the plan:

| What | Why |
|------|-----|
| Deal record (incl. current outreach plan field, stakeholder map, qualification signals) | Core context |
| Primary contact + all stakeholders (email, phone, LinkedIn) | Personalization and multi-threading |
| Organization record | Company context |
| Campaign record + campaign plan (if deal is part of a campaign) | Guardrails and sequence |
| Activity log / communication history | What has already happened |
| Existing tasks (pending and in-progress) | Avoid duplication |
| Completed task outputs | Responses received, research results |

### 1b. Classify Any Inbound Responses FIRST

Before writing a single line of the plan, classify all responses found in activity logs or task outputs:

| Classification | Indicators | Required Action |
|----------------|-----------|-----------------|
| Rejection / Opt-Out | "not interested", "remove me", "unsubscribe", DNC request | Mark deal DISENGAGED, archive ALL outreach tasks, create ZERO new tasks |
| Out-of-Office | Auto-reply with return date | Set ALL future task due dates to return date or later |
| Timing Constraint | "reach out in Q2", "call me in 3 months" | Set due dates to stated timeframe — do not use default sequence timing |
| Objection | Pushback on value, timing, relevance | Record specifics in Blockers section; tailor follow-ups to address objection |
| Positive / Neutral | Questions, info requests, agreed to meeting | Create appropriate follow-up tasks |
| Hostile | Angry, threatening | Do NOT respond; escalate to owner immediately; archive all outreach tasks |

See `references/reply-handling.md` for full classification guidance and objection handling patterns.

### 1c. Write the 8-Section Outreach Plan

Write the plan into the Deal's Outreach Plan field. When updating an existing plan, PRESERVE all historical entries — append new content; never overwrite previous sections.

See `references/outreach-plan-template.md` for field-by-field templates and examples.

**Required sections:**

1. **Deal Snapshot** — current state, stage, primary contact, org, campaign, key signals
2. **Research & Personalization Context** — what is known about the contact and org
3. **Outreach State** — touch number, last action, last response, days since contact
4. **Forward Plan** — next 1–3 actions with channel, timing, content strategy, authority level
5. **Conditional Forward Planning** — if/then scenarios for likely responses
6. **Plan Deviations Log** — changes from campaign plan with date and reason
7. **Qualification Tracker** — F.L.O.O.R. and B.A.N.T. progress with evidence
8. **HITL Communication Log** — human-in-the-loop interactions, questions, approvals

---

## Step 2: Manage Tasks

### 2a. Archive Obsolete Tasks

Before creating any new tasks, archive tasks that are:
- Superseded by the new plan
- Blocked by a response (e.g., rejection, OOO, hostile)
- Duplicates of tasks being created

Set archived tasks to Status = "Archived" with a note explaining why.

### 2b. Create New Tasks

Create up to **3 new action tasks** per planning cycle. Each task must:
- Align with the campaign's guardrails
- Have a future due date (minimum 1–2 days out)
- Include authority level metadata
- Include a complete Definition of Done

**Task Types:**

| Type | Channel | Notes |
|------|---------|-------|
| Send Email | Email | Include full From/To/Subject/Body |
| LinkedIn Message | LinkedIn | Include profile URL and full message |
| Phone Call | Phone | Include talking points |
| Research | N/A | Specific research question to answer |
| Human Communication | Owner message | ALWAYS assigned to deal owner, never executor |

**Authority Levels — determine assignee and status:**

See `references/authority-matrix.md` for full matrix and escalation rules.

| Level | Status | Assignee | Use When |
|-------|--------|----------|----------|
| A | Not Started | Executor | Standard outreach per campaign plan |
| B | Not Started | Executor | Actions owner should know about (notify only) |
| C | Human Review | Owner | Deviations, sensitive topics — must approve before execution |
| D | Not Started | Owner | Human executes directly (calls, executive outreach) |

**Conservative fallback:** If campaign plan or system defaults are unavailable, assign ALL tasks Level C.

**Level C task names** must be prefixed with `"Review: "`.

### 2c. Task Format

**Required metadata in Task Notes (JSON block):**
```json
{"plan_version": 1, "campaign": "Campaign Name", "touch_number": 1, "authority_level": "A"}
```

**Definition of Done by task type:**

For Send Email:
```
From: <sender_email> (<sender_name>, <sender_title>)
To: <contact email>
Subject: <subject line>

Body:
<full email body>
```

For LinkedIn Message:
```
To: <contact name>
Profile: <contact linkedin_url>

Message:
<full message content>
```

For Phone Call:
```
To: <contact name>
Phone: <contact phone>

Talking Points:
- <point 1>
- <point 2>
- <point 3>
```

For Human Communication:
```
To: <owner name>
Type: <question | recommendation | authority_request | blocker>

Message:
<clear description of what the owner needs to know or decide>
```

---

## Hard Rules

| Rule | Detail |
|------|--------|
| Rejection = stop | Contact rejected → archive everything, create zero outreach tasks |
| Hostile = escalate | Hostile response → immediate stop, Human Communication task to owner |
| OOO = adjust all dates | Every task due date must fall after the stated return date |
| Never touch compliance fields | Do Not Contact, Do Not Email, opt-out fields are read-only |
| Max 3 tasks per cycle | Never create more than 3 action tasks in a single planning run |
| Preserve history | When updating a plan, append — never overwrite existing sections |
| All tasks need authority level | Every task must have authority level metadata and a Definition of Done |
| Campaign compliance required | Every action must be checked against campaign guardrails before creating |
| Conservative fallback | Missing defaults → all tasks default to Level C |

---

## References

- `references/outreach-plan-template.md` — full 8-section template with field descriptions and examples
- `references/authority-matrix.md` — authority level definitions, defaults by action type, escalation rules
- `references/reply-handling.md` — response classification, disengagement rules, objection handling patterns
