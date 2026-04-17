---
name: creating-campaigns
description: Interactive 5-stage workflow for creating GTM campaigns. Guides through Campaign Plan authoring, Apollo lead discovery, Airtable record creation, contact enrichment, and launch approval. Reference-only — no scripts.
---

# Creating Campaigns

Interactive workflow to build a Campaign Plan and populate Airtable and Apollo records. Five stages run in strict order. Never skip stages. Never enrich contacts before Stage 4.

---

## Overview

| Stage | Name | Gate |
|-------|------|------|
| 1 | Campaign Planning | Conversational (7 steps) |
| 2 | Lead Discovery | User confirms lead count |
| 3 | Plan Review & Approval | Explicit approval required |
| 4 | Record Creation | Atomic batch, no interruptions |
| 5 | Launch Approval | Explicit launch confirmation |

---

## Stage 1: Campaign Planning

Gather all data needed to populate the 16-section Campaign Plan. Work conversationally — group 2–4 related questions per exchange. Present smart defaults wherever possible. Do not ask open-ended questions when a sensible default exists.

Target 5–8 exchanges total across all 7 steps.

### Step 1.1 — Campaign Foundation & Thesis

Gather:
- Campaign name
- Campaign type: **Dynamic** (evolves with feedback) or **Static** (fixed sequence)
- Campaign thesis (one sentence: who, why now, what outcome)
- Primary objective (e.g., "Book 5 discovery calls")
- Secondary objective (e.g., "Learn what messaging resonates")
- Learning goal (one hypothesis to validate)
- Owner (default: Aaron Eden)
- Source (default: "BB Campaign")
- Status (default: "Drafting")

### Step 1.2 — Target Audience & ICP Definition

Gather:
- Industries (list)
- Job titles (list)
- Seniority levels (e.g., Director, VP, C-Suite)
- Company size range (employees or revenue band)
- Geographic focus (default: North America)
- ICP confidence score: 0 (untested) to 5 (validated)
- Stress signals — split into two types:
  - **Observable Events**: things you can see happening (hiring, funding, reorg)
  - **Data Signals**: metrics that indicate pain (churn rate, NPS drop)
- Hard disqualifiers (criteria that immediately exclude a lead)
- Apollo filter proposal: translate ICP into Apollo search parameters (titles, industries, headcount, geography, keywords)

### Step 1.3 — Buying Trigger, Research & Messaging

