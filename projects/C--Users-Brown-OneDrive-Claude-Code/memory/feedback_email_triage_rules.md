---
name: Email Triage & Auto-Draft Rules
description: Rules for the morning/afternoon email triage system including auto-draft behavior, scheduling replies, GTM campaign handling, batch processing workflow, tone adaptation, and command vocabulary.
type: feedback
---

## Auto-Draft Rules
- NOTHING should ever be auto-sent. Everything goes to Gmail drafts only.
- Auto-draft means use best judgment to reply naturally based on all available context (Airtable, transcripts, email history)
- Scheduling replies: draft introducing Brainy as "our AI operations manager" who will coordinate schedules, CC brainy-brown@lindymail.ai
- There is nothing that should NEVER be auto-drafted, but everything needs Josh's review before sending
- When auto-drafting, analyze the recipient to determine appropriate tone:
  - Internal team / close contacts: very casual, warm, direct
  - Active clients / warm leads: friendly, expert, approachable AI subject matter expert
  - Existing customers (Won deals): warm, partnership-oriented, expansion-minded
  - Institutional / corporate / nonprofit leadership: professional but warm, no slang
  - New/unknown contacts: professional-approachable, mirror their formality level
  - Partners (ASU, AZ MEP, ACA): warm, collaborative, strategic framing
- Auto-drafts should require less than 5 minutes of Josh's editing. If a draft would need heavy rewriting, flag as "personal attention" instead.
- NEVER use em dashes or en dashes in any draft. Use periods, commas, or restructure.
- NEVER remove anyone from CC or BCC. Only ADD CCs when specifically called for (e.g., Brainy).
- Gmail MCP handles signature automatically. Do NOT include manual sign-offs.

## Context Briefing Format
When Josh wants to process a specific email, provide:
- Deal stage, amount, days in stage, assignee, closing date (from Airtable)
- Transcript history highlights (most relevant need-to-know, not obvious info)
- **FULL email history summary across ALL threads with this contact** (not just the inbox thread)
- Staleness indicators based on MOST RECENT email in ANY thread (7+ days = cooling, 14+ days = going cold)
- Urgency signals (deadlines, time-sensitive language, Urgent Brown label)
- Any Airtable or data lake data (pain points, engagement level, deal type)
- Format: brief summary that can be expanded via "expand" command

## Critical: Full Email History is Mandatory
- ALWAYS search `from:<email>` AND `to:<email>` before presenting any contact's batch
- The inbox thread may be stale. Newer threads outside the inbox may have resolved the issue.
- If a newer thread supersedes the inbox thread, the recommendation must reflect the CURRENT state
- Check for team activity (Sven, Aaron, Daniel, Juan) in parallel threads with the same contact
- Staleness is measured from the MOST RECENT email in ANY thread, not just the inbox thread
- **Failure to do this results in wrong recommendations, wrong drafts, and wasted time**

## Batch Processing Workflow
- Group emails by RELATIONSHIP/CONTEXT, not just category
- A "batch" = all emails related to a relationship or initiative, potentially spanning Sales + BizDev categories
- Example: All SciTech emails (both sales and strategy) presented together as one cognitive unit
- "Clear the batch" = move to next relationship group after all items in current batch are processed
- Batching should be DYNAMIC: sometimes one person/one thing, sometimes a multi-stakeholder initiative
- Goal: reduce cognitive load by allowing Josh to process one relationship context at a time
- Within cross-category batches, SALES items are listed first

## Dashboard Sections (in order)
1. SALES: batches where all emails are sales-only
2. CROSS-CATEGORY RELATIONSHIPS: batches spanning both Sales and BizDev (e.g., SciTech)
3. BIZDEV: batches where all emails are bizdev-only
4. INTERNAL: batches from Brain Bridge team members

## Batch Priority Order (within sections)
1. Urgent/time-sensitive (Urgent Brown label or detected deadline)
2. Existing customers with new activity (Won deals, stage 10)
3. Active deals in late stages (07-09)
4. Active deals in mid stages (03-06)
5. Strategic partnerships
6. Early-stage leads (01-02)
7. Internal operations
8. Uncategorized/new contacts

