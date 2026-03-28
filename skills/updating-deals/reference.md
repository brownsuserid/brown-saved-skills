# Updating Deals

Update fields on an Airtable deal record using PATCH semantics. Handles BB junction tables for contact linking automatically.

## Usage

```bash
python3 update_deal.py --base bb --id recXXX \
    --status "Negotiation" \
    --amount 50000 \
    --contact recContactXXX
```

### Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--base` | Yes | Which base: `bb` or `aitb` |
| `--id` | Yes | Airtable record ID (recXXX) |
| `--name` | No | Deal name |
| `--status` | No | Deal status (literal value) |
| `--type` | No | Deal type (BB only) |
| `--organization` | No | Organization record ID (recXXX) |
| `--contact` | No | Contact record ID (recXXX) |
| `--amount` | No | Deal amount (float) |
| `--description` | No | Deal description |
| `--assignee` | No | Assignee: `pablo`, `aaron`, or record ID |
| `--campaign` | No | Campaign record ID (BB only) |
| `--config` | No | Path to YAML config file |

## Output

JSON with record ID, name, status, base, Airtable URL, and list of updated fields. Warns about missing organization, contact, or campaign links.

## Dependencies

- Requires `airtable-config` sibling skill for Airtable API configuration
