#!/usr/bin/env python3
"""
Search for contacts across all connected sources with fuzzy matching and deduplication.

Sources searched (priority order):
1. Brain Bridge Airtable — Contacts + Organizations
2. AITB Airtable — Contacts + Organizations
3. Obsidian People folder
4. Apple Contacts (macOS only, via osascript)
5. Google Contacts (via gog CLI, 3 accounts)

Usage:
    python search_contacts.py "John Smith"
    python search_contacts.py "John Smith" --json
    python search_contacts.py "Brain Bridge" --org
    python search_contacts.py "John Smith" --config /path/to/config.yaml
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "_shared"))

from airtable_config import api_headers, airtable_record_url, load_config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_OBSIDIAN_VAULT = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Mobile Documents",
    "iCloud~md~obsidian",
    "Documents",
    "2nd Brain (I)",
)

GOOGLE_ACCOUNTS = [
    "aaroneden77@gmail.com",
    "aaron@brainbridge.app",
    "aaron@aitrailblazers.org",
]


def _build_airtable_config(config: dict) -> dict:
    """Build AIRTABLE_CONFIG from the loaded YAML config."""
    bases = config["bases"]
    return {
        "bb": {
            "base_id": bases["bb"]["base_id"],
            "contacts_table_id": bases["bb"]["contacts_table_id"],
            "orgs_table_id": bases["bb"]["orgs_table"],
            "source_label": "Brain Bridge Airtable",
        },
        "aitb": {
            "base_id": bases["aitb"]["base_id"],
            "contacts_table_id": bases["aitb"]["contacts_table_id"],
            "orgs_table_id": bases["aitb"]["orgs_table"],
            "source_label": "AITB Airtable",
        },
    }


# Module-level config — loaded lazily or via main()
_config: dict | None = None
AIRTABLE_CONFIG: dict = {}


def _ensure_config(config_path: str | None = None) -> dict:
    """Load config if not already loaded. Returns the full config."""
    global _config, AIRTABLE_CONFIG
    if _config is None:
        _config = load_config(config_path)
        AIRTABLE_CONFIG.update(_build_airtable_config(_config))
    return _config


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, alphanumeric only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fuzzy_score(query: str, target: str) -> int:
    """Calculate a fuzzy match score (0-100) between query and target."""
    norm_query = normalize_name(query)
    norm_target = normalize_name(target)

    if not norm_query or not norm_target:
        return 0

    if norm_query == norm_target:
        return 100

    if norm_query in norm_target:
        return 90

    if norm_target in norm_query:
        return 80

    words = query.split()
    if not words:
        return 0

    match_count = sum(
        1
        for w in words
        if len(normalize_name(w)) >= 3 and normalize_name(w) in norm_target
    )
    return match_count * 70 // len(words)


# ---------------------------------------------------------------------------
# Source: Airtable
# ---------------------------------------------------------------------------


def fetch_airtable_records(
    base_id: str, table_id: str, formula: str, max_records: int = 10
) -> list[dict]:
    """Fetch records from Airtable with a filter formula."""
    import urllib.parse
    import urllib.request

    url = (
        f"https://api.airtable.com/v0/{base_id}/{table_id}"
        f"?filterByFormula={urllib.parse.quote(formula)}&maxRecords={max_records}"
    )
    req = urllib.request.Request(url, headers=api_headers())
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
    return data.get("records", [])


def parse_airtable_contact(record: dict, base_id: str, table_id: str) -> dict[str, Any]:
    """Parse an Airtable contact record into a normalized dict."""
    fields = record.get("fields", {})
    name = fields.get("Name") or fields.get("Full Name") or ""
    if not name:
        first = fields.get("First Name", "")
        last = fields.get("Last Name", "")
        name = f"{first} {last}".strip() or "Unknown"
    return {
        "name": name,
        "email": fields.get("Email", ""),
        "phone": fields.get("Phone", fields.get("Phone Number", "")),
        "title": fields.get("Title", fields.get("Role", "")),
        "organization": fields.get("Organization", fields.get("Company", "")),
        "link": airtable_record_url(base_id, table_id, record["id"]),
    }


def parse_airtable_org(record: dict, base_id: str, table_id: str) -> dict[str, Any]:
    """Parse an Airtable organization record as a contact-like result."""
    fields = record.get("fields", {})
    return {
        "name": fields.get("Name", "Unknown"),
        "email": fields.get("Email", fields.get("Contact Email", "")),
        "phone": fields.get("Phone", ""),
        "title": "Organization",
        "organization": fields.get("Name", ""),
        "link": airtable_record_url(base_id, table_id, record["id"]),
    }


def search_airtable(query: str, base_key: str, org_only: bool = False) -> list[dict]:
    """Search contacts and/or organizations in a single Airtable base."""
    _ensure_config()
    at_config = AIRTABLE_CONFIG[base_key]
    base_config = _config["bases"][base_key]
    base_id = at_config["base_id"]
    norm_query = re.sub(r"[^a-z0-9 ]", "", query.lower())
    results = []

    # Search contacts (unless org-only)
    if not org_only:
        name_field = base_config.get("contacts_name_field", "Name")
        email_field = base_config.get("contacts_email_field", "Email")
        formula = (
            f"OR(FIND('{norm_query}', LOWER({{{name_field}}})) > 0, "
            f"FIND('{norm_query}', LOWER({{{email_field}}})) > 0)"
        )
        try:
            records = fetch_airtable_records(
                base_id, at_config["contacts_table_id"], formula
            )
            for record in records:
                parsed = parse_airtable_contact(
                    record, base_id, at_config["contacts_table_id"]
                )
                parsed["source"] = at_config["source_label"]
                results.append(parsed)
        except Exception as e:
            print(f"[{base_key}] Error searching contacts: {e}", file=sys.stderr)

    # Search organizations (skip if no orgs table configured)
    orgs_table_id = at_config["orgs_table_id"]
    if orgs_table_id:
        orgs_name_field = base_config.get("orgs_name_field", "Name")
        org_formula = f"FIND('{norm_query}', LOWER({{{orgs_name_field}}})) > 0"
        try:
            org_records = fetch_airtable_records(base_id, orgs_table_id, org_formula)
            for record in org_records:
                parsed = parse_airtable_org(record, base_id, orgs_table_id)
                parsed["source"] = at_config["source_label"]
                results.append(parsed)
        except Exception as e:
            print(f"[{base_key}] Error searching orgs: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Source: Obsidian
# ---------------------------------------------------------------------------


def extract_yaml_field(content: str, key: str) -> str:
    """Extract a value from YAML frontmatter."""
    pattern = rf"^{re.escape(key)}:\s*(.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        value = match.group(1).strip().strip("\"'")
        return value
    return ""


def extract_email(content: str) -> str:
    """Extract the first email address from text."""
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
    return match.group(0) if match else ""


def extract_phone(content: str) -> str:
    """Extract the first phone number from text."""
    match = re.search(
        r"(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}", content
    )
    return match.group(0) if match else ""


def parse_obsidian_person(file_path: str, content: str) -> dict[str, Any]:
    """Parse an Obsidian People markdown file into a contact dict."""
    name = Path(file_path).stem
    return {
        "name": name,
        "email": extract_email(content),
        "phone": extract_phone(content),
        "title": (
            extract_yaml_field(content, "title")
            or extract_yaml_field(content, "role")
            or extract_yaml_field(content, "occupation")
        ),
        "organization": (
            extract_yaml_field(content, "company")
            or extract_yaml_field(content, "organization")
            or extract_yaml_field(content, "employer")
        ),
        "link": file_path,
    }


def obsidian_match_score(query: str, name: str, content: str) -> int:
    """Calculate match score for an Obsidian file: filename match, then content fallback."""
    norm_query = normalize_name(query)
    norm_name = normalize_name(name)

    if not norm_query or not norm_name:
        return 0

    if norm_query == norm_name:
        return 100

    if norm_query in norm_name:
        return 90

    # Word matching on filename
    words = query.lower().split()
    match_count = sum(
        1 for w in words if len(w) >= 3 and normalize_name(w) in norm_name
    )
    score = match_count * 80 // len(words) if words else 0

    # Content fallback for low filename scores
    if score < 50:
        lower_content = content.lower()
        for w in words:
            if len(w) >= 3 and w in lower_content:
                score += 10
        score = min(score, 100)

    return score


def search_obsidian(query: str, vault_path: str | None = None) -> list[dict]:
    """Search the Obsidian People folder for matching contacts."""
    vault = vault_path or os.environ.get("OBSIDIAN_VAULT", DEFAULT_OBSIDIAN_VAULT)
    people_dir = os.path.join(vault, "Extras", "People")

    if not os.path.isdir(people_dir):
        return []

    results = []
    pattern = os.path.join(people_dir, "*.md")

    for file_path in glob.glob(pattern):
        name = Path(file_path).stem
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        score = obsidian_match_score(query, name, content)
        if score >= 50:
            parsed = parse_obsidian_person(file_path, content)
            parsed["source"] = "Obsidian"
            results.append(parsed)

    return results


# ---------------------------------------------------------------------------
# Source: Apple Contacts (macOS only)
# ---------------------------------------------------------------------------

APPLE_CONTACTS_SCRIPT = r"""
on run argv
  set searchQuery to item 1 of argv
  set lowerQuery to do shell script "echo " & quoted form of searchQuery & " | tr '[:upper:]' '[:lower:]'"
  set TAB to (ASCII character 9)
  set LF to (ASCII character 10)

  tell application "Contacts"
    set matchingContacts to {}

    try
      set nameMatches to every person whose name contains searchQuery
      set matchingContacts to nameMatches
    end try

    set queryWords to words of searchQuery
    if (count of queryWords) > 1 then
      repeat with aWord in queryWords
        if length of aWord > 2 then
          try
            set wordMatches to every person whose name contains aWord
            repeat with aMatch in wordMatches
              if aMatch is not in matchingContacts then
                set end of matchingContacts to aMatch
              end if
            end repeat
          end try
        end if
      end repeat
    end if

    set jsonList to {}

    repeat with aContact in matchingContacts
      try
        set contactName to name of aContact
        set lowerName to do shell script "echo " & quoted form of contactName & " | tr '[:upper:]' '[:lower:]'"
        if lowerName contains lowerQuery then
          set contactEmails to {}
          set contactPhones to {}

          try
            repeat with anEmail in emails of aContact
              set end of contactEmails to value of anEmail as string
            end repeat
          end try

          try
            repeat with aPhone in phones of aContact
              set end of contactPhones to value of aPhone as string
            end repeat
          end try

          try
            set jobTitle to job title of aContact
          on error
            set jobTitle to ""
          end try

          try
            set org to organization of aContact
          on error
            set org to ""
          end try

          set bdStr to ""
          try
            set bd to birth date of aContact
            set bdMonth to (month of bd as integer) as string
            set bdDay to (day of bd) as string
            set bdYear to (year of bd) as string
            if bdYear is "1604" then
              set bdStr to bdMonth & "/" & bdDay
            else
              set bdStr to bdMonth & "/" & bdDay & "/" & bdYear
            end if
          on error
            set bdStr to ""
          end try

          set emailStr to ""
          repeat with e in contactEmails
            if emailStr is not "" then set emailStr to emailStr & ","
            set emailStr to emailStr & e
          end repeat

          set phoneStr to ""
          repeat with p in contactPhones
            if phoneStr is not "" then set phoneStr to phoneStr & ","
            set phoneStr to phoneStr & p
          end repeat

          set outputLine to contactName & TAB & emailStr & TAB & phoneStr & TAB & jobTitle & TAB & org & TAB & bdStr
          set end of jsonList to outputLine
        end if
      on error
        -- Skip contacts that cannot be read
      end try
    end repeat

    set output to ""
    repeat with lineItem in jsonList
      set output to output & lineItem & LF
    end repeat
    return output
  end tell
