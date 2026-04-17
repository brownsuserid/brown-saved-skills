# Generating Pitch Decks & Proposals

> Output: Gamma slide deck (Google Drive) or Google Docs proposal
> Cadence: **On-demand**

## Overview

Pulls full deal context from Airtable, meeting transcripts, and email history, then generates sales pitch decks via Gamma or structured proposals via Google Docs. Always presents an outline for approval before generating.

**Use cases:**
- "Create a pitch deck for Radiant Nuclear"
- "Generate a scope of work for the Cetera Investments deal"
- "Draft a partnership proposal for BCS"
- "Create workshop overview slides"
- "Write a case study for Intuit SPEED"

---

## Phase 1: Gather Deal Context

Run the context script to pull everything known about the deal:

```bash
python3 scripts/gather_deal_context.py \
  --deal "Radiant Nuclear"

# Or by record ID:
python3 ... --deal-id recPujEjs4Ntc6rok
```

**Pulls from BB Deals (tblw6rTtN2QJCrOqf):**
- Deal name, status, type, description
- Pain points and stakeholder map
- Primary contact (name, email, title)
- Organization (name, website, industry)
- Linked Airtable notes (most recent 5)

**Also searches Google Drive for meeting transcripts:**
```bash
gog drive search "{org_name} OR {contact_name}" --account aaron@brainbridge.app --max 10 --json
```

Read each relevant transcript via `gog docs cat {fileId} --account aaron@brainbridge.app` to extract:
- Key pain points mentioned
- Solutions discussed
- Pricing or timeline references
- Decision makers identified

**Output JSON:**
```json
{
  "deal": { "id": "recXXX", "name": "Radiant Nuclear", "status": "Demo/Inspiration Session", ... },
  "contact": { "name": "Dom Nguyen", "title": "CTO", "email": "dom@..." },
  "organization": { "name": "Radiant Nuclear", "industry": "Energy", ... },
  "airtable_notes": [ { "title": "Initial Discovery Call - 2026-01-15", ... } ],
  "transcript_snippets": [ { "file": "Radiant Nuclear - Discovery", "key_points": [...] } ]
}
```

---

## Phase 2: Select Template and Present Outline

Match the request to the appropriate template:

| Request type | Template | Format | Length |
|-------------|----------|--------|--------|
| Sales pitch / new customer | `sales-pitch` | Gamma slides | 10–12 slides |
| Partnership proposal | `partnership-proposal` | Gamma slides | 8–10 slides |
| Case study | `case-study` | Gamma slides | 6–8 slides |
| Workshop overview | `workshop-overview` | Gamma slides | 5–7 slides |
| Scope of work / SOW | `scope-of-work` | Google Doc | 3–5 pages |
| Pricing proposal | `pricing-proposal` | Google Doc | 2–3 pages |

**APPROVAL GATE:** Present the template choice and a detailed outline (slide-by-slide or section-by-section) using context from Phase 1. Include customer-specific talking points in the outline. Do NOT generate content until Aaron approves the outline.

**Example outline for sales pitch:**
```
Slide 1: Title, "BrainBridge for Radiant Nuclear"
Slide 2: Problem, Manual processes, slow knowledge transfer in nuclear ops
Slide 3: Solution, AI-powered workflow automation + knowledge management
Slide 4: How It Works, 3-step diagram: Connect → Automate → Learn
Slide 5: Case Study, Intuit SPEED: 40% cycle time reduction
Slide 6: For Radiant, Specific to Dom's pain points (from Jan 15 call)
Slide 7: Pricing, [ask Aaron for current pricing before populating]
Slide 8: Team, Aaron Eden, BrainBridge background
Slide 9: Next Steps, Pilot program, 30-day timeline
```

---

## Phase 3: Generate Content

### Slide Decks → Gamma

Use `using-gamma` skill to generate the deck:

```bash
# Via Gamma web interface or API:
# 1. Prepare structured content prompt from approved outline + context
# 2. Open Gamma at gamma.app with aaron@brainbridge.app account
# 3. New AI-generated presentation → paste structured prompt
# 4. Apply BrainBridge theme
# 5. Export PDF for sharing
```

Include in the Gamma prompt:
- Customer name and industry
- Specific pain points from transcripts
- Approved outline structure
- Customer-specific language (match their vocabulary from transcripts)

### Proposals / SOW → Google Docs

Run the proposal script:

```bash
python3 scripts/generate_proposal.py \
  --context-file context.json \
  --template scope-of-work \
  --deal-id recXXXXX
```

This creates a Google Doc at `aaron@brainbridge.app` with:
- Executive summary using deal context
- Scope section from template + customized with deal notes
- Pricing placeholder table (Aaron fills in actual numbers)
- Timeline based on discussed milestones
- Standard terms and conditions block
- "DRAFT, For Review" header

---

## Phase 4: Deliver and Track

After generating:

1. **Share the Google Drive link** with Aaron for review
2. **Create BB task:** "Review and send {deck_name} to {contact_name}"
3. **Update deal notes:** Add note with link to generated deck/proposal
4. **Ask Aaron:** any additional team members to share with?

---

## Templates

Templates live at:
```
managing-finances/templates/pitch-decks/
  sales-pitch.md
  partnership-proposal.md
  case-study.md
  workshop-overview.md
  scope-of-work.md
  pricing-proposal.md
```

Each template defines: slide count, section headings, guiding questions per section, and standard language blocks.

---

## Airtable Schema

### BB Deals (tblw6rTtN2QJCrOqf)

| Field | Used for |
|-------|---------|
| Name | Deck title, file naming |
| Status | Context for urgency/stage |
| Type | Template selection hint |
| Description | Executive summary input |
| Pain Points | Problem slide content |
| Stakeholder Map | Decision maker identification |
| Organization | Company name for deck |
| Deal Contacts | Recipient name, personalization (via junction table) |
| Notes | Meeting summaries |

---

## Guardrails

- **Never send decks automatically**, always create in Drive/Gamma for review first
- **Always present outline for approval**, never generate full content from Phase 1 data alone
- **No confidential pricing from other deals**, pricing must be explicitly provided by Aaron
- **DRAFT watermark**, always note "DRAFT" in filename and doc header until Aaron approves
- **Insufficient context**, if < 2 sources found for a deal, flag and ask Aaron to provide context before generating
- **Blocked deals**, check deal status; skip if Closed Won/Lost

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `gather_deal_context.py` | Pull deal, contact, org, notes, and transcript snippets from BB + Google Drive |
| `generate_proposal.py` | Create Google Doc proposal from template + deal context |

---

## Integration

- **Trigger:** On-demand
- **Bases:** BB (primary), AITB (sponsor deals/case studies)
- **Depends on:** `using-gamma` (slide decks), `using-gog` (Docs/Drive), `../airtable-config/airtable_config.py`, `AIRTABLE_TOKEN`
