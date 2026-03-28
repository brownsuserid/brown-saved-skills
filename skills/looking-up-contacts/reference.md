# Contact Lookup Skill

Search for contacts across all connected sources with fuzzy matching and deduplication.

## Usage

```bash
# Search for a contact by name
python search_contacts.py "John Smith"

# Search with JSON output (for programmatic use)
python search_contacts.py "John Smith" --json

# Search for an organization
python search_contacts.py "Brain Bridge" --org
```

## Sources Searched (Priority Order)

1. **Brain Bridge Airtable** - Contacts (tbllWxmXIVG5wveiZ) + Organizations
2. **AITB Airtable** - Contacts (tbloW7bNtSGI4E3A7) + Organizations
3. **Obsidian People folder** - `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I)/Extras/People/`
4. **Apple Contacts** - Via AppleScript on macOS
5. **Google Contacts** - Via `gog contacts` CLI (3 accounts)

When `--org` is used, only Airtable organization tables are searched.

## Scripts

- `search_contacts.py` - Single Python module containing all source searches, fuzzy matching, deduplication, and output formatting

Located at:
```
~/.openclaw/skills/maintaining-relationships/scripts/looking-up-contacts/
```

## Configuration

Environment variables:
- `AIRTABLE_TOKEN` - **Required.** API token for Airtable (must be set in environment)
- `OBSIDIAN_VAULT` - Path to Obsidian vault (default: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/2nd Brain (I))

## Output Format

### Human-readable (default):
```
CONTACT: John Smith

Found in 3 source(s):

**Source 1: Brain Bridge Airtable**
- Full Name: John Smith
- Email: john@example.com
- Phone: +1 555-1234
- Title: CEO
- Organization: Acme Corp
- Link: https://airtable.com/...

**Source 2: Obsidian**
- Full Name: John Smith
- Email: john@example.com
- Title: CEO
- Organization: Acme Corp
- Link: /Users/.../John Smith.md
```

### JSON (--json flag):
```json
{
  "query": "John Smith",
  "total_sources": 3,
  "results": [
    {
      "source": "Brain Bridge Airtable",
      "name": "John Smith",
      "email": "john@example.com",
      "phone": "+1 555-1234",
      "title": "CEO",
      "organization": "Acme Corp",
      "link": "https://airtable.com/..."
    }
  ]
}
```

## Dependencies

- `python3` - Core runtime
- `_shared/_config.py` - Airtable base IDs, table IDs, API helpers
- `osascript` - For Apple Contacts search (macOS only, optional)
- `gog` - For Google Contacts search (optional)

## Notes

- Results are deduplicated by normalized name (case-insensitive, special chars removed)
- Fuzzy matching requires a minimum score of 50% to include results
- Apple Contacts search requires macOS and Contacts app permissions
- `--org` flag restricts search to Airtable organization tables only
- Graceful degradation: if any source fails, remaining sources still return results
- Tests: `maintaining-relationships/tests/looking-up-contacts/test_search_contacts.py` (77 tests)

## Related Skills

- [Organization Lookup](looking-up-organizations.md) - Dedicated org search with richer fields (Industry, Size, Deals count)
- [Deal Lookup](looking-up-deals.md) - Search for deals by name or company
- [Searching Local Files](searching-local-files.md) - When a contact isn't found in any source above, search FilingCabinet for old LinkedIn CSVs, Slack mentions, and business documents
