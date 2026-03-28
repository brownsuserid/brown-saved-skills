# Updating Contacts

Update fields on an Airtable contact record using PATCH semantics (only specified fields are changed).

## Usage

```bash
python3 update_contact.py --base bb --id recXXX \
    --name "John Smith" \
    --email "john@example.com" \
    --title "VP Engineering"
```

### Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--base` | Yes | Which base: `bb` or `aitb` |
| `--id` | Yes | Airtable record ID (recXXX) |
| `--name` | No | Full name / display name |
| `--first-name` | No | First name (BB only) |
| `--last-name` | No | Last name (BB only) |
| `--email` | No | Email address |
| `--phone` | No | Phone number |
| `--title` | No | Job title |
| `--organization` | No | Organization record ID (recXXX) |
| `--config` | No | Path to YAML config file |

## Output

JSON with record ID, name, organization, base, Airtable URL, and list of updated fields. Warns if the contact has no linked organization.

## Dependencies

- Requires `airtable-config` sibling skill for Airtable API configuration