Gather:
- Buying trigger hypothesis (what event or condition makes now the right time)
- Assumptions being tested (2–3 falsifiable statements)
- Research context sources (LinkedIn, news, job postings, press releases)
- Confirmed ICP language: exact phrases real prospects use (not marketing speak)
- Value proposition (one sentence from the buyer's perspective)
- Competitive framing (how to position vs. alternatives, including "do nothing")
- Core messaging themes (2–3 topics the sequence will rotate through)
- Key talking points (3–5 bullets)
- Tone & style: choose from professional / warm / direct / consultative / peer-to-peer

### Step 1.4 — Engagement Flow, Artifacts & Reply Handling

Gather:
- Sequence structure (use the default in `references/engagement-patterns.md` as a starting point; confirm or modify)
- Pre-outreach research requirements (what to look up before Touch 1)
- Available artifacts: case studies, white papers, social proof to deploy mid-sequence
- Reply handling — confirm or override the four defaults:
  - **Interest**: advance qualification, propose meeting
  - **Objection**: acknowledge, explore concern before responding
  - **Confusion**: clarify relevance in 4 sentences or fewer
  - **Hostile**: do not respond, escalate to owner
  - **Out-of-Office**: pause sequence, resume on return date
- Expected objections (2–3 most likely with suggested responses)

### Step 1.5 — Guardrails & Constraints

Present defaults and ask the user to confirm or override:

| Constraint | Default |
|------------|---------|
| Word count per message | 75–100 words |
| Questions per message | 1 max |
| Subject line length | 3–5 words |
| Paragraphs per message | 2–3 max |

Also gather:
- Disallowed phrases (e.g., "synergy", "circle back", "just checking in")
- Disallowed patterns (e.g., no bullet lists in cold email body)
- Required elements (e.g., always personalize with a company-specific observation)
- Plain text constraint: confirm emails must render in plain text with no formatting

### Step 1.6 — Success Criteria, Stop Rules & Review Goals

Gather:
- Success definition mapped to pipeline stage (e.g., "Success = Deal moves to Discovery")
- Maximum touches before disengagement
- Disengagement triggers:
  - Full sequence completed, no reply
  - Explicit decline
  - DNC or unsubscribe request
  - Hostile reply
- Metrics targets (defaults: 20% response rate, 10% meeting rate, 1+ qualified opportunity)
- Post-campaign review questions (what will we learn regardless of outcome?)

### Step 1.7 — Flexibility, Sender, Overrides & Timing

Gather:
- Flexibility level per category: **Tight** (no deviation) / **Moderate** (minor changes OK) / **Loose** (Claude can adapt)
  - Categories: messaging, timing, CTA, artifacts, tone, reply handling, qualification, sequence length, channel order, personalization depth
- Email sender identity (name, email address)
- LinkedIn sender identity (name, profile URL)
- Phone sender identity (name, number) — or "N/A"
- Campaign timing:
  - Send days (default: Mon–Thu)
  - Holidays to skip
  - Send window (default: 8am–5pm recipient local time)
  - Minimum spacing between touches (default: 2 business days)

---

## Stage 2: Lead Discovery

Use Apollo MCP tools to search for matching leads.

**Rules:**
- Search only. No enrichment in this stage.
- Do not call any Apollo enrichment endpoint.

**Steps:**
1. Translate the ICP and Apollo filter proposal from Step 1.2 into an Apollo people search.
2. Preview a sample of contacts (name, title, company, location) — show 5–10 rows.
3. Report total lead count from the search.
4. Estimate enrichment credit cost if the user elects full enrichment in Stage 4:
   - Email enrichment: ~1 credit per contact
   - Phone enrichment: ~2–3 credits per contact
5. Ask the user to choose: **Proceed / Refine filters / Cancel**

If the user wants to refine, loop back into the Apollo filter parameters and re-search. Do not advance to Stage 3 until the user explicitly chooses "Proceed".

---

## Stage 3: Plan Review & Approval Gate

Before creating any records, present the complete Campaign Plan and get explicit approval.

**Steps:**
1. Check Airtable for existing Organization and Contact records that match the lead list (deduplication check). Report any found.
2. Present the full Campaign Plan using the structure in `references/campaign-plan-template.md`. Every section must contain real data — no placeholder brackets.
3. Present the execution plan:
   - Number of Organization records to create
   - Number of Contact records to create
   - Number of Deal records to create
   - Enrichment options selected
4. Ask the user about enrichment:
   - Email enrichment? (yes/no)
   - Phone enrichment? (yes/no)
   - Phone reveal (mobile)? (yes/no, higher credit cost)
5. State the total estimated credit cost.

**MANDATORY APPROVAL GATE:**
Do not proceed to Stage 4 until the user responds with an explicit approval: "yes", "approved", "go ahead", or equivalent. If the user asks for changes, return to the relevant planning step, update the plan, and re-present Stage 3.

---

## Stage 4: Record Creation

Run as a single atomic batch. Do not pause for confirmations between steps. Do not ask questions mid-batch.

**Execution order:**
1. Create the Campaign record in Airtable:
   - Embed the full 16-section Campaign Plan in the Campaign record body
   - Set "Message Guardrails" field to the Section 7 content
   - Set Status = "Drafting"
2. For each lead:
   a. Create or find Organization record
   b. Create Contact record linked to Organization
   c. Create Deal record linked to Contact and Campaign
3. If email enrichment was approved: enrich all contacts via Apollo
4. If phone enrichment was approved: enrich all contacts via Apollo
5. Evaluate quality gate: if fewer than 80% of records created successfully, halt and report before proceeding.

**Report after batch completes:**
- X/Y Organizations created (Z already existed)
- X/Y Contacts created
- X/Y Deals created
- Enrichment: X/Y emails found, X/Y phones found
- Errors (if any): list with reason

---

## Stage 5: Launch Approval

Present a final pre-launch summary:
- Campaign name and thesis
- Plan summary (one sentence per section)
- Records created (totals from Stage 4)
- Enrichment results
- Any errors or gaps

Explain what happens when the campaign launches:
- Campaign status changes from "Drafting" to "In Progress"
- All associated Deals are flagged for outreach planning
- Outreach Planner reads the Campaign Plan and creates per-deal outreach plans following the sequence, guardrails, and flexibility rules defined here

Ask for explicit launch confirmation. If the user confirms, update the Campaign record Status to "In Progress". If the user wants to adjust anything, return to the relevant stage.

---

## Rules

1. **Never enrich in Stage 2.** Apollo search is preview-only. Enrichment happens in Stage 4 only, and only if the user approved it in Stage 3.
2. **No placeholder brackets.** Every field in the Campaign Plan must contain real data or an explicit stated default. Never output `[TBD]` or `[Insert X here]`.
3. **Stage 4 is atomic.** Run the full record creation batch without stopping for confirmations. Only halt if the 80% quality gate fails.
4. **Smart defaults over open questions.** Propose a value and ask the user to confirm or override rather than asking an open-ended question.
5. **Group 2–4 related questions per exchange** during Stage 1. Do not ask one question at a time.
6. **Mandatory approval gate** before Stage 4. Do not create records without explicit user approval.
7. **Deduplication before creation.** Always check for existing Airtable records before creating new ones in Stage 4.

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/campaign-plan-template.md` | Full 16-section Campaign Plan template with field definitions |
| `references/qualification-frameworks.md` | F.L.O.O.R. and B.A.N.T. frameworks with progression defaults |
| `references/engagement-patterns.md` | Sequence defaults, reply handling, authority levels, content constraints |