## Auto-Archive Rules (Silent, No Asking)
- LinkedIn connection requests, endorsements, congratulations
- Cold sales/SDR outreach (unknown sender + sales language + no Airtable match)
- Newsletters/promos (unsubscribe links, bulk sender patterns)
- Calendar notifications (accepts, declines, updates, cancellations)
- System notifications (GitHub, CI/CD) unless critical
- Emails where deal is assigned to someone else in Airtable AND Josh is only CC'd

## GTM Campaign Marking
- "Mark for GTM" = add to a running list (contacts to add to GTM campaigns)
- Do NOT take any action on GTM-marked items. No Airtable changes, no emails.
- Present the full GTM list at the end of triage session
- Josh will manually add these contacts to campaigns

## Deal Pulse (After Email Batches)
- Surface active deals (stages 03-09) with no email activity in 7+ days
- Surface deals with closing dates within 14 days
- Surface deals where last email was outbound from Josh with no reply

## Command Vocabulary
| Command | Action |
|---|---|
| auto-draft [#s] / draft [#s] | Draft natural replies for those items |
| respond [#] / I'll handle [#] | Flag for personal attention with deep context |
| GTM [#s] / mark for GTM | Add to running GTM prospect list |
| archive [#] / kill [#] | Archive that email |
| expand [#] / tell me more about [#] | Show deep context brief (deal, transcripts, history) |
| draft-all / draft everything | Auto-draft all items with auto-draft recommendation |
| clear / next / done | Mark batch as processed, show next batch |
| skip | Skip batch, come back later |
| brainy [#] / schedule [#] | Auto-draft scheduling reply with Brainy CC |
| go | Start from top / continue to next batch |
| wrap up / done for now | Jump to session summary |
| show me draft for [name] | Review a specific draft in chat |
| send [name]'s draft | Send individual draft (only with explicit instruction) |

## Dropped Ball Scan (Part 2 — SEPARATE from inbox triage)
- This is a completely separate exercise from the inbox triage (Part 1)
- Part 1 (all inbox batches, drafts, Deal Pulse, wrap-up) must be FULLY COMPLETE before starting Part 2
- Do NOT interleave dropped ball scanning with inbox triage. Josh handles urgent/pressing items first.
- Scan full Gmail for unreplied inbound emails (default: last 30 days)
- Filter out noise (newsletters, cold SDR, no-reply addresses, internal team, already-processed senders)
- Check if Josh or team ever replied in any thread with each sender
- Surface contacts who were left hanging, grouped by severity (urgent/moderate/recent)
- Josh processes dropped balls with the same command vocabulary as inbox batches
- Adjustable time window: "scan last 60 days", "check 90 days back"

## Triage Schedule
- Morning: 7:00 AM daily (scheduled task pre-processes, Josh triggers "triage" when ready)
- Afternoon: 12:00 PM daily (identical full triage, same format)
- Both sessions use the same email-morning-triage skill

## Airtable Contact/Company/Deal Verification (Every Triage Session)
- Every contact in the inbox MUST be checked against Airtable for: Contact record, Organization record, Deal record
- If a Contact record exists but the email address doesn't match what the sender is currently using, flag it and give Josh the option to update
- If no Contact or Organization record exists, ask Josh if he wants to create them. Not all contacts need a Deal, but Contact + Org should always be offered.
- If Josh declines, keep asking on future triages UNLESS Josh explicitly says "never ask again" for that contact/company
- "Never ask again" contacts/companies are tracked in the list below and silently skipped
- This applies to: morning triage, afternoon triage, email-reply-assistant, and any email-related skill
- Record creation order: Organization first, then Contact (linked to Org), then Deal (linked to Org) if requested
- Always pre-populate records with data from email signatures, web search, and existing context before presenting to Josh

### CRM Never-Ask List
(Contacts/companies Josh has explicitly said to never ask about creating in Airtable)
- (none yet)

## Label Protection
- NEVER add, remove, or modify any Gmail labels
- Labels are read-only inputs for classification
- Existing label structure is sacred
