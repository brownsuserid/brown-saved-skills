---
name: Airtable Deletion Safety Rule
description: NEVER delete Airtable records without first listing every specific record (name, ID, table) and getting explicit approval
type: feedback
---

Never delete anything in Airtable without first giving Josh full context on exactly what will be deleted.

**Why:** Josh needs to verify each record before it's removed. Bulk deletions without itemized review risk losing data.

**How to apply:** Before ANY Airtable delete_records call, list every record by name, record ID, and table. Wait for explicit "yes, delete those" approval. Never batch deletions into background agents where Josh can't review them before execution.
