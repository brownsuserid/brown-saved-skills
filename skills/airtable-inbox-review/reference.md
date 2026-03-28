# Airtable Inbox Review

> Scripts: `~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/`

## Overview

This skill triages and **routes** items from all inboxes into the right Airtable projects. The goal is inbox zero through routing, not deep work. Every item should end up in a project unless it can be handled with a quick, trivial action right now (archive, one-line reply, etc.).

Works **one inbox at a time** to keep the conversation manageable.

**Flow:** Airtable tasks -> Email -> Beeper. Each step gathers, triages, routes, and waits for Aaron's input before moving to the next.

**Core principle:** For each item, ask: "Can this be resolved in under 30 seconds?" If yes, handle it inline (archive, quick reply, mark done). If no, route it to the right project as a task. Everything gets sorted somewhere.

---

## Step 1: Airtable Inbox Tasks

### 1a. Gather

Run the gather script. It outputs structured JSON to stdout.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_inbox.py
```

Returns:
- `bases.personal` / `bases.aitb` / `bases.bb`, arrays of inbox tasks per base
- `summary.total_inbox_tasks`, total count
- `summary.per_base`, count per base

Each task includes: `id`, `task`, `description`, `status`, `score`, `due_date`, `notes`, `base`, `airtable_url`, `assignee_ids`, `project_ids`, `project_status`.

**`project_status` values:**
- `"unrouted"`, no project linked at all
- `"inbox"`, linked to the base's Inbox project (needs routing)
- `"routed"`, already has a real project (included for completeness, rare in inbox results)

**Scope filter** (applied in the script): Only includes tasks with no assignee, or assigned to Aaron or Pablo. Skips tasks assigned to other team members (Juan, Josh, Sven).

### 1b. Triage and Route

For each task, decide: **handle now** or **route to a project**.

**Handle now** (under 30 seconds): Task is trivially completable right here. Examples: mark a duplicate done, add a missing DoD that's obvious from the title, archive something stale. Flag these for inline action.

**Route to a project** (everything else): Determine the right project using [routing-airtable-tasks.md](routing-airtable-tasks.md).

For tasks with `project_status` of `"unrouted"` or `"inbox"`, follow the routing workflow:
1. Identify candidate bases from task context
2. Explore goals using `scripts/query_goals.py`
3. Explore projects using `scripts/query_projects.py`
4. Determine best fit (Strong match / Possible match / No match)
5. Return routing decision with confidence level

**Batch optimization:** Group similar tasks and query goals/projects once per base rather than per task.

**Clarity check** (while routing): If the task is vague or missing a Definition of Done, note it alongside the routing recommendation. Don't make clarity a separate category. Just flag it: "Route to X, but needs a clearer DoD."

### 1c. Present and Pause

Format and deliver the Airtable section:

```
AIRTABLE INBOX ({N} tasks)
Personal: {n} | AITB: {n} | BB: {n}

