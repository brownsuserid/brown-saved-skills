# Updating Organizations

Update fields on an Airtable organization record using PATCH semantics.

## Usage

```bash
python3 update_org.py --base bb --id recXXX \
    --name "Acme Corp" \
    --industry "Manufacturing" \
    --website "https://acme.com"
```

### Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--base` | Yes | Which base: `bb` or `aitb` |
| `--id` | Yes | Airtable record ID (recXXX) |
| `--name` | No | Organization name |
| `--industry` | No | Industry |
| `--size` | No | Company size |
| `--description` | No | Description |
| `--website` | No | Website URL |
| `--config` | No | Path to YAML config file |

## Output

JSON with record ID, name, base, Airtable URL, and list of updated fields.

## Dependencies

- Requires `airtable-config` sibling skill for Airtable API configuration
