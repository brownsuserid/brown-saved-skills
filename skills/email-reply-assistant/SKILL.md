---
name: email-reply-assistant
description: Helps compose informed email replies by gathering context from Gmail history, Airtable CRM, and meeting transcripts. Use when the user wants to reply to an email, draft a response, or says things like "reply to [person]", "draft email to [person]", "respond to that email from [person]". Also invoked from the email-morning-triage skill when Josh says "respond to #X".
---

# Email Reply Assistant
Helps compose informed email replies by gathering context from Gmail history, Airtable CRM data, and meeting transcripts.

## Trigger
Use when the user wants to reply to an email, draft a response, or says things like "reply to [person]", "draft email to [person]", "respond to that email from [person]".

Also invoked from the `email-morning-triage` skill when Josh uses the "respond" command during triage.

## Operating Modes

### Standalone Mode (default)
Full workflow: find thread, gather context, ask for objective, draft reply. Used when Josh invokes this skill directly outside of triage.

### Triage Mode
When invoked from the email-morning-triage skill, the thread is already identified and context has been partially gathered. In triage mode:
- **Skip Step 1** (thread already identified from triage batch)
- **Skip thread confirmation** (Josh already selected this item)
- **Step 5 (objective)**: Infer objective from triage context (deal stage, email content, recommendation). Still present the context summary and ask "What's your goal for this reply?" but offer a suggested objective based on context.
- **Airtable context**: Should already be available from triage enrichment. If not, query it fresh.

## Workflow

### Step 1: Find the Email Thread (Standalone Mode Only)
- Use `gmail_search` to find recent emails matching the user's description (person name, subject, etc.)
- Present the top results with sender, subject, and date
- Ask the user: "Which thread should I work with?"
- Wait for confirmation before proceeding
- **In triage mode: SKIP this step.** Thread ID is already known.

### Step 2: Read the Full Thread
- Use `gmail_get_thread` to read the confirmed thread in full
- Summarize the thread briefly for the user (key points, what the latest message says, what action is expected)

### Step 3: Pull Email History with That Person
- Use `gmail_search` to find past emails with the same sender/recipient (e.g., `from:<email>` or `to:<email>`)
- Read the most recent 5-10 past threads to understand the relationship context and prior conversations
- Note any recurring topics, tone, and relationship dynamics

### Step 3.5: Pull Airtable CRM Context
Search Airtable for the sender/recipient to enrich the reply context:

