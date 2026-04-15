---
name: email-morning-triage
description: >
  CEO morning/afternoon email triage system. Builds today's meeting agenda with attendee context, fetches inbox,
  cross-references Airtable CRM and transcripts, clusters emails into relationship-based batches, presents a
  command-driven dashboard, auto-drafts replies, tracks GTM prospects, sets daily priorities from BB Tasks,
  and surfaces a sales follow-up dashboard for stale deals and tasks. Use when Josh says "triage",
  "process inbox", "morning email", "afternoon email", "check my email", "what's on today",
  "today's agenda", "set priorities", or "what should I focus on".
  Runs identically for both morning and afternoon sessions.
---

# Email Morning Triage System

**Four-part system.** Phase 0: Today's meeting agenda with attendee context from Airtable and email history. Part 1 (Phases 1-6): Command-driven inbox triage that transforms Josh's inbox into relationship-grouped batches enriched with CRM context, transcript intelligence, and email history. Josh processes batches by issuing numbered commands, clears each batch, and moves on. Output: clean inbox, drafts ready to send, GTM prospect list, and a short personal-attention list. Post-triage: Daily priorities from BB Tasks and a sales follow-up dashboard surfacing stale deals and tasks. Part 2 (separate exercise, only after everything above is complete): Dropped ball scan across all of Gmail for unreplied contacts.

## Core Design Principle

**This system exists because deals die from cognitive overload, not from bad emails.** Every email should arrive with a recommendation and, where possible, a ready draft. If Josh has to think about what to do with an email, the system failed. Optimize for maximum impact in minimum time.

## UNIVERSAL ARCHIVE RULE (MANDATORY)

**Every time a message is archived during triage, regardless of which phase or which command triggered the archive, ALL four inbox labels MUST be removed in a single `gmail_modify_labels` call:**

- `INBOX`
- `Label_3884176123759987561` (Check Brown)
- `Label_4977808787076738220` (Read Brown)
- `Label_8057477445084827980` (Urgent Brown)

Remove all four every time, unconditionally. Do not inspect which labels are currently on the message and do not "only remove what's there." Pass all four IDs in `remove_labels` on every archive action. Gmail silently ignores removals for labels that aren't attached, so this is safe and idempotent.

This applies to:
- Phase 1.2 noise archival
- Any `archive [letter]` or `archive [#]` command during batch processing
- Deep-search sweeps (Phase 7 dropped-ball scan dismissals)
- Any other archive action taken during the triage session

The goal: an archived email must never reappear in a future triage because one of the secondary labels was overlooked.

## Trigger

Use when Josh says any of: "triage", "process inbox", "morning email", "afternoon email", "check my email", "email triage", "let's do email", "what's on today", "today's agenda", "set priorities", "what should I focus on", or any variation requesting inbox processing, meeting prep, or daily priority setting.

---

## PHASE 0: TODAY'S AGENDA (Automated, Before Inbox Processing)

**Purpose:** Give Josh a quick briefing on today's meetings before diving into email. Runs first, completes in under 60 seconds. Do not let slow lookups block triage.

### Step 0.1 - Find Today's Meetings via Gmail

Search Gmail for calendar-related emails that indicate meetings scheduled for today:

- `gmail_search` with query: `subject:(invitation OR invite OR "accepted" OR "updated invitation") newer_than:14d`
- `gmail_search` with query: `from:calendar-notification@google.com newer_than:7d`
- `gmail_search` with query: `subject:("agenda" OR "prep" OR "meeting notes") newer_than:3d`

