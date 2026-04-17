# Campaign Plan Template

16-section structure for all Brain Bridge GTM campaigns. Every field must contain real data when the plan is finalized. No placeholder brackets allowed.

---

## Section 1 — Campaign Overview

| Field | Value |
|-------|-------|
| Campaign Name | |
| Owner | |
| Source | BB Campaign |
| Status | Drafting |
| Type | Dynamic or Static |
| Launch Date | |
| Thesis | (one sentence: who, why now, what outcome) |
| Primary Objective | |
| Secondary Objective | |
| Learning Goal | |

---

## Section 2 — Target Audience

**ICP Table**

| Dimension | Value |
|-----------|-------|
| Industries | |
| Job Titles | |
| Seniority Levels | |
| Company Size | |
| Geography | |
| ICP Confidence Score | 0–5 |

**Stress Signals**

Observable Events (visible, external triggers):
-

Data Signals (metrics or internal indicators):
-

**Hard Disqualifiers**
-

**Lead Filters (Apollo Parameters)**

| Filter | Value |
|--------|-------|
| Titles | |
| Industries | |
| Headcount range | |
| Geography | |
| Keywords | |

**Estimated Lead Volume:**

---

## Section 3 — Buying Trigger Hypothesis

**Hypothesis Statement:**
(One sentence: "We believe [prospect type] experiences [trigger event], which creates urgency to [desired action].")

**Assumptions Being Tested:**
1.
2.
3.

---

## Section 4 — Qualification Approach

See `qualification-frameworks.md` for full framework definitions.

**Framework Progression**

| Stage | Framework | Gate |
|-------|-----------|------|
| Initial qualification | F.L.O.O.R. at 40% | Owns Execution confirmed |
| Deeper qualification | F.L.O.O.R. at 60% | Double-O confirmed |
| Full qualification | B.A.N.T. at 100% | All four confirmed |

**Hard Gates**
- 40%: Prospect must own execution (not just influence)
- 60%: Both Ownership and Ops Bandwidth confirmed
- 100%: All B.A.N.T. criteria met

**Campaign-Specific Notes:**
(Any qualification overrides or additions specific to this campaign)

---

## Section 5 — Research & Insights

**Context Sources**
-

**Confirmed ICP Language**
(Exact phrases prospects use — sourced from interviews, reviews, forums, or transcripts)
-

---

## Section 6 — Messaging Strategy