1. **Contacts table** (`tbllWxmXIVG5wveiZ`): Search by email address for contact record (name, role, org link)
2. **Organizations table** (`tblPEqGDvtaJihkiP`): Pull org details (industry, type, relationship classification)
3. **Deals table** (`tblw6rTtN2QJCrOqf`): Search for linked deals. For each deal, note:
   - Stage name and days in current stage
   - Deal amount and closing date
   - Assignee (is this Josh's deal or delegated?)
   - Engagement level
   - Pain points (from deal description)

Present Airtable context alongside email/transcript context in Step 5. This helps Josh (and the draft) understand where the relationship stands in the pipeline.

**In triage mode:** This data may already be cached from triage enrichment. Use cached data if available, query fresh if not.

### Step 4: Search Brainy's Brain for Transcripts
Search the "Brainy's Brain" transcript folder (ID: `1DEgcy3ygv9-tkbgTByQPH5VvB-WrLyar`) for meeting transcripts related to the person.

**How to search — use Drive query syntax, NOT free-text search:**
- Use `drive_search` with queries like: `'1DEgcy3ygv9-tkbgTByQPH5VvB-WrLyar' in parents and name contains '<term>'`
- Free-text `drive_search` (e.g., "Benoit transcript") is unreliable for finding transcripts — always search by **name within the folder**

**Search with multiple name variations (run in parallel):**
- Person's first name (e.g., "Ben")
- Person's full/formal name (e.g., "Benoit", "Benoît")
- Person's last name (e.g., "Bourgeois")
- Company or project name (e.g., "VDK")
- Short nicknames if known from email signatures or prior context

**Transcript naming conventions** (titles vary — cast a wide net):
- `"Josh Brown & Benoît le Bourgeois - Investor Deck/Transcript- 2026-02-19"`
- `"Brain Bridge & VDK/Transcript- 2025-12-19"`
- `"Josh/Ben/Transcript- 2025-10-23"`
- `"1 Hour Meeting w/ Josh Brown, Brain Bridge & (Benoît le Bourgeois)/Transcript- 2025-12-22"`

**Prioritize the 2-3 most recent transcripts** — sort results by date and focus on recency.

**Reading large transcripts efficiently:**
- Transcripts are often 100K+ characters — do NOT read the full document into context
- Use `drive_export` with `text/plain` to get raw text, then save to a temp file
- Use `Grep` to search the saved file for keywords relevant to the email thread (names, topics, companies mentioned)
- Read only the surrounding context (50-100 lines) around matched keywords
- If the transcript is small (<15K chars), reading it fully is fine

### Step 5: Ask for the Email Objective
- Present a summary of all gathered context:
  - Current thread summary
  - Key points from past email history
  - Airtable CRM context (deal stage, amount, engagement, pain points)
  - Relevant highlights from meeting transcripts
- **Standalone mode:** Ask the user: "What is your objective for this reply? What outcome do you want?" Wait for response.
- **Triage mode:** Present context summary AND a suggested objective based on deal stage + email content. For example: "Based on the deal being at 06-Aligning Scope and Jim's question about API limits, I'd suggest the objective is: reassure on technical capability and push for a validation call. Sound right, or do you want to take it a different direction?" Wait for confirmation or redirection.

### Step 6: Analyze and Draft
- Analyze the transcripts and email history for key themes and points related to the stated objective
- Draft a reply that is:
  - Low cognitive load (short paragraphs, clear structure, easy to scan)
  - Grounded in specific details from transcripts and prior conversations
  - Aligned with the stated objective
  - Matching the tone and style of the user's past emails
- Present the draft to the user

### Step 7: Dash Check
Before presenting any draft to the user, scan every sentence for em dashes (—) and double dashes (--). These are NOT allowed in Josh's emails.

**What to do:**
- Search the draft for `—` and `--`
- For each affected sentence, rewrite it to eliminate the dash entirely. Do NOT simply replace with a hyphen. Restructure the sentence using commas, periods, or different phrasing.
- Re-read the full draft after rewriting to confirm zero dashes remain

**Examples:**
| Before | After |
|---|---|
| "One thought for next steps — I'd love to bring Aaron in." | "One thought for next steps. I'd love to bring Aaron in." |
| "Really enjoyed Thursday — there's a ton of synergy." | "Really enjoyed Thursday. There's a ton of synergy here." |
| "He had John Deere HQ as a client -- so ag-tech isn't new to him." | "He actually had John Deere HQ as a client, so ag-tech isn't new to him." |

### Step 8: Edit and Send
- The user reviews and requests edits for personalization
- Apply any requested changes
- When the user confirms, use `gmail_reply` to send the email
- Confirm the email was sent successfully

## Josh Brown – Email Writing Style Guide

All drafted replies MUST match Josh's voice. Study these patterns and apply them consistently.

### Overall Tone & Voice
Josh blends informal warmth with business clarity. Confident but never pushy, optimistic but not naive. Human-first. He writes like he speaks, with rhythm, slight humor, and encouragement.

- **Conversational and Personable**: Opens with "Hey [Name]" or "Hi there" — never stiff or overly formal
- **Accessible Language**: No jargon or excessive formalities, even in professional exchanges
- **Optimistic Framing**: "Looking forward!" or "Sounds great" — future-oriented, opportunity-driven
- **Emotionally Intelligent**: Acknowledges delays or challenges without judgment
- **Respectful Assertiveness**: Sets agendas and drives actions without over-explaining or pressuring

### Structure & Formatting
Short to medium length, well-spaced, easy to scan. Even longer emails feel lightweight due to clear formatting and varied sentence lengths.

- **Whitespace**: Strategic paragraph breaks make content skimmable
- **Bullet Points**: Occasionally used in action-oriented emails
- **Clear Pivots**: Distinct transitions between greeting, core message, and sign-off
- **Signature**: Ends with "Josh", "Looking forward!", or "-Brown" depending on audience formality
- **Opening**: Quick acknowledgment or purpose — "Great to connect," "Just circling back"
- **Body**: 1-3 short paragraphs or a bullet list for availability, ideas, or updates
- **Call to Action**: Simple ask — "Does that work for you?" or "Let me know what you think"

### Signature Phrases (use naturally, don't force)
| Phrase | When to Use |
|---|---|
| Looking forward! | Upbeat sign-off that creates momentum |
| Let me know | Invites next steps without pressure |
| No problem at all | De-escalates missed meetings or miscommunication |
| Do you have any time on [day]… | Soft meeting ask, always phrased to allow opt-out |
| Hey [Name]! | Standard greeting — personal, casual, any seniority |
| Morning Man! | High-familiarity, close internal contacts only |
| Wanted to circle back | Follow-up that doesn't feel aggressive |
| Can we carve out a few mins… | Accommodating meeting proposal |
| That actually strengthens your direction | Supporting others while giving input |
| We're excited to work with you | Partnership enthusiasm in client comms |
| Hope you're well | Standard opener for outreach or reconnection |
| Appreciate your time | Gratitude after meetings or calls |
| Totally my bad on this one | Owns mistakes with lightness |
| Here's the link | Signals immediacy when sharing resources |

### What NOT to Do
- No corporate filler or buzzwords ("synergize", "leverage", "circle the wagons")
- No long-winded explanations — every sentence serves a purpose
- No stiff formality ("Dear Mr. Smith", "Please find attached herewith")
- No passive-aggressive follow-ups — always assume good intent
- No over-apologizing — one acknowledgment is enough

## Gmail Signature Handling
The Gmail MCP server automatically appends the user's configured Gmail signature (fetched from Gmail Settings API) to all outgoing emails — drafts, replies, and sends. No manual signature handling is needed.

1. **Do NOT include a manual sign-off in the email body** (no "Josh", "- Josh", "Best, Josh", etc.). The Gmail signature already contains the name, title, and contact info.
2. **End the email body with the last line of actual content.** The signature is appended automatically by the MCP server.
3. **Do NOT hardcode or append any signature HTML.** The server fetches and caches the exact signature from Gmail settings, preserving all formatting, images, and icons.

## Important Notes
- Always wait for user confirmation before sending any email. NEVER auto-send.
- NEVER remove anyone from CC or BCC. If someone is on the thread, they stay. Only ADD CCs when specifically called for.
- NEVER modify Gmail labels. Labels are read-only.
- Reference specific details from transcripts and Airtable data to make the email feel informed and personal
- If no transcripts are found, proceed with email history and Airtable context only and let the user know
- When in triage mode, coordinate with the email-morning-triage skill's batch context