From results, extract events occurring **today** by parsing date references in subject lines and email bodies (look for today's date in various formats). Deduplicate by event title/time.

For each meeting, capture: title, time, organizer, attendee list (from invite/RSVP emails).

### Step 0.2 - Attendee Enrichment

For each meeting attendee (parallel lookups, time-cap 30 seconds total):

1. **Airtable Contact lookup** (`tbllWxmXIVG5wveiZ`): Search by attendee email. Pull name, role, organization, linked deals.
2. **Airtable Deal lookup** (`tblw6rTtN2QJCrOqf`): If contact has linked deals, pull deal name, stage, amount, assignee, closing date.
3. **Email history search**: `gmail_search` for `from:<attendee_email>` and `to:<attendee_email>` (last 5 messages each direction). Summarize last interaction date and topic.
4. **BB Tasks lookup** (`tblmQBAxcDPjajPiE`): Search for tasks linked to the attendee's deals. Note any open action items.

If a lookup takes too long, skip it and note "context unavailable" rather than blocking the agenda.

### Step 0.3 - Present Agenda Briefing

```
TODAY'S AGENDA — [Date]
========================

[Time] — [Meeting Title]
  Organizer: [Name]
  Attendees: [Name (Role, Org)] | [Name (Role, Org)] | ...
  Deal context: [Deal name — Stage, $Amount] (if applicable)
  Last contact: [Date — brief topic summary]
  Open items: [Any open tasks or action items relevant to this meeting]
  Prep notes: [1-2 sentence recommendation: what to review, what to raise, what to close]

[Time] — [Meeting Title]
  ...

Ready to proceed to inbox triage? Say "go" or ask about any meeting.
```

**If no meetings are found for today**, display one line:

```
No meetings on today's calendar. Proceeding to inbox triage.
```

Then continue directly to Phase 1.

---

## PHASE 1: FETCH & FILTER (Automated, No User Input)

### Step 1.1 - Pull Inbox

Search all four inbox labels in parallel:
- `gmail_search` with query: `label:INBOX`
- `gmail_search` with query: `label:Check-Brown`
- `gmail_search` with query: `label:Urgent-Brown`
- `gmail_search` with query: `label:Read-Brown`

For each email found:
- Pull message metadata: sender, subject, date, labels, thread ID, snippet
- Deduplicate by thread ID (multiple messages in same thread = one item)
- Use `gmail_get_thread` to read full thread content for each unique thread

### Step 1.2 - Identify Noise Emails (Requires Approval)

Identify emails matching the noise patterns below, but **DO NOT archive them automatically.** Instead, present the full list to Josh and wait for explicit approval before archiving any of them.

**Noise patterns:**
- **LinkedIn**: Connection requests, endorsements, "congratulations", skill endorsements, "who viewed your profile"
- **Cold outreach**: Unknown sender + sales language + no Airtable match (SDR emails, cold pitches)
- **Newsletters/promos**: Emails with unsubscribe links, bulk sender patterns, marketing campaigns
- **Calendar notifications**: Accepts, declines, updates, cancellations, rescheduling confirmations
- **System notifications**: GitHub, CI/CD, monitoring alerts (unless they mention "critical", "down", or "error")
- **Delegated relationships**: Emails where the deal is assigned to someone other than Josh in Airtable AND Josh is only CC'd (not in the To line)

**Presentation format:**
```
NOISE EMAILS ([count] identified)
==================================
Newsletters/Promos ([count]):
  1. [Sender] - "[Subject]"
  2. [Sender] - "[Subject]"

Calendar ([count]):
  3. [Sender] - "[Subject]"

Cold Outreach ([count]):
  4. [Sender] - "[Subject]"

LinkedIn ([count]):
  5. [Sender] - "[Subject]"

System ([count]):
  6. [Sender] - "[Subject]"

Delegated ([count]):
  7. [Sender] - "[Subject]"

Archive all? Or say "keep [numbers]" to pull any back into triage.
```

**Rules:**
- Wait for Josh to say "archive all", "yes", "go ahead", or similar before archiving
- If Josh says "keep [numbers]", move those emails back into the triage pipeline and archive the rest
- When archiving, remove ALL inbox-related labels from the email: **INBOX**, **Check-Brown**, **Urgent-Brown**, and **Read-Brown**. This ensures the email is fully cleared from the triage system and won't reappear in future triages.
- After approval: present a one-line confirmation at the start of triage dashboard:
```
Archived: [count] noise emails ([breakdown])
```

### Step 1.3 - Flag Scheduling Requests

Scan remaining emails for scheduling intent:
- Keywords: "find a time", "schedule a call", "are you available", "let's meet", "when works for you", "grab 15 minutes", "set up a meeting"
- Calendar links: Calendly, HubSpot meetings, Chili Piper, etc.

Tag these internally as SCHEDULING for auto-draft with Brainy CC later.

---

## PHASE 2: CLASSIFY & ENRICH (Automated, No User Input)

### Step 2.1 - Sender Identification & Airtable Record Verification

**PRIMARY KEY: Email address.** Always use the sender's email address from the inbox thread as the primary lookup key. Never rely on name matching alone. Names are ambiguous (Tom vs Thomas, Ben vs Benoît). Email addresses are unique.

For each remaining email sender, run Airtable lookups:

1. **Search Contacts table** (`tbllWxmXIVG5wveiZ`) by the sender's **email address** (search both `Email (Work)` and `Email (Personal)` fields)
2. **If found**: Pull linked Organization, linked Deals, contact type, role
3. **If not found by email**: Search by sender name as a fallback. Check email domain against Organizations table (`tblPEqGDvtaJihkiP`). But treat name matches as tentative until confirmed.
4. **If still unknown**: Flag as "New Contact". Extract what you can from email signature (name, title, company, phone)

**When Josh references a contact by name** (e.g., "Tyler Smith") while working on a thread, always resolve the name to the email address from that thread first, then search Airtable by that email address. Do NOT search Airtable by name alone. This prevents false negatives (name spelled differently) and false positives (duplicate records with the same name).

**Airtable Record Verification (MANDATORY for every sender):**

Every contact that appears in the inbox must be checked against Airtable. The goal is to ensure Brain Bridge has a complete record of every person Josh communicates with.

**Check 1 — Contact exists?**
- If NO Contact record exists: Flag as `CRM: No contact record`. Queue for Josh's decision.
- If Contact record exists: proceed to Check 2.

**Check 2 — Email address matches?**
- Compare the email address the sender is CURRENTLY emailing from against the `Email (Work)` field in their Airtable Contact record.
- If they DON'T match: Flag as `CRM: Email mismatch (Airtable has X, sender uses Y)`. Give Josh the option to update.

**Check 3 — Organization exists?**
- If no linked Organization record: Flag as `CRM: No organization record`. Queue for Josh's decision.
- If Organization exists: proceed to Check 4.

**Check 4 — Deal exists?**
- If no linked Deal record: Note as `CRM: No deal record`. Queue for Josh's decision.
- Not all contacts need a deal. Josh decides. But always surface the option.

**Presenting CRM gaps to Josh:**
- During batch presentation (Step 4.2), include a `CRM:` status line for every email showing the current state.
- If records are missing, ask Josh: "Want me to create a Contact/Organization/Deal for [Name]?"
- If Josh declines, keep asking on future triages UNLESS Josh says "never ask again" for that specific contact/company.
- Maintain a `CRM_NEVER_ASK` list in session memory. Contacts/orgs on this list are silently skipped in future sessions.
- If Josh says "never ask again" for a contact, note it in the feedback rules file so it persists across sessions.

**Record creation flow (when Josh approves):**
1. Extract sender name, email, title, company from email signature/headers.
2. Search the web for the sender's company to gather: industry, size, location, description.
3. Pre-populate all proposed fields and present summary to Josh for confirmation.
4. Create in order: Organization first, then Contact (linked to Org), then Deal (linked to Org) if requested.
5. Default deal stage: "02-Contacted" if an email has been exchanged.

### Step 2.2 - Category Classification

Each email gets one or more categories:

**SALES (Definitive Rule):**
- If the sender/org has ANY deal record in Airtable Deals table (`tblw6rTtN2QJCrOqf`), they are SALES. Period.
- **Active deal (stages 01-09):** Label as ACTIVE PROSPECT. Note the stage and deal amount.
- **Won deal (stage 10-Signed Proposal Won):** Label as EXISTING CUSTOMER. Frame as upsell/resell opportunity.
- **Lost/Disqualified deal:** Still note the history. May be a re-engagement opportunity.

**BIZDEV:**
- Sender is tagged as partner/referral partner in Airtable
- Sender is from: ASU SciTech, University of Arizona, AZ MEP, ACA Secret Sauce
- Content discusses partnerships, introductions, co-marketing, referrals, strategic initiatives, joint proposals
- Anyone listed as a referral partner in Airtable Organizations

**INTERNAL:**
- Sender is Aaron Eden, Sven Plieger, Juan Ortiz, or Daniel Lee
- Content about client delivery, operations, Brain Bridge business, internal tools/systems

**CROSS-CATEGORY:**
- A contact CAN be both SALES and BIZDEV (e.g., SciTech is both customer and strategic partner)
- When cross-category, **sales items are listed first** within the batch

**UNCATEGORIZED:**
- No Airtable match, no clear signals. Present for Josh's judgment.

### Step 2.3 - Context Enrichment (MANDATORY — Never Skip)

For each email/thread, build a context packet. **Every sub-step below is required.** Incomplete enrichment leads to wrong recommendations, wrong drafts, and wasted time.

**⚠️ CRITICAL RULE: Full Email History Search is NON-NEGOTIABLE.**
Before presenting ANY email to Josh, you MUST search the sender's full Gmail history. The inbox thread may be stale or superseded by more recent threads. If you skip this step, you WILL present outdated context and Josh WILL act on bad information. This is the single most important enrichment step.

**Email history (REQUIRED FIRST — do this before all other enrichment):**
- Use `gmail_search` for `from:<sender_email>` AND `to:<sender_email>` (both directions, in parallel)
- Pull at least the 10-15 most recent messages across ALL threads with this person
- Identify ALL active threads with this contact, not just the inbox thread
- **Check for superseding context**: If a newer thread exists that resolves, updates, or changes the situation described in the inbox thread, the newer thread takes precedence. The inbox thread may be old/stale.
- **Check for recent outbound from Josh**: Did Josh already reply, follow up, or address this? If so, note it.
- **Check for activity with the team**: Are Sven, Aaron, Daniel, or Juan in recent threads with this contact? If so, summarize their involvement.
- Summarize the last 3-5 interactions chronologically (date, topic, who initiated, outcome, current status)
- **Determine the TRUE current state** of the relationship based on ALL email evidence, not just the inbox thread

**Airtable data:**
- Deal: stage name, days in current stage, deal amount, assignee, closing date, engagement level
- Contact: role, title, org, relationship type
- Organization: industry, type, other deals with this org

**Transcript search (via MCP data lake):**
- Search for sender name, org name, project name
- Extract 2-3 most relevant snippets (not full transcripts)
- Prioritize most recent transcripts

**Staleness detection (based on FULL email history, not just inbox thread):**
- Calculate staleness from the MOST RECENT email in ANY thread with this contact
- If the most recent exchange is within 48 hours, the relationship is ACTIVE — do not flag as stale
- If deal has had no email activity in 7+ days, flag as "cooling"
- If deal has had no activity in 14+ days, flag as "going cold"

**Urgency signals:**
- Email has Urgent Brown label
- Time-sensitive language ("by Friday", "deadline", "ASAP", "end of month")
- Reply-expected indicators ("let me know", "waiting to hear back", "following up")

**Validation check (before presenting to Josh):**
- Does the inbox email still represent an open action item, or has it been resolved in a different thread?
- Is there a more recent thread that changes the context or urgency?
- Would the recommendation change if Josh had seen the full email history? If yes, adjust the recommendation.
- If the inbox thread is outdated/resolved, note it as "RESOLVED — [brief explanation]" and recommend archiving unless there's a new action needed

---

## PHASE 3: CLUSTER INTO BATCHES

### Step 3.1 - Relationship Clustering

Group emails into cognitive units. NOT a flat list. Each batch = one relationship context.

**Clustering logic (priority order):**
1. **Organization cluster**: All emails from the same org get grouped together, regardless of which individual sent them (e.g., all SciTech emails from Trip, Jim, Sarah, Dr. Martinez = one batch)
2. **Initiative cluster**: If multiple unrelated people are emailing about the same project/initiative, group them (e.g., "Brainy rollout" emails from different prospects)
3. **Individual cluster**: Solo emails that don't belong to a larger context (one-off inquiry from a new lead)

**Within each cluster, sub-group by category, with SALES first:**
```
BATCH: SciTech Institute (5 emails)
  SALES (3):
    #1 - Trip Shannan: Re: Brainy pilot pricing [Deal: 06-Aligning Scope, $45K]
    #2 - Jim Carroll: Re: Data integration timeline [Deal: 04-Soft-Qualifying]
    #3 - New contact (Sarah Chen): Inquiry about AI training services
  BIZDEV (2):
    #4 - Dr. Martinez: Re: Joint research proposal with ASU
    #5 - Board notification: Next advisory meeting March 28
```

### Step 3.2 - Batch Ordering (Strategic Priority)

Order batches in the dashboard following this priority stack:

1. **Urgent/time-sensitive** - Urgent Brown label or detected deadline within 48 hours
2. **Existing customers with new activity** (Won deals, stage 10) - protect and expand revenue
3. **Active deals in late stages** (07-Proposal Meeting Booked through 09-Negotiating) - closest to new revenue
4. **Active deals in mid stages** (03-Responding through 06-Aligning Scope) - pipeline momentum
5. **Strategic partnerships** - long-term value
6. **Early-stage leads** (01-02) - nurture
7. **Internal** - delivery and operations
8. **Uncategorized/new contacts** - requires Josh's judgment

### Step 3.3 - Dashboard Section Assignment

Assign each batch to a dashboard section:
- **SALES**: Batches where ALL emails are sales-only
- **CROSS-CATEGORY RELATIONSHIPS**: Batches where emails span both Sales and BizDev (e.g., SciTech)
- **BIZDEV**: Batches where ALL emails are bizdev-only
- **INTERNAL**: Batches from Brain Bridge team members

---

## PHASE 4: PRESENT TO JOSH (Interactive)

### Step 4.1 - Triage Overview Dashboard

**Draft Detection (MANDATORY before presenting dashboard):**
Before presenting the dashboard, pull the list of Gmail drafts (`gmail_list_drafts`). For each inbox thread, check if a draft reply already exists for that thread by matching thread IDs. If a draft exists:
- Do NOT exclude the email from the dashboard. Still include it in its batch.
- Flag it with `DRAFT EXISTS` in the batch presentation (Step 4.2).
- When presenting the batch, show a one-line snippet of the existing draft and ask: "Keep this draft, replace it, or delete it?"
- If Josh says "keep", move on. If "replace", delete the old draft and create a new one. If "delete", remove the draft and treat the email as unhandled.

Present the high-level dashboard:

```
TRIAGE - [Date]
================================
Noise archived: [count] emails ([breakdown])
Remaining: [count] emails across [count] batches

SALES ([count] emails, [count] batches)
  [A] [Org/Person] - [count] emails - [Deal stage info]
  [B] [Org/Person] - [count] emails - [Deal stage info]
  ...

CROSS-CATEGORY RELATIONSHIPS ([count] emails, [count] batches)
  [C] [Org/Person] - [count] emails ([breakdown by category])
  ...

BIZDEV ([count] emails, [count] batches)
  [D] [Org/Person] - [count] emails - [relationship context]
  ...

INTERNAL ([count] emails, [count] batches)
  [E] Brain Bridge Operations - [count] emails ([who x count])
  ...

Ready to start? Pick a batch letter, or say "go" to start from the top.
```

### Step 4.2 - Batch Presentation

When Josh picks a batch (letter) or says "go", present the expanded batch:

```
BATCH [LETTER]: [Name] ([count] emails)
======================================

SALES:
  #1 [Sender] - "[Subject]"
     [Deal info: stage | amount | days in stage]
     CRM: [✅ Contact + Org + Deal] or [⚠️ No contact record] or [⚠️ Email mismatch] or [⚠️ No deal]
     DRAFT: [📝 Draft exists: "[snippet of draft]" — Keep, replace, or delete?] (only if a draft exists for this thread)
     > [One-line summary of what the email is about and what action is expected]
     REC: [Recommendation: auto-draft / respond / archive / brainy / GTM]

  #2 [Sender] - "[Subject]"
     [Context: deal info, new contact indicator, relationship note]
     CRM: [status]
     > [One-line summary]
     REC: [Recommendation]

BIZDEV: (if cross-category)
  #3 [Sender] - "[Subject]"
     [Context]
     CRM: [status]
     > [Summary]
     REC: [Recommendation]

CRM GAPS (if any):
  - [Name]: [Missing Contact / Missing Org / Missing Deal / Email mismatch]. Create? [yes/no/never ask]

COMMANDS: [auto-draft #] [respond #] [GTM #] [archive #] [expand #] [brainy #] [draft-all] [clear] [skip]
```

**Every email MUST have a recommendation based on COMPLETE context.** The recommendation must account for the full email history with this contact, not just the inbox thread. If the inbox thread has been superseded by newer activity (payment made, meeting held, issue resolved), the recommendation must reflect the CURRENT state. Don't present an email without telling Josh what you think should happen. Possible recommendations:
- **Auto-draft**: You can write a good reply based on context. Say what the draft will cover.
- **Brainy**: This is a scheduling request. Auto-draft with Brainy CC.
- **Respond**: This needs Josh's personal voice/judgment. Flag for personal attention.
- **Archive**: Informational only, no action needed.
- **GTM**: This person should be added to a GTM campaign.
- **Expand**: Recommend Josh get the deep context brief before deciding.

### Step 4.3 - The "Expand" Command

When Josh says "expand #[N]", provide the deep context brief:

```
DEEP CONTEXT: [Sender] - [Subject]
======================================================
DEAL: [Deal name] | [Stage] | [Amount] | Created [date]
  Pipeline trajectory: [stage progression with time in each]
  Assigned to: [name]
  Closing date: [date]
  Engagement: [level]

EMAIL HISTORY (last 5 threads):
  - [Date]: [Summary of exchange]
  - [Date]: [Summary]
  ...

TRANSCRIPT HIGHLIGHTS ([date] call - "[title]"):
  - [Key insight not obvious from email]
  - [Key insight]
  - [Key quote if impactful]

CURRENT EMAIL:
  [Full email body displayed]

AIRTABLE NOTES:
  [Any relevant fields: pain points, description, tags]

RECOMMENDATION: [Detailed strategic recommendation with reasoning]
```

### Step 4.4 - Context Presentation (The "Give Me Context" Command)

When Josh says "give me context for [letters]", "context for [name]", "full emails for [letters]", or any variation requesting expanded context for one or more batches, present each batch using this exact format:

```
## [LETTER] [Contact Name] — [Organization]
**Priority: [HIGH/MEDIUM/LOW] ([reason])**

**CRM:** [Deal name, stage, assignee, key deal details] or "No Airtable record (contact or deal)"
**CRM Status:** [✅ All records exist] or [⚠️ Missing: Contact / Organization / Deal] or [⚠️ Email mismatch: Airtable has X, sender uses Y]
**Relationship:** [New/Existing. How long. Key context from history.]

**Full Thread:**
1. **[Sender] → [Recipient] ([date]):** [Full email body content, not a summary]
2. **[Sender] → [Recipient] ([date]):** [Full email body content]
...

**Situation:** [2-3 sentences explaining the current state based on ALL evidence: inbox thread, email history, CRM data, superseding context. What happened, where things stand RIGHT NOW.]

**Recommendation:** [Clear actionable recommendation. What Josh should do and why.]
```

**Rules for this format:**
- **Full email bodies, not summaries.** Show the actual content of every message in the thread. Josh needs to read the real words, not a paraphrase.
- **Chronological order.** Oldest message first, newest last.
- **Strip quoted replies.** Only show the new content in each message, not the cascading quoted text from previous replies.
- **CRM data is mandatory.** Always include Airtable deal info if it exists. If no record exists, say so explicitly.
- **Situation must reflect the TRUE current state.** Cross-reference full email history, not just the inbox thread. If a Calendly rebooking, payment, or other superseding event occurred, call it out.
- **One recommendation per batch.** Be specific. "Draft a reply" is not enough. Say what the reply should accomplish and suggest Brainy/archive/GTM/respond as appropriate.

This format is used whenever Josh requests context for specific batches, contacts, or names. It replaces the compact dashboard view (Step 4.2) for those items with a full-context presentation that gives Josh everything he needs to make a decision.

---

## PHASE 5: COMMAND PROCESSING

### Step 5.1 - Command Parser

Josh issues commands in natural language. Interpret flexibly:

| Input Pattern | Action |
|---|---|
| `auto-draft 1, 2, 3` or `draft 1 2 3` | Generate drafts for those items |
| `respond 7` or `I'll handle 7` | Flag for personal attention, present deep context when ready |
| `GTM 3, 8` or `mark 3 and 8 for GTM` | Add to running GTM prospect list |
| `archive 5` or `kill 5` | Archive that email |
| `expand 2` or `tell me more about 2` | Show deep context brief |
| `draft-all` or `draft everything` | Auto-draft all items with an auto-draft recommendation |
| `clear` or `next` or `done` | Mark batch as processed, present next batch |
| `skip` | Skip batch, come back later |
| `brainy 4` or `schedule 4` | Auto-draft scheduling reply with Brainy CC |
| `context [letters]` or `give me [letters]` or `full emails for [letters]` | Present full context format (Step 4.4) for those batches |
| `go` | Start from the top / continue to next batch |
| `wrap up` or `done for now` | Jump to session summary |
| `scan [N] days` or `check last [N] days` | Adjust dropped ball scan window (default 30 days) |

Josh may also use compound commands: "draft 1 and 2, archive 5, GTM 3, and I'll respond to 4"

When Josh gives numbered commands for a batch like "1, 2, 3, 5 should be auto-drafted", interpret that as `auto-draft 1, 2, 3, 5`.

### Step 5.2 - Auto-Draft Execution

**HARD RULES FOR ALL DRAFTS:**
- **NEVER remove anyone from CC or BCC.** If someone is on the thread, they stay. Only ADD CCs when called for.
- **NEVER send.** Everything goes to Gmail Drafts via `gmail_create_draft`. NEVER use gmail_send or gmail_reply with send.
- **NEVER use em dashes (--) or en dashes (-).** Use periods, commas, or rewrite the sentence.
- **Preserve the full recipient list** from the existing thread exactly as-is.
- **ALWAYS show Josh the draft text in chat BEFORE creating it in Gmail drafts.** Wait for approval.

**Tone Detection (per recipient):**

| Recipient Type | Tone |
|---|---|
| Internal team / close contacts (Aaron, Sven, Juan, Daniel) | Very casual, warm, direct, minimal pleasantries |
| Active clients / warm leads | Friendly, expert, approachable. Josh as AI subject matter expert. |
| Existing customers (Won deals) | Warm, partnership-oriented, looking for expansion opportunities |
| Institutional / corporate / nonprofit leadership | Professional but warm, no slang, respectful of formality |
| New/unknown contacts | Professional-approachable, mirror their formality level |
| Partners (ASU, AZ MEP, ACA) | Warm, collaborative, strategic framing |

**Intent Inference (per email context):**

| Detected Intent | Draft Approach |
|---|---|
| Scheduling request | Brainy handoff (see Step 5.3) |
| Question asked | Answer using transcript/history context, offer to elaborate |
| Follow-up needed | Warm check-in referencing last interaction |
| Proposal/pricing discussion | Reference deal specifics, push toward next pipeline stage |
| Introduction/new contact | Warm welcome, suggest call, reference how they found us |
| Thank you / confirmation | Brief acknowledgment, next steps if applicable |
| Problem/complaint | Empathetic response, acknowledge issue, propose resolution path |

**Draft Generation Process:**
1. Determine tone from recipient analysis
2. Determine intent from email content + deal stage + transcript context
3. Generate draft following Josh's Email Writing Style Guide (see below)
4. Scan for em dashes and double dashes. Rewrite any violations.
5. Present draft in chat to Josh
6. On approval: create as Gmail draft via `gmail_create_draft` (NEVER send)

**Gmail Signature Handling:**
The Gmail MCP server automatically appends Josh's configured Gmail signature. Do NOT include a manual sign-off in the email body (no "Josh", "- Josh", "Best, Josh", etc.). End the email body with the last line of actual content.

### Step 5.3 - Scheduling Reply (Brainy Handoff)

For any email tagged as SCHEDULING:

Draft template:
```
Hey [Name]!

[1-2 sentences acknowledging the meeting request / context for why meeting is valuable]

I'm looping in Brainy, our AI operations manager, who will help us both find a time that works.

[Optional: mention meeting topic/agenda if relevant]

Looking forward to connecting!
```

- **CC:** brainy-brown@lindymail.ai (ADD to CC, never replace existing CCs)
- **Default meeting length:** 30 minutes (unless Josh specifies otherwise)

### Step 5.4 - GTM Marking

When Josh marks items for GTM:
- Extract: Name, email, company, title (from email signature/Airtable)
- Add to a running list held in session memory
- Do NOT take any action on these contacts. No Airtable changes, no emails, no campaigns.
- Present the full GTM list at session wrap-up.

---

## PHASE 6: SESSION WRAP-UP

When all batches are processed or Josh says "wrap up":

### Step 6.1 - Summary Dashboard

```
TRIAGE COMPLETE
===============
Processed: [count] emails across [count] batches
  Noise archived (with approval): [count]
  Auto-drafted: [count] (ready in Gmail Drafts)
  Marked for personal response: [count]
  Archived during triage: [count]
  GTM prospects collected: [count]
  Dropped balls found: [count] (from Phase 7 full Gmail scan)

DRAFTS READY FOR REVIEW:
  1. [Sender] - [Subject]
  2. [Sender] - [Subject]
  ...

PERSONAL ATTENTION NEEDED:
  - [Sender] - [Subject] ([reason: strategic review / high-value / needs Josh's voice])
  - [Sender] - [Subject] ([reason])
  ...

DROPPED BALLS RECOVERED:
  - [Name] - [Subject] ([days] days, [action taken: drafted / flagged / GTM])
  - [Name] - [Subject] ([days] days, [action taken])
  ...

GTM CAMPAIGN PROSPECTS:
  - [Name] ([email]) - [Company], [context for why GTM]
  - [Name] ([email]) - [Company], [context]
  (Copy this list for manual GTM entry)
```

### Step 6.2 - Draft Review & Send (FINAL STEP)

**This is the last step of every morning and afternoon triage session.** After all batches are processed, present ALL drafts created during this session for Josh to review and send.

```
DRAFTS READY TO SEND:
  1. [Recipient] - "[Subject]" — [one-line summary of what the draft says]
  2. [Recipient] - "[Subject]" — [one-line summary]
  ...

Say "send all", "send [number]", "show [number]" to review, or "edit [number]" to revise.
```

Josh can:
- Say "send all" or "send all drafts" to send every draft
- Say "send 1, 3" to send specific drafts
- Say "show me draft for [name]" or "show [number]" to review a specific draft in chat and request edits
- Say "edit [number]" to revise a draft before sending
- Say "send [name]'s draft" for individual sends
- Open Gmail and review/send drafts manually

**NEVER auto-send. NEVER interpret ambiguous commands as "send". When in doubt, ask.**

---

## TODAY'S PRIORITIES (Post-Triage, Interactive)

**Purpose:** After all email batches are processed, help Josh set his focus for the day using the BB Tasks table. Runs after Phase 6 wrap-up, before the Sales Follow-Up Dashboard.

### Step P.1 - Query BB Tasks

Run two Airtable queries against the Tasks table (`tblmQBAxcDPjajPiE`):

**Current flags (a):** Tasks where:
- `For Today` = true
- `Assignee` contains Josh (`rec9sF1mdcCAM5g4q`)
- `Status` is NOT "Completed" and NOT "Cancelled"

**Recommendations (b):** Top 10 tasks by `Score` (descending) where:
- `Assignee` contains Josh (`rec9sF1mdcCAM5g4q`)
- `Status` is NOT "Completed" and NOT "Cancelled"
- `For Today` is NOT true (exclude already-flagged tasks)
- Prefer tasks with upcoming deadlines and linked deals

### Step P.2 - Present Priority Lists

```
TODAY'S PRIORITIES
==================

CURRENT FLAGS ([count]):
  1. [Task name] — Score: [score] | Status: [status] | Deadline: [date or "none"]
     Deal: [linked deal name, stage] (if applicable)
     DoD: [Definition of Done, truncated to one line]
  2. ...

RECOMMENDATIONS ([count]):
  A. [Task name] — Score: [score] | Status: [status] | Deadline: [date or "none"]
     Deal: [linked deal name, stage] (if applicable)
     DoD: [Definition of Done, truncated to one line]
  B. ...

COMMANDS: "keep all, add A and C" | "clear 2, add B" | "clear all, set A B C" | "search [term]" | "skip-priorities"
```

### Step P.3 - Accept Commands

Parse natural language commands for modifying the For Today list:

- **"keep all, add A and C"** — Keep existing flags, add recommended tasks A and C
- **"clear 2, add B"** — Remove flag from current task #2, add recommended task B
- **"clear all, set A B C"** — Remove all current flags, set only A, B, C as today's priorities
- **"search [term]"** — Search BB Tasks by name/notes for the term, present matches as additional options
- **"skip-priorities"** — Proceed without changes

Before applying any changes, show a diff:
```
PRIORITY CHANGES:
  + Adding: [Task name A], [Task name C]
  - Removing: [Task name 2]
  = Keeping: [Task name 1], [Task name 3]

Confirm? [yes/no]
```

**Never auto-clear flags. Always require explicit confirmation before writing.**

### Step P.4 - Write Updates to Airtable

After Josh confirms:
- Update `For Today` field in Airtable for each changed task
- Report results: "Updated [N] tasks. [Task A] and [Task C] added to today's priorities. [Task 2] removed."

If any update fails, report the error and continue with remaining updates.

---

## SALES FOLLOW-UP DASHBOARD (Post-Triage)

**Purpose:** Surface stale deals AND stale tasks linked to deals so nothing falls through the cracks. Runs after Today's Priorities.

### Deal Pulse

Query Airtable Deals table (`tblw6rTtN2QJCrOqf`) for:
- Active deals (stages 03-09) with no email activity in 7+ days
- Deals with closing dates within 14 days
- Deals where the last email was outbound from Josh with no reply

For each flagged deal, search Gmail (`from:me to:<deal_contact_email>` and `to:me from:<deal_contact_email>`) to verify staleness against actual email history.

```
DEAL PULSE (no new email, but needs attention):
  - [Org] / [Deal name]: [days] days since last contact. Stage [stage]. Closing date: [date].
  - [Org] / [Deal name]: Josh sent proposal [days] ago. No response. Consider follow-up?
```

### Task Scan

Query BB Tasks table (`tblmQBAxcDPjajPiE`) where:
- `Assignee` contains Josh (`rec9sF1mdcCAM5g4q`)
- `Status` is NOT "Completed" and NOT "Cancelled"
- Task is linked to a Deal whose status is NOT terminal (not Won/Lost/Disqualified)

**Follow-up intent detection:** Flag tasks whose name contains keywords: "follow up", "follow-up", "send email", "reach out", "check in", "check-in", "ping", "nudge", "reconnect", "touch base", "circle back", "respond to", "reply to". Mark these with `[F]`.

**Staleness tiers** (based on task `Created` date with no status change or notes update):
- **Critical (14+ days):** Red alert. Task has been sitting untouched.
- **Warning (7-13 days):** Needs attention soon.
- **Watch (3-6 days):** On the radar.

```
TASK SCAN ([count] tasks linked to active deals):
  CRITICAL (14+ days):
    T1. [F] [Task name] — [days] days stale | Deal: [deal name, stage]
        Status: [status] | Deadline: [date] | DoD: [one-line]
    T2. [Task name] — [days] days stale | Deal: [deal name, stage]
        ...

  WARNING (7-13 days):
    T3. [F] [Task name] — [days] days stale | Deal: [deal name, stage]
        ...

  WATCH (3-6 days):
    T4. [Task name] — [days] days stale | Deal: [deal name, stage]
        ...
```

`[F]` = follow-up task (contains follow-up keywords). `T#` numbering is sequential across all tiers.

### Dashboard Commands

| Command | Action |
|---|---|
| `draft T[#]` | Look up the task's linked Deal, then query Deal Contacts junction (`tbltrHekUeRLmpzGM`) to find the Contact record. Enrich with email history and Airtable data. Draft a follow-up email using Josh's style guide. Present draft for approval before creating in Gmail Drafts. |
| `expand T[#]` | Show full task context: task details, linked deal (stage, amount, assignee, closing date), contact info, last 5 email exchanges, and Contact Activity Logs (`tblgf9zD001tj6mL5`). |
| `complete T[#]` | Mark the task as "Completed" in Airtable. Confirm before writing. |
| `skip-dashboard` | Proceed to Part 2 (Dropped Ball Scan) or end session. |

After processing dashboard commands, proceed to Part 2 (Dropped Ball Scan) or wrap up if Josh declines.

---

## PART 2: DROPPED BALL SCAN (Full Gmail History Check)

**This is a SEPARATE exercise from the inbox triage above.** Part 1 (Phases 1-6 + Deal Pulse) must be fully completed first. All inbox batches processed, all drafts created, session wrap-up presented. Only THEN does Part 2 begin.

**Do NOT start the dropped ball scan while inbox triage is still in progress.** Josh will finish Part 1, review his drafts, and handle all urgent/pressing items first. The dropped ball scan is a lower-priority, broader sweep that happens after the immediate work is done.

**Purpose:** Scan Josh's entire Gmail to find anyone who contacted him and never received a reply. These are dropped balls, forgotten contacts, and lost opportunities regardless of whether emails are in the inbox or archived.

**Trigger:** Begins only after Josh has completed the full inbox triage (Part 1) and is ready. Josh may say "dropped ball scan", "check for dropped balls", "run part 2", "scan for unreplied", or similar. Can also run automatically after the Part 1 wrap-up summary is presented, with Josh's confirmation.

### Step 7.1 - Broad Inbound Email Search

Search Gmail for recent inbound emails that may have been missed or archived without reply:

- `gmail_search` with query: `to:me -from:me newer_than:30d` (start with 30-day window)
- Pull unique senders from results
- Deduplicate senders (one entry per person, regardless of how many emails they sent)

### Step 7.2 - Filter Out Noise

Remove these senders from the scan (they are not "dropped balls"):

- **Already processed in this triage session**: Any sender who appeared in the inbox batches above
- **Auto-archive patterns**: Same rules as Phase 1 Step 1.2 (LinkedIn, newsletters, cold SDR, calendar notifications, system notifications)
- **No-reply addresses**: noreply@, no-reply@, donotreply@, notifications@, mailer-daemon@
- **Bulk/transactional senders**: Emails with unsubscribe links, bulk sender headers, marketing automation platforms
- **Internal team**: Aaron, Sven, Juan, Daniel (these are handled in INTERNAL batches)
- **Known automated tools**: Calendly confirmations, Stripe receipts, Airtable notifications, GitHub, CI/CD, monitoring tools

### Step 7.3 - Reply Check

For each remaining sender, check if Josh (or his team) ever replied:

- `gmail_search` with query: `from:me to:<sender_email> newer_than:30d`
- Also check: `from:sven OR from:aaron OR from:daniel OR from:juan to:<sender_email> newer_than:30d` (team may have handled it)
- **If Josh or a team member replied in ANY thread with this person within the relevant timeframe**: Remove from dropped ball list
- **If no reply found from Josh or team**: This is a potential dropped ball. Keep it.

### Step 7.4 - Context Enrichment for Dropped Balls

For each potential dropped ball, gather lightweight context:

- **Airtable lookup**: Is this person in the CRM? What deal stage? Is the deal assigned to someone else?
- **Email content scan**: What did they email about? Is it a genuine opportunity, a question, a request?
- **How long ago**: Days since their most recent unreplied email
- **Thread count**: How many unreplied threads exist with this person?

**Filter out false positives:**
- If the deal is assigned to someone other than Josh AND that person has been actively communicating with the contact, it's not a dropped ball
- If the email was purely informational (FYI, sharing an article, no question asked, no response expected), it's not a dropped ball
- If Josh's team replied on his behalf, it's not a dropped ball

### Step 7.5 - Present Dropped Ball Report

Present findings grouped by severity:

```
DROPPED BALL SCAN (last 30 days)
=================================

URGENT (10+ days, valid contact, clear ask):
  1. [Name] ([email]) - [Company/Context]
     Last email: [date] ([days] days ago)
     Subject: "[subject]"
     > [One-line summary of what they asked/wanted]
     Deal: [stage info if in Airtable, or "Not in CRM"]
     REC: [auto-draft / respond / brainy / GTM / archive]

  2. [Name] ([email]) - [Company/Context]
     ...

MODERATE (5-10 days, or less clear intent):
  3. [Name] ([email]) - [Company/Context]
     ...

RECENT (< 5 days, may still be within normal response window):
  4. [Name] ([email]) - [Company/Context]
     ...

No dropped balls found: [count] inbound emails checked, all replied to or filtered.
```

### Step 7.6 - Command Processing for Dropped Balls

Josh can use the same command vocabulary from Phase 5:
- `auto-draft [#s]` / `draft [#s]` - Draft a reply (tone: acknowledge the delay warmly, no over-apologizing)
- `respond [#]` - Flag for personal attention
- `brainy [#]` - Schedule a meeting via Brainy
- `GTM [#s]` - Add to GTM prospect list
- `archive [#]` - Dismiss (not a real dropped ball)
- `expand [#]` - Get full context brief

**Drafting tone for dropped balls:**
- Acknowledge the delay naturally: "Hey [Name]! Wanted to circle back on this." or "Hi [Name], apologies for the delayed response."
- Do NOT over-apologize. One brief acknowledgment is enough.
- Reference what they originally asked about to show it wasn't forgotten.
- Include a clear next step or call to action.

### Step 7.7 - Adjustable Time Window

- Default scan window: 30 days
- Josh can adjust: "scan last 60 days", "check 90 days back", "dropped balls this quarter"
- For longer windows, increase filtering strictness to keep the list manageable (prioritize CRM contacts and clear asks over unknown senders)

---

## Josh Brown - Email Writing Style Guide

All drafted replies MUST match Josh's voice:

### Overall Tone & Voice
- **Conversational and Personable**: Opens with "Hey [Name]" or "Hi there". Never stiff.
- **Accessible Language**: No jargon or excessive formalities, even in professional exchanges
- **Optimistic Framing**: "Looking forward!" or "Sounds great". Future-oriented, opportunity-driven.
- **Emotionally Intelligent**: Acknowledges delays or challenges without judgment
- **Respectful Assertiveness**: Sets agendas and drives actions without over-explaining or pressuring
- **Leads with empathy**: Always considers the other person's position first

### Structure & Formatting
- **Whitespace**: Strategic paragraph breaks make content skimmable
- **Bullet Points**: Occasionally used in action-oriented emails
- **Clear Pivots**: Distinct transitions between greeting, core message, and sign-off
- **Opening**: Quick acknowledgment or purpose. "Great to connect," "Just circling back"
- **Body**: 1-3 short paragraphs or a bullet list
- **Call to Action**: Simple ask. "Does that work for you?" or "Let me know what you think"

### Signature Phrases (use naturally, don't force)
| Phrase | When to Use |
|---|---|
| Looking forward! | Upbeat sign-off that creates momentum |
| Let me know | Invites next steps without pressure |
| No problem at all | De-escalates missed meetings or miscommunication |
| Do you have any time on [day]... | Soft meeting ask, phrased to allow opt-out |
| Hey [Name]! | Standard greeting. Personal, casual, any seniority |
| Wanted to circle back | Follow-up that doesn't feel aggressive |
| Can we carve out a few mins... | Accommodating meeting proposal |
| We're excited to work with you | Partnership enthusiasm in client comms |
| Hope you're well | Standard opener for outreach or reconnection |
| Appreciate your time | Gratitude after meetings or calls |

### What NOT to Do
- No em dashes or en dashes. Ever. Use periods or commas.
- No corporate filler ("synergize", "leverage", "circle the wagons")
- No long-winded explanations. Every sentence serves a purpose.
- No stiff formality ("Dear Mr. Smith", "Please find attached herewith")
- No passive-aggressive follow-ups. Always assume good intent.
- No over-apologizing. One acknowledgment is enough.
- No manual signature/sign-off. Gmail MCP handles it automatically.

---

## REFERENCE: Airtable Schema

**Base:** Operating System (BB) (`appwzoLR6BDTeSfyS`)

| Table | ID | Key Fields |
|---|---|---|
| Deals | `tblw6rTtN2QJCrOqf` | Name, Status (pipeline stage), Organization, Amount, Assignee, Closing Date, Type, Engagement |
| Contacts | `tbllWxmXIVG5wveiZ` | Name, Email, Organization, Role |
| Organizations | `tblPEqGDvtaJihkiP` | Name, Industry, Type |
| Tasks | `tblmQBAxcDPjajPiE` | Task, Status, Assignee, Deals, Definition of Done, Notes, Created, Deadline, For Today, Score |
| Deal Contacts | `tbltrHekUeRLmpzGM` | Deal, Contact, Deal Stage |
| Contact Activity Logs | `tblgf9zD001tj6mL5` | Contact, Activity Type, Details, Created, Hash |

**Josh's BB Assignee Record ID:** `rec9sF1mdcCAM5g4q`

**Pipeline Stages:**
| Stage | Record ID |
|---|---|
| 00-Paused | recGXQK8cnJhJZmKU |
| 00-Disengaged | recd7yx8okT58BBhb |
| 01-Identified & Enriched | recPA9aoE2dZQuFQY |
| 02-Contacted | rec05mmqWkadN6TDn |
| 03-Responding | recf0FIMRj6QF9Rwb |
| 04-Soft-Qualifying | recuQkWl3niAkKBLB |
| 05-Hard-Qualifying | rec3HZUsB9prEaUGv |
| 06-Aligning Scope | recC61RlY5ZXUGylE |
| 07-Proposal Meeting Booked | recZH5Dikh3E6LhLr |
| 08-Reviewing Proposal | recbaQXMSudZjYDz0 |
| 09-Negotiating Proposal | recp517hrxj6kxJg4 |
| 10-Signed Proposal (Won) | recDEbErJd4m8PVyS |
| 11-Signed Proposal (Lost) | rec3th5vMQEyzCkxx |
| 11-Disqualified | recPQkGzdqk3XpQoC |

---

## REFERENCE: Brain Bridge Internal Team

Emails from these people are ALWAYS classified as INTERNAL:
- Aaron Eden
- Sven Plieger
- Juan Ortiz
- Daniel Lee

---

## REFERENCE: Key Contacts & Relationships

**Active Clients (from GTM):** Trip Shannan, Jim Carroll, Staff, SciTech Institute, Polychem
**Strategic Partners:** ASU SciTech, University of Arizona AZ MEP, ACA Secret Sauce, plus anyone tagged as partner/referral in Airtable

**SciTech Institute** is the primary cross-category relationship: both active customer AND long-term strategic partner. Always batch SciTech emails together across categories.