**Value Proposition:**
(One sentence from the buyer's perspective: "For [prospect], [product] delivers [outcome] by [mechanism].")

**Competitive Framing:**
(How to position vs. alternatives including "do nothing")

**Core Messaging Themes (2–3):**
1.
2.
3.

**Key Talking Points:**
-
-
-

**Tone & Style:**
(Choose: professional / warm / direct / consultative / peer-to-peer)

---

## Section 7 — Message Guardrails

> This section is duplicated into the Campaign record's "Message Guardrails" field in Airtable.

**Content Constraints**

| Constraint | Value |
|------------|-------|
| Word count per message | 75–100 words |
| Questions per message | 1 max |
| Subject line length | 3–5 words |
| Paragraphs per message | 2–3 max |

**Disallowed Phrases:**
-

**Disallowed Patterns:**
-

**Required Elements:**
-

**Plain Text Constraints:**
All emails must render correctly in plain text. No HTML formatting, no bullet lists in cold email body, no embedded images.

---

## Section 8 — Engagement Flow

**Sequence Structure**

| Step | Day | Channel | Content Strategy | CTA |
|------|-----|---------|-----------------|-----|
| 1 | 1 | Email | | |
| 2 | 3 | LinkedIn | | |
| 3 | 5 | Email | | |
| 4 | 8 | Phone | | |
| 5 | 12 | Email | | |

See `engagement-patterns.md` for default sequence structure.

**Pre-Outreach Research Requirements:**
Before Touch 1, look up:
-

**CTA Progression:**
(How the ask evolves across the sequence — from soft to direct)

---

## Section 9 — Artifact & Case Study Usage Rules

**Matching Criteria:** Deploy an artifact when 2 of the following 3 match:
1. Industry match
2. Problem match
3. Company size match

**Available Artifacts**

| Artifact | Type | Best For |
|----------|------|---------|
| | | |

---

## Section 10 — Flexibility Rules

**Flexibility by Category**

| Category | Level | Notes |
|----------|-------|-------|
| Messaging | Tight / Moderate / Loose | |
| Timing | Tight / Moderate / Loose | |
| CTA | Tight / Moderate / Loose | |
| Artifacts | Tight / Moderate / Loose | |
| Tone | Tight / Moderate / Loose | |
| Reply Handling | Tight / Moderate / Loose | |
| Qualification | Tight / Moderate / Loose | |
| Sequence Length | Tight / Moderate / Loose | |
| Channel Order | Tight / Moderate / Loose | |
| Personalization Depth | Tight / Moderate / Loose | |

**Hard Constraints:**
(Things Claude must never change regardless of flexibility level)

**Triggers for Plan Update:**
(Conditions that require returning to the plan and revising — e.g., "If reply rate < 5% after 20 sends")

---

## Section 11 — Sender Configuration

| Channel | Sender Name | Identity |
|---------|-------------|---------|
| Email | | address |
| LinkedIn | | profile URL |
| Phone | | number or N/A |

---

## Section 12 — System Default Overrides

List any overrides to system-wide defaults. If none: "No overrides — System Defaults apply."

| Setting | Default | Override |
|---------|---------|---------|
| | | |

---

## Section 13 — Campaign Timing

| Parameter | Value |
|-----------|-------|
| Send Days | Mon–Thu (default) |
| Holidays to Skip | |
| Send Window | 8am–5pm recipient local time (default) |
| Timezone Source | Prospect's location |
| Minimum Touch Spacing | 2 business days (default) |

---

## Section 14 — Success Criteria & Stop Rules

**Success Definition**

| Outcome | Pipeline Stage |
|---------|---------------|
| | |

**Stop Rules**

| Condition | Action |
|-----------|--------|
| Full sequence completed, no reply | Disengage |
| Explicit decline | Disengage immediately |
| DNC or unsubscribe request | Disengage, flag record |
| Hostile reply | Escalate to owner, do not respond |

**Metrics Targets**

| Metric | Target |
|--------|--------|
| Response rate | 20% (default) |
| Meeting rate | 10% (default) |
| Qualified opportunities | 1+ (default) |

---

## Section 15 — Reply Handling Strategy

**Reply Type Strategy**

| Reply Type | Strategy | Authority Level |
|------------|----------|----------------|
| Interest | Advance qualification, propose meeting | Level A |
| Objection | Acknowledge, explore concern before responding | Level B |
| Confusion | Clarify relevance in 4 sentences or fewer | Level A |
| Hostile | Do not respond, escalate to owner | Level D |
| Out-of-Office | Pause sequence, resume on return date | Level S |

See `engagement-patterns.md` for authority level definitions.

**Common Objections & Responses**

| Objection | Suggested Response |
|-----------|-------------------|
| | |
| | |

---

## Section 16 — Post-Campaign Review Plan

**Metrics to Track**

| Metric | Source | Frequency |
|--------|--------|-----------|
| Reply rate | Airtable | Weekly |
| Meeting rate | Airtable | Weekly |
| Deals created | Airtable | End of campaign |
| Message that got the most replies | Airtable | End of campaign |

**Learning Questions:**
1. Did the buying trigger hypothesis hold?
2. Which messaging theme drove the most engagement?
3. What did we learn about the ICP that we didn't know before?

**Evidence-Based Change:**
(What would cause us to update the Campaign Plan mid-run?)

---

## Pipeline Compatibility Contract

This campaign plan is compatible with the Outreach Planner. The Outreach Planner reads:
- Section 7 (Message Guardrails) from the Campaign record "Message Guardrails" field
- Section 8 (Engagement Flow) for sequence structure
- Section 10 (Flexibility Rules) to determine what it can adapt
- Section 15 (Reply Handling) to determine how to respond to inbound replies

The Outreach Planner creates one outreach plan per Deal. It does not modify the Campaign Plan.

---

## Validation Checklist

Before submitting for approval in Stage 3, verify:

- [ ] All 16 sections contain real data (no placeholder brackets)
- [ ] Thesis is one sentence with who, why now, and outcome
- [ ] Apollo filter parameters are specific enough to return a bounded list
- [ ] Sequence structure has a step for each touch with day, channel, and CTA
- [ ] Reply handling covers all 5 reply types
- [ ] Message Guardrails section duplicated to Campaign record field
- [ ] Success criteria mapped to a pipeline stage
- [ ] Disengagement rules cover all 4 stop conditions
- [ ] Sender identity confirmed for each active channel
