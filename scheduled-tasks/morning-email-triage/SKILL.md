---
name: morning-email-triage
description: Morning email triage pre-processing: fetches inbox, cross-references Airtable, enriches with transcripts, and presents triage dashboard.
---

Run the email-morning-triage skill. This is the 7 AM morning triage session.

Execute the full triage workflow:
1. Fetch all inbox emails (labels: INBOX, Check Brown, Urgent Brown, Read Brown)
2. Auto-archive noise (LinkedIn, cold outreach, newsletters, calendar notifications, delegated relationships)
3. Classify each remaining email using Airtable CRM data (Contacts, Organizations, Deals tables)
4. Enrich with context: deal stage, email history, transcript highlights, staleness indicators
5. Cluster into relationship-based batches
6. Present the triage dashboard and wait for Josh's commands

Use the email-morning-triage skill for the complete workflow instructions.