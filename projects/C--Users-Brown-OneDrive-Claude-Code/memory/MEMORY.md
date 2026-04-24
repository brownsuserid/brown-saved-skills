# Memory

## Critical Rules

- **NEVER send an email without explicit written permission from Josh in the chat.** Drafting is fine, but sending requires Josh to clearly say "send it" or equivalent. "Do it" in response to a draft means finalize the draft, NOT send it. When in doubt, ask. Do not send.
- **NEVER use dashes of ANY kind in emails.** No em dashes, en dashes, double dashes (--), or single hyphens used as dashes. Use periods, commas, or rewrite the sentence instead. Compound words with hyphens (e.g., "follow-up") are fine.
- **ALL emails must have proper newlines/blank lines between paragraphs.** No wall-of-text formatting. Every paragraph must be separated by a blank line with hard returns.
- **ALWAYS show Josh the draft text in chat BEFORE creating it in Gmail drafts.** Wait for his approval or edits, then save to drafts.
- **When archiving emails, remove ALL inbox-related labels:** INBOX, Check-Brown, Urgent-Brown, and Read-Brown. Do not add any labels. Do not modify non-inbox labels.
- **NEVER remove anyone from CC or BCC.** If someone is on the thread, they stay on the thread. Only ADD a CC when specifically called for (e.g., adding Brainy). Never subtract.

## Terminology

- **"Inbox"** = Any email with one of these labels: **INBOX**, **Check Brown**, **Urgent Brown**, or **Read Brown**. When listing or processing the inbox, search for all four labels.

## Email Processing Format

When processing inbox emails one at a time, present each email in this structure:
- **Sender**
- **Subject**
- **Full Previous Message** (the actual email body)
- **Summary of Previous Thread** (if any prior messages in the thread)
- **Recommendation** (archive, leave unread, draft reply, etc.)

### Auto-rules during inbox processing:
- Present noise emails (LinkedIn, cold sales, newsletters, calendar notifications) for Josh's approval BEFORE archiving
- Archive emails where the deal is assigned to someone other than Josh in Airtable AND Josh is only CC'd (not in To line)
- When archiving, remove ALL inbox labels (INBOX, Check-Brown, Urgent-Brown, Read-Brown)

## Shortcuts

- **"Add Brainy"** = CC brainy-brown@lindymail.ai on the reply. Introduce Brainy as "our AI operations manager" who will help find a day and time to meet. Default meeting length is 30 minutes unless Josh specifies otherwise.

## Brain Bridge Internal Team
- Aaron Eden
- Sven Plieger
- Juan Ortiz
- Daniel Lee

## Triage Schedule
- **Morning triage:** 7:00 AM cron pre-processes data; Josh triggers "triage" when ready
- **Afternoon triage:** 12:00 PM identical full triage, same format

## Airtable CRM

- **Base:** Operating System (BB) (`appwzoLR6BDTeSfyS`)
- **Deals table:** `tblw6rTtN2QJCrOqf`
- **Contacts table:** `tbllWxmXIVG5wveiZ`
- **Organizations table:** `tblPEqGDvtaJihkiP`
- See [airtable-fields.md](airtable-fields.md) for full field reference.

### Creating Deals (ALWAYS create all 3 records)
Every deal requires **3 linked records**: Organization, Contact, and Deal. No exceptions.

When Josh asks to create a deal:
1. Extract sender name, email, title, company from the email signature/headers.
2. Search the web for the sender's company to gather: industry, size, location, description.
3. Search Airtable for existing Contact and Organization records. Link if found; note if new ones are needed.
4. Pre-populate all 3 records with as much data as possible.
5. Present a summary of all proposed fields to Josh for confirmation before creating.
6. Create in order: Organization first, then Contact (linked to Org), then Deal (linked to Org). Stage defaults to "02-Contacted" if an email has been sent.

## Airtable Safety Rules
- [Airtable Deletion Safety Rule](feedback_airtable_deletions.md) - NEVER delete records without listing every specific record and getting explicit approval first

## User Profile & Triage System
- [Josh Brown CEO Profile](user_josh_profile.md) - role, team, key contacts, communication style
- [Email Triage & Auto-Draft Rules](feedback_email_triage_rules.md) - auto-draft behavior, batch processing, GTM handling, command vocabulary
- [Triage Pagination Rule](feedback_triage_pagination.md) - MUST paginate all inbox search results to avoid missing older emails

## Contact Routing
- [Kirsten Iversen → Aaron Eden](feedback_kirsten_iversen_aaron.md) - All Kirsten Iversen tasks/campaigns assigned to Aaron, not Josh

## Triage Flow
- [Auto-pull next thread after archiving](feedback_triage_auto_pull.md) - After archiving a batch, always pull next thread automatically, never ask first
