# Associate Deals with Campaigns

Associates orphaned BB deals with the appropriate GTM campaigns using LLM reasoning over enriched deal and campaign context.

## When to Use

- Deals exist in BB CRM without a campaign
- After bulk deal imports or manual deal creation
- Periodic cleanup to ensure all deals are campaign-attributed

## Workflow

### Phase A: Campaign Review & Cleanup (Do First)

Before matching deals, ensure the campaign list is clean and well-documented. Bad campaign data produces bad matches.

#### A1. Audit Campaign Descriptions

Pull all active campaigns and check for missing descriptions, target audience, and campaign plans. Flag any that are empty or sparse.

#### A2. Consolidate Duplicates

Look for campaigns that are fragments of the same effort (e.g., separate records for LinkedIn vs Email variants of one campaign). Consolidate:
1. Pick the primary record (the one with deals)
2. Move any child deals from duplicates to the primary
3. Archive the duplicates

#### A3. Add Missing Descriptions

For campaigns without descriptions, sample their linked deals to understand what the campaign was. Draft descriptions for operator approval. Include:
- What the campaign targets (ICP)
- How leads were sourced (channel: LinkedIn, email, event, referral)
- What messaging/content was used
- Current status

#### A4. Scan for Missing Campaigns

Search Google Drive (`gog drive search` on BB account) for campaign documentation that may not have Airtable records:
- Search: "outreach campaign", "ICP campaign", "GTM campaign", "LinkedIn Helper", "Apollo campaign", "cold outreach", "workshop campaign"
- Read promising docs for campaign names, ICPs, and outreach details
- Cross-reference against existing Airtable campaigns
- Create any missing campaigns with proper descriptions

#### A5. Verify Referral Campaigns

Ensure each referral source (external person who introduces deals) has a campaign record with a description of who they are and what types of deals they refer.

### Phase B: Prepare Data

```bash
python3 associate_deals.py \
  --assignee aaron > /tmp/deal_campaign_data.json
```

Fetches the operator's orphaned deals, enriches each with org, contacts, activity logs (3 earliest + 3 most recent with full content), tags, outreach plan. Fetches all campaigns with full context (plan, target audience, campaign code, message guardrails, started/ended). Outputs batched JSON (5 deals per batch).

### Phase C: Route Deals (LLM Subagents, Batch by Batch)

Process ONE batch at a time. Present results for operator approval before moving to the next batch.

For each batch, spawn a subagent with the batch's deals + full campaign list.

**Subagent prompt:**
```
You are routing BB CRM deals to the correct GTM campaign. Read the deals and campaigns provided.

For each deal, review ALL context and recommend the best campaign match. Pay special attention to:

- **Activity log content**: The actual text of outreach messages and the TYPE of activity (LinkedIn Connected, Email Sent, etc.) are the strongest signals. Explicit campaign mentions ("Campaign: X", "Connected via X") are near-certain attribution.
- **First touches**: The earliest activity logs reveal where the deal originated. Later activity is follow-up.
- **Deal type**: Partner->partner campaigns, speaking->event campaigns, etc.
- **Creation date**: Deals created on the same day were likely batch-imported from one effort.
- **Campaign code/plan/target audience**: Read these to understand what each campaign covers.

Rules:
- An employee sending outreach emails does NOT mean they referred the deal.
- "Referral" campaigns mean someone OUTSIDE the company introduced the deal.
- If activity logs explicitly name a campaign, that's near-certain attribution.

For EVERY deal, include org name, contact name(s), and a brief summary of the key context you considered (activity log excerpts, creation date, deal type). The operator needs this detail to approve or adjust.

For each deal output JSON:
{
  "deal_id": "recXXX",
  "deal_name": "...",
  "org": "...",
  "contacts": "...",
  "context_summary": "brief summary of evidence considered",
  "campaign_id": "recYYY or null",
  "campaign_name": "... or null",
  "reason": "specific evidence",
  "confidence": "high/medium/low",
  "alt_campaign_id": "recZZZ or null",
  "alt_campaign_name": "... or null",
  "alt_reason": "..."
}

If no campaign fits, set campaign_id to null and explain: "NEW CAMPAIGN: [name]" or "NO MATCH: [why]".
```

**After each batch:**
1. Present recommendations to operator for approval/adjustment
2. If a new campaign is suggested, align on details and create it before the next batch
3. Execute approved associations immediately (don't wait for all batches)
4. For deals with no signals, create research tasks and skip them
5. Only proceed to the next batch after approval + execution

### Phase D: Execute

After each batch is approved, write recommendations to a JSON file and run:

```bash
python3 associate_deals.py --execute recommendations.json
```

Expected format:
```json
[
  {"deal_id": "recXXX", "campaign_id": "recYYY", "deal_name": "...", "campaign_name": "..."}
]
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--assignee` | aaron | Scopes to this person's deals |
| `--deal` | (none) | Single deal by record ID |
| `--execute FILE` | (none) | Apply associations from recommendations JSON |

## Data Enrichment

**Deals:**
- Organization name(s)
- Contact name(s) via junction table
- Activity logs: 3 earliest (first touches / campaign source) + 3 most recent (current state), each with full content (type + details up to 500 chars)
- Tags 2 (old campaign stage), Engagement, Outreach Plan
- Description, Pain Points
- Created date and Created By

**Campaigns:**
- Name, Source, Status, Campaign Code
- Description, Target Audience, Campaign Plan (up to 800 chars)
- Message Guardrails
- Deal count, Assignee, Started/Ended dates

## Dependencies

- `../airtable-config/airtable_config.py` (Airtable config)
- Airtable API (AIRTABLE_TOKEN env var)
- `gog` CLI (for Google Drive campaign doc search in Phase A)
