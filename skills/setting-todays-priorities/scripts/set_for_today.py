#!/usr/bin/env python3
"""
Set or unset the "For Today" checkbox on Airtable task records.

Usage:
    python3 set_for_today.py --records '[{"id":"recXXX","base":"personal","value":true}, ...]' [--config path/to/config.yaml]

Output:
    JSON with updated, errors, and summary.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Import shared Airtable config
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_shared"
    ),
)
import airtable_config  # noqa: E402


def validate_record(record: dict, config: dict) -> str | None:
    """Validate a single record dict. Returns error message or None."""
    bases = airtable_config.get_bases(config)
    valid_bases = set(bases.keys())
    if "id" not in record:
        return "Missing 'id' field"
    if not isinstance(record["id"], str) or not record["id"].startswith("rec"):
        return f"Invalid record ID: {record['id']} (must start with 'rec')"
    if "base" not in record:
        return f"Missing 'base' field for {record['id']}"
    if record["base"] not in valid_bases:
        return (
            f"Invalid base '{record['base']}' for {record['id']} "
            f"(must be one of: {', '.join(sorted(valid_bases))})"
        )
    if "value" not in record:
        return f"Missing 'value' field for {record['id']}"
    if not isinstance(record["value"], bool):
        return f"Invalid value for {record['id']}: must be true or false"
    return None


def update_for_today(record_id: str, base_key: str, value: bool, config: dict) -> dict:
    """PATCH a single record's For Today field. Returns the updated record."""
    base_cfg = airtable_config.get_base(config, base_key)
    for_today_field = base_cfg["for_today_field"]

    url = f"https://api.airtable.com/v0/{base_cfg['base_id']}/{base_cfg['tasks_table_id']}/{record_id}"
    payload = json.dumps({"fields": {for_today_field: value}}).encode()

    req = urllib.request.Request(
        url, data=payload, headers=airtable_config.api_headers(), method="PATCH"
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set/unset For Today on Airtable tasks"
    )
    parser.add_argument(
        "--records",
        required=True,
        help="JSON array of {id, base, value} objects",
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config = airtable_config.load_config(args.config)
    bases = airtable_config.get_bases(config)

    try:
        records = json.loads(args.records)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON for --records: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(records, list):
        print("Error: --records must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Validate all records upfront
    for rec in records:
        err = validate_record(rec, config)
        if err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

    updated: list = []
    errors: list = []

    for rec in records:
        record_id = rec["id"]
        base_key = rec["base"]
        value = rec["value"]
        base_cfg = bases[base_key]

        try:
            result = update_for_today(record_id, base_key, value, config)
            fields = result.get("fields", {})
            updated.append(
                {
                    "id": result["id"],
                    "task": fields.get(base_cfg["task_field"], ""),
                    "base": base_key,
                    "for_today": value,
                    "airtable_url": airtable_config.airtable_record_url(
                        base_cfg["base_id"],
                        base_cfg["tasks_table_id"],
                        result["id"],
                    ),
                }
            )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            errors.append(
                {
                    "id": record_id,
                    "base": base_key,
                    "error": f"HTTP {e.code}: {error_body}",
                }
            )
            print(
                f"Warning: Failed to update {record_id} in {base_key}: {error_body}",
                file=sys.stderr,
            )
        except Exception as e:
            errors.append(
                {
                    "id": record_id,
                    "base": base_key,
                    "error": str(e),
                }
            )
            print(
                f"Warning: Failed to update {record_id} in {base_key}: {e}",
                file=sys.stderr,
            )

    output = {
        "updated": updated,
        "errors": errors,
        "summary": {
            "total_requested": len(records),
            "successful": len(updated),
            "failed": len(errors),
        },
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
