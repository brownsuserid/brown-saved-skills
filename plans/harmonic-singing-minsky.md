# Plan: Integrate Meeting Prep, Sales Follow-ups, and Daily Priorities into Email Morning Triage

## Context

Josh's email-morning-triage skill handles inbox processing but doesn't address three critical CEO workflows: knowing what meetings are coming today, tracking stale sales tasks/deals, and setting daily priorities. Three standalone skills from core-library cover these (`preparing-for-meetings`, `managing-sales-followups`, `setting-todays-priorities`) but they were built for Aaron's Mac-based system with `gog` CLI, Telegram, and Beeper — none of which exist on Josh's Windows machine. This plan integrates their **concepts** into the triage SKILL.md using the same MCP-tool approach (Gmail MCP, Airtable MCP lookups) the triage already uses.

## Target File

`C:\Users\Brown\.claude\skills\email-morning-triage\SKILL.md` (788 lines)

## Changes

### 1. Update Frontmatter (lines 1-8) — REPLACE

Update `description` to mention meeting agenda, sales follow-up dashboard, and daily priorities. Add new trigger phrases: "what's on today", "today's agenda", "set priorities", "what should I focus on".

### 2. Update Intro Paragraph (line 12) — REPLACE

Change "Two-part system" to "Four-part system" covering: (0) today's meeting agenda, (1) inbox triage, (post-triage) priorities + sales dashboard, (2) dropped ball scan.

### 3. New PHASE 0: TODAY'S AGENDA — INSERT after line 22, before Phase 1

~55 lines. Runs first, before inbox processing.

- **Step 0.1**: Search Gmail for today's calendar events using invite/RSVP/event notification queries (no calendar API needed)
- **Step 0.2**: For each meeting, identify attendees and enrich via Airtable Contacts lookup + email history search (same pattern as Phase 2 enrichment)
- **Step 0.3**: Present compact agenda briefing with attendee context, deal info, open items, and prep notes
- If no meetings found, say so in one line and proceed to Phase 1
- Time cap: complete in under 60 seconds, don't block triage on slow lookups

### 4. New TODAY'S PRIORITIES section — INSERT after Phase 6 wrap-up (after line 571), before Deal Pulse

~60 lines. Runs after all email batches are processed.

- **Step P.1**: Query BB Tasks table (`tblmQBAxcDPjajPiE`) for (a) tasks where For Today = true, Assignee = Josh (`rec9sF1mdcCAM5g4q`), Status not terminal, and (b) top 10 recommendations by Score not already flagged
- **Step P.2**: Present numbered list (current flags) + lettered list (recommendations) with task name, score, status, deadline, linked deals, definition of done
- **Step P.3**: Accept natural language commands: "keep all, add A and C", "clear 2, add B", "clear all, set A B C", "search [term]". Show diff before applying. Require explicit confirmation.
- **Step P.4**: Write For Today field updates to Airtable. Report results.
- Never auto-clear flags. Always confirm before writing.

### 5. Replace DEAL PULSE with SALES FOLLOW-UP DASHBOARD — REPLACE lines 574-589

~65 lines. Expands the existing 15-line Deal Pulse into a full dashboard.

**Deal Pulse (kept):** Same queries — active deals with no email activity in 7+ days, deals with closing dates within 14 days, unanswered outbound emails.

**Task Scan (new):** Query BB Tasks where Assignee = Josh, Status not terminal, linked to non-terminal deals. Categorize:
- Follow-up intent detection via task name keywords ("follow up", "send email", "reach out", "check in", etc.)
- Staleness tiers: Critical (14+), Warning (7-13), Watch (3-6)
- Present with `[F]` marker for follow-up tasks, `T#` numbering

**Dashboard Commands (new):**
- `draft T[#]` — enrich via Deal Contacts junction (`tbltrHekUeRLmpzGM`) → Contact record, draft follow-up email using Josh's style guide
- `expand T[#]` — full task context with deal, contact, email history, activity logs (`tblgf9zD001tj6mL5`)
- `complete T[#]` — mark task Completed in Airtable
- `skip-dashboard` — proceed to next section

### 6. Update Airtable Schema Reference (lines 746-750) — APPEND

Add three new table rows:
- Tasks: `tblmQBAxcDPjajPiE` (Task, Status, Assignee, Deals, Definition of Done, Notes, Created, Deadline, For Today, Score)
- Deal Contacts: `tbltrHekUeRLmpzGM` (Deal, Contact, Deal Stage)
- Contact Activity Logs: `tblgf9zD001tj6mL5` (Contact, Activity Type, Details, Created, Hash)

Add: **Josh's BB Assignee Record ID:** `rec9sF1mdcCAM5g4q`

## New Flow Order

1. **PHASE 0: TODAY'S AGENDA** (new)
2. PHASE 1: FETCH & FILTER (unchanged)
3. PHASE 2: CLASSIFY & ENRICH (unchanged)
4. PHASE 3: CLUSTER INTO BATCHES (unchanged)
5. PHASE 4: PRESENT TO JOSH (unchanged)
6. PHASE 5: COMMAND PROCESSING (unchanged)
7. PHASE 6: SESSION WRAP-UP (unchanged)
8. **TODAY'S PRIORITIES** (new)
9. **SALES FOLLOW-UP DASHBOARD** (replaces Deal Pulse)
10. PART 2: DROPPED BALL SCAN (unchanged)
11. Reference sections (schema updated)

## Estimated Impact

- ~170 lines added, ~15 removed (old Deal Pulse)
- Final file: ~943 lines
- No new dependencies — uses same Gmail MCP + Airtable MCP tools already in use

## Verification

After editing, trigger "triage" or "morning email" in a new Claude Code session and confirm:
1. Phase 0 searches Gmail for calendar events and presents agenda (or "no meetings" message)
2. Phases 1-6 work exactly as before (no regressions)
3. After Phase 6 wrap-up, priorities section presents For Today tasks and recommendations
4. Sales dashboard presents stale deals AND stale tasks with T# numbering
5. `draft T[#]` resolves contact via Deal Contacts junction and generates a draft
6. Part 2 dropped ball scan still works after all new sections
