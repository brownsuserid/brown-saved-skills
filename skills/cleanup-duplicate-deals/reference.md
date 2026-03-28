# cleanup-duplicate-deals

Detect and merge duplicate deal records in Airtable.

## Scripts

### cleanup_deals.py
Fetches all deals, groups by normalized name (stripping "Name: " prefix), identifies shell duplicates (records missing Organization/Contact/Status/Assignee/Type), moves their Notes to the primary record, and deletes the shells. Default is `--dry-run`; use `--execute` to apply. Use `--deal` to target a single deal name. Supports `--config` and `--base` flags.

## Dependencies
- airtable-config (sibling skill)
- AIRTABLE_TOKEN env var
