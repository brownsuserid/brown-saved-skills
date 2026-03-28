# search-airtable

Generic Airtable search engines for organizations, contacts, and deals.

Config-driven — each library (AITB, BB, Personal) ships its own YAML config
that defines which bases to search and how fields are mapped.

## Usage

```bash
# Search with a specific config
python search_orgs.py "Acme Corp" --config /path/to/config.yaml

# Filter to one base within a multi-base config
python search_orgs.py "Acme Corp" --config /path/to/config.yaml --base aitb

# JSON output
python search_orgs.py "Acme Corp" --config /path/to/config.yaml --json
```

## Config Format

```yaml
bases:
  base_key:
    base_id: appXXXXXXXX
    orgs_table_id: tblXXXXXXXX
    source_label: Human-readable name
    fields:
      name: Name
      industry: Industry
      size: Company Size    # or "Size" — varies per base
      description: Description
      website: Website
      contacts: Contacts
      deals: Deals          # or "Sponsor Deals" — varies per base
```

## Requirements

- `AIRTABLE_TOKEN` environment variable
- `pyyaml` package