HANDLE NOW ({n})
---
{#}. base | task name
    Link: {airtable_url}
    Action: {what to do, e.g. "Mark complete (duplicate of X)", "Add DoD: ..."}

ROUTE ({n})
---
{#}. base | task name | score
    Link: {airtable_url}
    -> {Project Name} ({Confidence})
    {If needs clarity: "Note: needs clearer DoD - suggested: ..."}
    {If no match: "Needs new project - Suggested: Project Name"}
```

**Numbers are sequential across both sections** (HANDLE NOW starts at 1, ROUTE continues the count).

**Then ask:** "Want me to apply these routes? Anything to change?"

**Wait for Aaron's response.** Apply approved routing and inline actions. Then proceed to Step 2.

**If zero Airtable inbox tasks:** Say "Airtable inbox is clean." and move directly to Step 2.

---

## Step 2: Email Inbox

### 2a. Gather

Run the email gather script. It fetches inbox emails from 3 Gmail accounts via the `gog` CLI and outputs structured JSON to stdout.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_emails.py [--max 50] [--accounts personal,bb,aitb]
```

**Do not use `--since`.** Inbox processing must catch everything still in the inbox regardless of age. Old emails sitting in the inbox are exactly the items that need triage.

**Accounts:**

| Alias | Email | Airtable Base |
|-------|-------|---------------|
| personal | aaroneden77@gmail.com | personal |
| bb | aaron@brainbridge.app | bb |
| aitb | aaron@aitrailblazers.org | aitb |

**CLI flags:**
- `--max N`, Max emails per account (default: 50)
- `--accounts alias,alias`, Comma-separated aliases to query (default: all 3)
- `--since Nd`, Only emails newer than N days. **Do not use for inbox processing.** Reserved for targeted queries only.

**Returns:**
- `accounts.personal` / `accounts.bb` / `accounts.aitb`, arrays of email objects per account
- `summary.total_emails`, total count
- `summary.per_account`, count per account
- `summary.unread_count`, total unread emails

Each email includes: `thread_id`, `message_id`, `account`, `email_address`, `from`, `from_name`, `to`, `subject`, `date`, `snippet` (200 chars), `body_text` (truncated at 2000 chars), `labels`, `has_attachments`.

**Graceful degradation:** If a single account fails (e.g., OAuth token expired), the error is logged to stderr and other accounts continue.

### 2b. Apply Auto-Rules

Pipe the gathered email JSON through `apply_rules.py`. This script loads `learned_mappings.json` -> `email_rules`, regex-matches each email's `from` address, and archives matches via `gog` CLI automatically. Remaining (unmatched) emails are output as JSON for triage.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_emails.py | \
  python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/apply_rules.py
```

Use `--dry-run` to preview what would be archived without executing.

The output JSON includes an `auto_processed` section with count and item details. Matched emails are excluded from `accounts` and the `summary` totals are recalculated. If an archive fails, the email is put back into the remaining list so it appears in triage.

**This step is mandatory.** Always run `apply_rules.py` in the pipeline. Never skip it and triage manually.

### 2c. Triage and Route

For each remaining email, decide: **handle now** or **route to a project**.

**Handle now** (under 30 seconds):
- Archive: newsletters, notifications, FYI, no action needed
- Quick reply: one-line acknowledgment, simple yes/no, "thanks"
- Note and archive: waiting-for updates, status notifications

**Bounce-back / Delivery Failure:** When an email is a delivery failure notification (from mailer-daemon, "Delivery Status Notification", "Address not found", etc.), handle inline:
1. Identify the original message: read the bounce to determine who it was sent to, what the subject was, and which account sent it
2. Research the correct address: look up the recipient in contacts (`search_contacts.py`), check Airtable deals/orgs, and web search for their current email
3. If a correct address is found: resend the original message to the new address (draft only), archive the bounce
4. If no correct address is found but an alternative channel exists (LinkedIn, Beeper, phone): flag it with the alternative channel and draft an outreach via that channel instead
5. If no address or alternative channel can be found and the email was sales-related: mark the associated deal as lost in Airtable and archive the bounce
6. Present all bounce findings together in a BOUNCED section before the HANDLE NOW section

**Route to a project** (everything else): Determine the right base and project, then create an Airtable task.
- Action Required: email needs Aaron to do something substantial
- Reply Needed: needs a thoughtful response (create task, draft reply later)
- Delegate: action needed from someone else (create task with assignee)
- **Scheduling Request:** If someone is asking to meet, schedule a call, or find time with Aaron, flag it as "COORDINATE" and reference `maintaining-relationships/references/coordinating-meeting-times.md`. Do not create a generic "reply to scheduling email" task. Instead, present it as a coordination action so Aaron can kick off the meeting coordination workflow directly.

**Assessment criteria:**
- Sender: known contact vs unknown, internal vs external
- Is there a question directed at Aaron?
- Is there a deadline or time-sensitivity signal?
- Does it relate to an existing Airtable project/task?
- Is it automated/notification vs human-written?

**For each email that needs routing, determine:**
1. Which base and project to route to
2. Suggested task title and assignee
3. Priority (high/medium/low)

### 2d. Present and Pause

Format and deliver the Email section:

```
EMAIL INBOX ({N} emails across {n} accounts)
Personal: {n} | BB: {n} | AITB: {n}
{If auto-processed: "Auto-processed: {n} (newsletters/notifications)"}

BOUNCED ({n})
---
{#}. account | original recipient | original subject | date
    Failed address: {bounced_email}
    Research: {what was found: new address / alternative channel / nothing}
    Action: {resend to new address (draft) / outreach via {channel} / mark deal "{deal_name}" as lost}

HANDLE NOW ({n})
---
{#}. account | from | subject
    Action: {archive / quick reply: "..." / note and archive}

ROUTE TO PROJECT ({n})
---
{#}. account | from | subject | date
    -> {Base}: {Project Name} | Task: "{suggested title}" | Assignee: {name}
    {If reply needed: "Draft reply: {summary}"}
```

**Numbers are sequential across both sections** (HANDLE NOW starts at 1, ROUTE continues the count). Aaron can reference items by number, e.g. "archive 1-3, create tasks for 4 and 6, draft reply for 5".

**Then ask:** "Want me to handle the quick ones and create tasks for the rest?"

**Wait for Aaron's response.** Execute approved actions. Then proceed to Step 3.

**If zero emails:** Say "Email inboxes are clean." and move directly to Step 3.

---

## Step 3: Beeper Messages

### 3a. Gather

Run the Beeper gather script. It fetches unread chats via the Beeper MCP server (through `beeper-read.sh`) and outputs structured JSON to stdout.

```bash
python3 ~/.openclaw/skills/managing-projects/scripts/airtable-inbox-review/gather_beeper.py [--limit 50] [--since 2026-02-01T00:00:00Z]
```

**CLI flags:**
- `--limit N`, Max unread chats to fetch (default: 50)
- `--since ISO`, Only include chats with activity after this ISO timestamp

**Returns:**
- `chats`, array of chat objects, each with `chat_id`, `name`, `messages`, `message_count`
- `summary.total_unread_chats`, total unread chat count
- `summary.total_messages`, total message count across all chats

Each message includes: `sender_id`, `is_sender`, `timestamp`, `text`.

**Graceful degradation:** If the Beeper MCP server is unavailable, the error is logged to stderr and an empty result is returned.

### 3b. Triage and Route

For each unread chat, decide: **handle now** or **route to a project**.

**Handle now:** FYI messages, simple acknowledgments, messages that just need a read.

**Route to a project:** Someone is waiting on Aaron for something that takes real effort. Create an Airtable task in the right project.

### 3c. Present and Pause

Format and deliver the Beeper section:

```
BEEPER ({N} unread chats, {M} messages)

HANDLE NOW ({n})
---
{#}. chat name | last message snippet | timestamp
    Action: {FYI (no action) / quick reply: "..."}

ROUTE TO PROJECT ({n})
---
{#}. chat name | last message snippet | timestamp
    -> {Base}: {Project Name} | Task: "{suggested title}" | Assignee: {name}
```

**Numbers are sequential across both sections.**

**Then ask:** "Want me to create these tasks? Any replies?"

**Wait for Aaron's response.** Execute approved actions.

**If zero unread chats:** Say "Beeper is clean."

---

## Step 4: Wrap Up

After all three inboxes are processed, present a brief summary of what was done:

```
INBOX REVIEW COMPLETE
---
Airtable: {n} tasks reviewed, {n} routed, {n} updated
Email: {n} reviewed, {n} archived, {n} tasks created, {n} drafts created
Beeper: {n} chats reviewed
```

Only show this if actions were taken. If Aaron skipped everything, just say "Done."

---

## Executing Approved Actions

These actions apply across all steps when Aaron approves them.

### Email Actions

**Archive emails:**
```bash
gog gmail labels modify <threadId> --remove-labels "INBOX" --account <email>
```

**Batch archive (by account for efficiency):**
```bash
gog gmail batch modify <messageId1> <messageId2> ... --remove-labels "INBOX" --account <email>
```

**Create Airtable task from email** (must meet quality standard, see [creating-tasks.md](creating-tasks.md)):
```bash
python3 ~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py \
  --base <base> \
  --title "Review vendor proposal from Acme Corp for Q2 services" \
  --description "Done when proposal is reviewed, pricing compared to budget, and recommendation drafted for Aaron." \
  --assignee aaron \
  --project <projectRecordId> \
  --due-date "2026-02-18" \
  --for-today \
  --notes "Source: https://mail.google.com/mail/u/0/#inbox/<threadId>"
```

Field guidance for email-derived tasks:
- **Title:** Action verb + specific subject from the email
- **Description:** Observable outcome, what "done" looks like for this email action
- **Assignee:** Default to `aaron` unless explicitly specified otherwise
- **Project:** Route via `routing-airtable-tasks` if no obvious project fit
- **Due date:** Set when the email mentions a deadline or time-sensitive request
- **For Today:** Set for high-priority emails (assessed as "Action Required" with high priority)

**Draft reply to email:**
```bash
python3 ~/.openclaw/skills/using-gog/scripts/draft_email.py \
  --account <personal|bb|aitb> \
  --to <sender_email> \
  --subject "Re: <original_subject>" \
  --body "Body text here..." \
  --reply-to-message-id <messageId>
```
The script appends the correct account signature automatically. Use `--no-signature` if the body already includes one.

### Execution Rules

- Email actions require explicit approval from Aaron
- Replies are created as **drafts only**, never sent directly
- All email-derived tasks include the Gmail URL in Notes for traceability: `Source: https://mail.google.com/mail/u/0/#inbox/<threadId>`
- Batch archive by account for efficiency (group all approved archives per account into one batch modify call)
- Report execution results: count of archived, tasks created, drafts created, any failures

---

## Formatting Rules

- No emoji in the output
- Always show both the task name as plain text AND the Airtable URL on a separate "Link:" line
- Keep it scannable, no paragraphs, use lists and tables
- Sort tasks by score descending within each section
- Sort emails by priority (high first), then date (newest first)

---

## Guardrails

- **Read-only by default**: Scripts only read data; no modifications without approval
- **No modifications without confirmation**: Routing recommendations and email actions are suggestions only; Aaron approves changes
- **Drafts only**: Email replies are created as drafts, never sent directly
- **Beeper requires approval**: Beeper messages are NEVER sent without explicit approval. Present the proposed message text and wait for Aaron to confirm before calling beeper-send.sh.
- **Graceful degradation**: If any gather script fails for an account/base, report the error and skip that source
- **No hardcoded tokens**: Airtable auth uses `AIRTABLE_TOKEN` env var via `_config.py`; Gmail auth managed by `gog` CLI (already authenticated)
- **Shared infrastructure**: Reuses `_shared/_config.py` for all base IDs, people IDs, and API helpers
- **Traceability**: All email-derived Airtable tasks include the Gmail URL in Notes

---

## Integration

- **Cron**: Runs daily at 3:00 PM Arizona time via openclaw cron
- **Delivery**: In-chat (direct to conversation)
- **Reused config**: All Airtable base IDs, people IDs, and API helpers come from `_shared/_config.py`
- **Routing delegation**: Uses routing-airtable-tasks, see [routing-airtable-tasks.md](routing-airtable-tasks.md)
- **Gmail access**: Via `gog` CLI (see `~/.openclaw/skills/using-gog/SKILL.md`)
- **Task creation**: Via `~/.openclaw/skills/managing-projects/scripts/executing-tasks/create_task.py`

---

## Scripts Reference

| Script | Purpose | Dependencies |
|--------|---------|-------------|
| `gather_inbox.py` | Fetch inbox tasks from all 3 Airtable bases with scope filtering and pagination | `_shared/_config.py` |
| `gather_emails.py` | Fetch inbox emails from 3 Gmail accounts via `gog` CLI | `gog` CLI (authenticated) |
| `apply_rules.py` | Apply auto-rules from `learned_mappings.json`, archive matches, output remaining | `gog` CLI, `learned_mappings.json` |
| `gather_beeper.py` | Fetch unread Beeper messages via Beeper MCP server | `beeper-read.sh`, `BEEPER_TOKEN` env var |
