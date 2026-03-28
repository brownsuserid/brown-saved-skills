# Deal Lookup Skill

Search for deals across Brain Bridge and AITB Airtable bases with fuzzy matching and deduplication.

## Usage

```bash
# Search for a deal by name or company
python search_deals.py "Acme"

# Show only open deals
python search_deals.py "Acme" --open

# Filter to a specific base
python search_deals.py "Acme" --base bb

# JSON output
python search_deals.py "Acme" --json --open
```

## Sources Searched

1. **Brain Bridge Airtable** - Deals (`tblw6rTtN2QJCrOqf`)
   - Searches by deal Name
   - Types: New Business, Existing Business, Partner
2. **AITB Airtable** - Sponsor Deals (`tblRb57pOJaYsW6u5`)
   - Searches by Project Title and Organization Name (lookup)
   - All deals are sponsor type

## Scripts

- `search_deals.py` - Main entry point, orchestrates searches across both bases with fuzzy matching

Located at:
```
~/.openclaw/skills/maintaining-relationships/scripts/looking-up-deals/
```

## Configuration

Environment variables:
- `AIRTABLE_TOKEN` - **Required.** API token for Airtable
- `BB_BASE_ID` - Brain Bridge base ID (default: appwzoLR6BDTeSfyS)
- `AITB_BASE_ID` - AITB base ID (default: appweWEnmxwWfwHDa)

## Output Format

### Human-readable (default):
```
DEAL: Acme Corp - Phase 2

Found 1 result(s):

**Result 1: Brain Bridge Airtable**
- Deal: Acme Corp - Phase 2
- Status: Proposal/Price Quote
- Type: Existing Business
- Organization: Acme Corp
- Contact: Jane Smith
- Amount: $45000
- Link: https://airtable.com/...
```

### JSON (--json flag):
```json
{
  "query": "Acme",
  "total_sources": 1,
  "results": [
    {
      "source": "Brain Bridge Airtable",
      "name": "Acme Corp - Phase 2",
      "status": "Proposal/Price Quote",
      "type": "Existing Business",
      "organization": "Acme Corp",
      "primary_contact": "Jane Smith",
      "amount": 45000,
      "description": "Phase 2 engagement for AI platform",
      "link": "https://airtable.com/..."
    }
  ]
}
```

## Fields Returned

| Field | BB Source | AITB Source |
|-------|----------|------------|
| name | Name | Project Title |
| status | Status | Stage |
| type | Type (New/Existing/Partner) | "Sponsor" (all) |
| organization | Organization (linked) | Organization Name (lookup) |
| primary_contact | Deal Contacts (via junction `tblxdCIQQ7Uu0g1qS`) | Contact Full Name (lookup) |
| amount | Amount | Deal Value |
| description | Description | Description |
| link | Airtable URL | Airtable URL |

## Status Values

### BB Deal Statuses
Contacted, Qualification, Interest Expressed, Empathy Interview, Demo/Inspiration Session, Proposal/Price Quote, Negotiation/Review, Closed Won, Closed Lost, Closed Lost to Competitor

### AITB Sponsor Deal Stages
Backlog, Interest Expressed, Empathy Interview, Scope Identified, Budget Identified, Closed - Won, Closed - Lost

## Flags

| Flag | Description |
|------|-------------|
| `--json`, `-j` | Output in JSON format |
| `--open`, `-o` | Exclude closed deals (Won/Lost) |
| `--base`, `-b` | Filter by base: `bb` or `aitb` |

## Dependencies

- `python3` - Core runtime
- `_shared/_config.py` - Airtable base IDs, table IDs, API helpers

## Notes

- Both bases are searched in parallel for speed
- Results are deduplicated by normalized name within each source
- Fuzzy matching requires a minimum score of 50% to include results
- BB contacts are resolved via the Deal Contacts junction table (`tblxdCIQQ7Uu0g1qS`), not a direct linked field
- The `--open` flag excludes: BB "Closed Won/Lost/Lost to Competitor", AITB "Closed - Won/Lost"
- Tests: `maintaining-relationships/tests/looking-up-deals/test_search_deals.py` (35 tests)

## Related Skills

- [Contact Lookup](looking-up-contacts.md) - Search for individual contacts
- [Organization Lookup](looking-up-organizations.md) - Search for organizations
- [Sales Deal Review](../../managing-finances/references/sales-deal-review.md) - Scheduled deal pipeline report