end run
"""


def parse_apple_contact_line(line: str) -> dict[str, Any] | None:
    """Parse a tab-delimited AppleScript output line into a contact dict."""
    parts = line.split("\t")
    if len(parts) < 1 or not parts[0].strip():
        return None

    name = parts[0].strip()
    emails = parts[1].strip() if len(parts) > 1 else ""
    phones = parts[2].strip() if len(parts) > 2 else ""
    title = parts[3].strip() if len(parts) > 3 else ""
    org = parts[4].strip() if len(parts) > 4 else ""
    birthday_raw = parts[5].strip() if len(parts) > 5 else ""

    # Clean up "missing value" from AppleScript
    title = "" if "missing value" in title else title
    org = "" if "missing value" in org else org
    birthday_raw = "" if "missing value" in birthday_raw else birthday_raw

    # Parse birthday into structured data
    birthday = None
    if birthday_raw:
        bd_parts = birthday_raw.split("/")
        if len(bd_parts) >= 2:
            birthday = {
                "month": int(bd_parts[0]),
                "day": int(bd_parts[1]),
                "year": int(bd_parts[2]) if len(bd_parts) > 2 else None,
            }

    return {
        "name": name,
        "email": emails.split(",")[0] if emails else "",
        "phone": phones.split(",")[0] if phones else "",
        "title": title,
        "organization": org,
        "birthday": birthday,
        "link": "contacts://",
    }


def run_apple_contacts_search(query: str) -> str:
    """Execute the AppleScript to search Apple Contacts. Returns raw output."""
    result = subprocess.run(
        ["osascript", "-e", APPLE_CONTACTS_SCRIPT, query],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def search_apple_contacts(query: str) -> list[dict]:
    """Search macOS Apple Contacts via AppleScript."""
    import platform

    if platform.system() != "Darwin":
        return []

    try:
        output = run_apple_contacts_search(query)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    if not output:
        return []

    results = []
    for line in output.split("\n"):
        parsed = parse_apple_contact_line(line)
        if parsed:
            parsed["source"] = "Apple Contacts"
            results.append(parsed)

    return results


# ---------------------------------------------------------------------------
# Birthday filtering (Apple Contacts bulk query via JXA)
# ---------------------------------------------------------------------------

BIRTHDAY_JXA_SCRIPT = """
(() => {
    const app = Application('Contacts');
    const people = app.people;
    const names = people.name();
    const birthDates = people.birthDate();
    const emails = people.emails.value();
    const phones = people.phones.value();
    const titles = people.jobTitle();
    const orgs = people.organization();

    const results = [];
    for (let i = 0; i < names.length; i++) {
        const bd = birthDates[i];
        if (!bd) continue;

        const month = bd.getMonth() + 1;
        const day = bd.getDate();
        const year = bd.getFullYear();
        const hasYear = year !== 1604;

        const email = (emails[i] && emails[i].length > 0) ? emails[i][0] : null;
        const phone = (phones[i] && phones[i].length > 0) ? phones[i][0] : null;
        const title = titles[i] || null;
        const org = orgs[i] || null;

        results.push({
            name: names[i],
            month: month,
            day: day,
            birth_year: hasYear ? year : null,
            email: email,
            phone: phone,
            title: title,
            organization: org
        });
    }
    return JSON.stringify(results);
})()
"""


def search_upcoming_birthdays(days: int) -> list[dict]:
    """Find contacts with birthdays in the next N days from Apple Contacts."""
    from datetime import datetime

    import platform

    if platform.system() != "Darwin":
        return []

    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", BIRTHDAY_JXA_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"Error querying birthdays: {result.stderr}", file=sys.stderr)
            return []
        contacts = json.loads(result.stdout.strip())
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ) as e:
        print(f"Error querying birthdays: {e}", file=sys.stderr)
        return []

    today = datetime.now().date()
    upcoming = []

    for c in contacts:
        for year_offset in [0, 1]:
            try:
                birthday_this_year = datetime(
                    today.year + year_offset, c["month"], c["day"]
                ).date()
            except ValueError:
                continue

            delta = (birthday_this_year - today).days
            if 0 <= delta <= days:
                age = None
                if c["birth_year"]:
                    age = today.year + year_offset - c["birth_year"]

                upcoming.append(
                    {
                        "name": c["name"],
                        "email": c.get("email", ""),
                        "phone": c.get("phone", ""),
                        "title": c.get("title", ""),
                        "organization": c.get("organization", ""),
                        "birthday": {
                            "month": c["month"],
                            "day": c["day"],
                            "year": c["birth_year"],
                        },
                        "birthday_date": birthday_this_year.isoformat(),
                        "days_away": delta,
                        "turning_age": age,
                        "source": "Apple Contacts",
                        "link": "contacts://",
                    }
                )
                break

    upcoming.sort(key=lambda x: x["days_away"])
    return upcoming


# ---------------------------------------------------------------------------
# Source: Google Contacts (via gog CLI)
# ---------------------------------------------------------------------------


def run_gog_contacts_search(query: str, account: str) -> list[dict]:
    """Run gog contacts search for a single account. Returns parsed contacts."""
    try:
        result = subprocess.run(
            ["gog", "contacts", "search", query, "--account", account, "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        return data.get("contacts", [])
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ):
        return []


def parse_google_contact(contact: dict) -> dict[str, Any]:
    """Parse a gog contacts search result into a normalized dict."""
    emails = contact.get("emails", [])
    phones = contact.get("phones", [])
    return {
        "name": contact.get("name", ""),
        "email": contact.get("email", emails[0] if emails else ""),
        "phone": contact.get("phone", phones[0] if phones else ""),
        "title": contact.get("title", contact.get("jobTitle", "")),
        "organization": contact.get("organization", contact.get("company", "")),
        "link": "https://contacts.google.com",
    }


def search_google_contacts(query: str, accounts: list[str] | None = None) -> list[dict]:
    """Search Google Contacts across all configured accounts."""
    accounts = accounts or GOOGLE_ACCOUNTS

    if not _command_exists("gog"):
        return []

    results = []
    for account in accounts:
        contacts = run_gog_contacts_search(query, account)
        for contact in contacts:
            name = contact.get("name", "")
            if not name:
                continue
            score = fuzzy_score(query, name)
            if score >= 50:
                parsed = parse_google_contact(contact)
                parsed["source"] = "Google Contacts"
                results.append(parsed)

    return results


def _command_exists(cmd: str) -> bool:
    """Check if a command is available on PATH."""
    import shutil

    return shutil.which(cmd) is not None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def search_all_sources(query: str, org_only: bool = False) -> list[dict]:
    """Search all contact sources and collect results."""
    _ensure_config()
    results = []

    # Airtable (BB + AITB)
    for base_key in AIRTABLE_CONFIG:
        try:
            results.extend(search_airtable(query, base_key, org_only=org_only))
        except Exception as e:
            print(f"[{base_key}] Error: {e}", file=sys.stderr)

    # Non-Airtable sources (skip if org-only)
    if not org_only:
        try:
            results.extend(search_obsidian(query))
        except Exception as e:
            print(f"[obsidian] Error: {e}", file=sys.stderr)

        try:
            results.extend(search_apple_contacts(query))
        except Exception as e:
            print(f"[apple] Error: {e}", file=sys.stderr)

        try:
            results.extend(search_google_contacts(query))
        except Exception as e:
            print(f"[google] Error: {e}", file=sys.stderr)

    return results


def filter_and_dedup(
    results: list[dict], query: str, min_score: int = 50
) -> list[dict]:
    """Filter results by fuzzy match score and deduplicate within same source."""
    seen: set[str] = set()
    filtered = []

    for result in results:
        name = result.get("name", "")
        source = result.get("source", "")
        if not name:
            continue

        score = fuzzy_score(query, name)
        if score < min_score:
            continue

        unique_key = f"{source}:{normalize_name(name)}"
        if unique_key in seen:
            continue

        seen.add(unique_key)
        filtered.append(result)

    return filtered


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

ALL_SOURCES = [
    "Brain Bridge Airtable",
    "AITB Airtable",
    "Obsidian",
    "Apple Contacts",
    "Google Contacts",
]
ORG_SOURCES = ["Brain Bridge Airtable", "AITB Airtable"]


def format_json(query: str, results: list[dict]) -> str:
    """Format results as JSON."""
    sources = {r["source"] for r in results}
    return json.dumps(
        {
            "query": query,
            "total_sources": len(sources),
            "results": results,
        },
        indent=2,
    )


def format_human(query: str, results: list[dict], org_only: bool = False) -> str:
    """Format results as human-readable text."""
    expected_sources = ORG_SOURCES if org_only else ALL_SOURCES

    if not results:
        lines = [f"No contacts found for: {query}", ""]
        lines.append("Sources searched:")
        for src in expected_sources:
            lines.append(f"  - {src}")
        return "\n".join(lines)

    best_name = results[0]["name"]
    lines = [
        f"CONTACT: {best_name}",
        "",
        f"Found in {len(results)} source(s):",
        "",
    ]

    for i, result in enumerate(results, 1):
        lines.append(f"**Source {i}: {result['source']}**")
        if result.get("name"):
            lines.append(f"- Full Name: {result['name']}")
        if result.get("email"):
            lines.append(f"- Email: {result['email']}")
        if result.get("phone"):
            lines.append(f"- Phone: {result['phone']}")
        if result.get("title"):
            lines.append(f"- Title: {result['title']}")
        if result.get("organization"):
            lines.append(f"- Organization: {result['organization']}")
        if result.get("link"):
            lines.append(f"- Link: {result['link']}")
        lines.append("")

    # Show missing sources
    found_sources = {r["source"] for r in results}
    missing = [s for s in expected_sources if s not in found_sources]

    lines.append("---")
    lines.append("")
    if missing:
        lines.append("Not found in:")
        for m in missing:
            lines.append(f"  - {m}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def format_birthday_json(results: list[dict]) -> str:
    """Format upcoming birthday results as JSON."""
    return json.dumps(
        {
            "upcoming_birthdays": results,
            "count": len(results),
        },
        indent=2,
    )


def format_birthday_human(results: list[dict]) -> str:
    """Format upcoming birthday results as human-readable text."""
    if not results:
        return "No upcoming birthdays."

    lines = ["UPCOMING BIRTHDAYS", ""]
    for b in results:
        label = "TODAY" if b["days_away"] == 0 else f"in {b['days_away']}d"
        age_str = f" (turning {b['turning_age']})" if b.get("turning_age") else ""
        lines.append(f"  {b['birthday_date']} ({label}) - {b['name']}{age_str}")
        if b.get("email"):
            lines.append(f"    Email: {b['email']}")
        if b.get("phone"):
            lines.append(f"    Phone: {b['phone']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search for contacts across all connected sources."
    )
    parser.add_argument("query", nargs="?", default=None, help="Name to search for")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON format")
    parser.add_argument(
        "--org", "-o", action="store_true", help="Search organizations only"
    )
    parser.add_argument(
        "--birthday-upcoming",
        type=int,
        metavar="DAYS",
        help="Find contacts with birthdays in the next N days",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file (default: _shared/configs/all.yaml)",
    )
    args = parser.parse_args()

    # Load config
    _ensure_config(args.config)

    # Birthday mode: no query needed, searches Apple Contacts for upcoming birthdays
    if args.birthday_upcoming is not None:
        results = search_upcoming_birthdays(args.birthday_upcoming)
        if args.json:
            print(format_birthday_json(results))
        else:
            print(format_birthday_human(results))
        return

    if not args.query:
        parser.error("query is required (or use --birthday-upcoming N)")

    print("Searching all sources...", file=sys.stderr)
    raw_results = search_all_sources(args.query, org_only=args.org)
    results = filter_and_dedup(raw_results, args.query)

    if args.json:
        print(format_json(args.query, results))
    else:
        print(format_human(args.query, results, org_only=args.org))


if __name__ == "__main__":
    main()
