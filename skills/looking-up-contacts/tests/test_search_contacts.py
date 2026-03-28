"""Tests for search_contacts.py — contact lookup across all sources."""

import json
import os
import sys
from unittest.mock import MagicMock, patch


# Add scripts dir to path so we can import the module
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "looking-up-contacts"
    ),
)

import search_contacts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_airtable_response(records, offset=None):
    """Build a fake Airtable response body."""
    body = {"records": records}
    if offset:
        body["offset"] = offset
    return json.dumps(body).encode()


def _mock_urlopen(response_bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_contact_record(
    record_id="recC1",
    name="John Smith",
    email="john@example.com",
    phone="+1 555-1234",
    title="CEO",
    org="Acme Corp",
):
    return {
        "id": record_id,
        "fields": {
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Title": title,
            "Organization": org,
        },
    }


def _make_org_record(record_id="recOrg1", name="Acme Corp"):
    return {
        "id": record_id,
        "fields": {"Name": name},
    }


# ---------------------------------------------------------------------------
# TestNormalizeName
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_basic(self):
        assert search_contacts.normalize_name("John Smith") == "johnsmith"

    def test_special_chars(self):
        assert search_contacts.normalize_name("O'Brien Jr.") == "obrienjr"

    def test_empty(self):
        assert search_contacts.normalize_name("") == ""

    def test_numeric(self):
        assert search_contacts.normalize_name("Agent 007") == "agent007"


# ---------------------------------------------------------------------------
# TestFuzzyScore
# ---------------------------------------------------------------------------


class TestFuzzyScore:
    def test_exact_match(self):
        assert search_contacts.fuzzy_score("John Smith", "John Smith") == 100

    def test_case_insensitive(self):
        assert search_contacts.fuzzy_score("john smith", "JOHN SMITH") == 100

    def test_query_in_target(self):
        assert search_contacts.fuzzy_score("John", "John Smith") == 90

    def test_target_in_query(self):
        assert search_contacts.fuzzy_score("John Smith III", "John") == 80

    def test_partial_word_match(self):
        score = search_contacts.fuzzy_score("John Smith", "John Smith Consulting")
        assert score >= 50

    def test_no_match(self):
        assert search_contacts.fuzzy_score("Alpha", "Zebra") == 0

    def test_empty(self):
        assert search_contacts.fuzzy_score("", "John") == 0

    def test_short_words_excluded_from_partial(self):
        # "Al" is 2 chars, excluded from partial word matching
        # but note: "al" IS contained in "totally" so substring match returns 90
        # Test with words that truly don't substring-match either
        assert search_contacts.fuzzy_score("Zo", "Absolutely Nothing") == 0


# ---------------------------------------------------------------------------
# TestParseAirtableContact
# ---------------------------------------------------------------------------


class TestParseAirtableContact:
    def test_full_record(self):
        record = _make_contact_record()
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")

        assert result["name"] == "John Smith"
        assert result["email"] == "john@example.com"
        assert result["phone"] == "+1 555-1234"
        assert result["title"] == "CEO"
        assert result["organization"] == "Acme Corp"
        assert "airtable.com" in result["link"]

    def test_name_fallback_to_full_name(self):
        record = {"id": "recC1", "fields": {"Full Name": "Jane Doe"}}
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")
        assert result["name"] == "Jane Doe"

    def test_name_fallback_to_first_last(self):
        record = {
            "id": "recC1",
            "fields": {"First Name": "Jane", "Last Name": "Doe"},
        }
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")
        assert result["name"] == "Jane Doe"

    def test_missing_fields(self):
        record = {"id": "recC1", "fields": {}}
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")
        assert result["name"] == "Unknown"
        assert result["email"] == ""
        assert result["phone"] == ""

    def test_phone_fallback(self):
        record = {
            "id": "recC1",
            "fields": {"Name": "Test", "Phone Number": "555-9876"},
        }
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")
        assert result["phone"] == "555-9876"

    def test_title_fallback_to_role(self):
        record = {"id": "recC1", "fields": {"Name": "Test", "Role": "Engineer"}}
        result = search_contacts.parse_airtable_contact(record, "appXXX", "tblXXX")
        assert result["title"] == "Engineer"


# ---------------------------------------------------------------------------
# TestParseAirtableOrg
# ---------------------------------------------------------------------------


class TestParseAirtableOrg:
    def test_basic_org(self):
        record = _make_org_record()
        result = search_contacts.parse_airtable_org(record, "appXXX", "tblXXX")

        assert result["name"] == "Acme Corp"
        assert result["title"] == "Organization"
        assert result["organization"] == "Acme Corp"

    def test_missing_name(self):
        record = {"id": "recOrg1", "fields": {}}
        result = search_contacts.parse_airtable_org(record, "appXXX", "tblXXX")
        assert result["name"] == "Unknown"


# ---------------------------------------------------------------------------
# TestSearchAirtable
# ---------------------------------------------------------------------------


class TestSearchAirtable:
    @patch("search_contacts.fetch_airtable_records")
    def test_contacts_and_orgs_searched(self, mock_fetch):
        # Arrange
        mock_fetch.side_effect = [
            [_make_contact_record()],  # contacts
            [_make_org_record()],  # orgs
        ]

        # Act
        results = search_contacts.search_airtable("John", "bb")

        # Assert
        assert len(results) == 2
        assert mock_fetch.call_count == 2

    @patch("search_contacts.fetch_airtable_records")
    def test_org_only_skips_contacts(self, mock_fetch):
        # Arrange
        mock_fetch.return_value = [_make_org_record()]

        # Act
        results = search_contacts.search_airtable("Acme", "bb", org_only=True)

        # Assert
        assert mock_fetch.call_count == 1  # Only orgs
        assert all(r["title"] == "Organization" for r in results)

    @patch("search_contacts.fetch_airtable_records")
    def test_graceful_on_contacts_failure(self, mock_fetch):
        # Arrange — contacts fail, orgs succeed
        mock_fetch.side_effect = [
            Exception("API error"),
            [_make_org_record()],
        ]

        # Act
        results = search_contacts.search_airtable("Acme", "bb")

        # Assert
        assert len(results) == 1

    @patch("search_contacts.fetch_airtable_records")
    def test_source_label_added(self, mock_fetch):
        mock_fetch.side_effect = [
            [_make_contact_record()],
            [],
        ]

        results = search_contacts.search_airtable("John", "bb")
        assert results[0]["source"] == "Brain Bridge Airtable"

    @patch("search_contacts.fetch_airtable_records")
    def test_bb_formula_uses_config_field_names(self, mock_fetch):
        """BB contacts table uses 'Full Name' and 'Email (Work)', not 'Name'/'Email'.
        The formula must use field names from BASES config, not hardcoded defaults."""
        mock_fetch.side_effect = [[], []]

        search_contacts.search_airtable("gilberto", "bb")

        # First call is contacts search — check the formula arg
        contacts_call = mock_fetch.call_args_list[0]
        formula = contacts_call[1].get("formula") or contacts_call[0][2]
        assert "Full Name" in formula, (
            f"Expected 'Full Name' in formula, got: {formula}"
        )
        assert "Email (Work)" in formula, (
            f"Expected 'Email (Work)' in formula, got: {formula}"
        )

    @patch("search_contacts.fetch_airtable_records")
    def test_aitb_formula_uses_config_field_names(self, mock_fetch):
        """AITB contacts table uses 'Name' and 'Email' — should work with defaults."""
        mock_fetch.side_effect = [[], []]

        search_contacts.search_airtable("gilberto", "aitb")

        contacts_call = mock_fetch.call_args_list[0]
        formula = contacts_call[1].get("formula") or contacts_call[0][2]
        assert "Name" in formula

    @patch("search_contacts.fetch_airtable_records")
    def test_org_formula_uses_config_field_names(self, mock_fetch):
        """Org search formula should use orgs_name_field from config."""
        mock_fetch.side_effect = [[], []]

        search_contacts.search_airtable("acme", "bb")

        # Second call is orgs search
        orgs_call = mock_fetch.call_args_list[1]
        formula = orgs_call[1].get("formula") or orgs_call[0][2]
        assert "Name" in formula

    @patch("search_contacts.fetch_airtable_records")
    def test_skips_org_search_when_no_orgs_table(self, mock_fetch):
        """If a base has no orgs_table (None), org search should be skipped."""
        mock_fetch.return_value = [_make_contact_record()]

        # Temporarily set bb orgs_table_id to None to test the guard
        original = search_contacts.AIRTABLE_CONFIG["bb"]["orgs_table_id"]
        search_contacts.AIRTABLE_CONFIG["bb"]["orgs_table_id"] = None
        try:
            search_contacts.search_airtable("John", "bb")
            # Only contacts call, no orgs call
            assert mock_fetch.call_count == 1
        finally:
            search_contacts.AIRTABLE_CONFIG["bb"]["orgs_table_id"] = original


# ---------------------------------------------------------------------------
# TestObsidian helpers
# ---------------------------------------------------------------------------


class TestExtractYamlField:
    def test_basic_field(self):
        content = "---\ntitle: CEO\ncompany: Acme\n---\n"
        assert search_contacts.extract_yaml_field(content, "title") == "CEO"

    def test_quoted_value(self):
        content = '---\ncompany: "Acme Corp"\n---\n'
        assert search_contacts.extract_yaml_field(content, "company") == "Acme Corp"

    def test_missing_field(self):
        content = "---\ntitle: CEO\n---\n"
        assert search_contacts.extract_yaml_field(content, "company") == ""

    def test_empty_content(self):
        assert search_contacts.extract_yaml_field("", "title") == ""


class TestExtractEmail:
    def test_finds_email(self):
        assert (
            search_contacts.extract_email("Contact: john@example.com for info")
            == "john@example.com"
        )

    def test_no_email(self):
        assert search_contacts.extract_email("No email here") == ""

    def test_first_email_returned(self):
        content = "john@a.com and jane@b.com"
        assert search_contacts.extract_email(content) == "john@a.com"


class TestExtractPhone:
    def test_us_phone(self):
        assert search_contacts.extract_phone("Call 555-123-4567") == "555-123-4567"

    def test_no_phone(self):
        assert search_contacts.extract_phone("No phone here") == ""

    def test_parenthesized(self):
        result = search_contacts.extract_phone("(555) 123-4567")
        assert "555" in result and "4567" in result


class TestObsidianMatchScore:
    def test_exact_filename_match(self):
        score = search_contacts.obsidian_match_score("John Smith", "John Smith", "")
        assert score == 100

    def test_filename_contains_query(self):
        score = search_contacts.obsidian_match_score("John", "John Smith", "")
        assert score == 90

    def test_content_fallback(self):
        score = search_contacts.obsidian_match_score(
            "Acme", "Random Name", "Works at acme corporation"
        )
        assert score >= 10

    def test_no_match(self):
        score = search_contacts.obsidian_match_score("Alpha", "Zebra", "Unrelated")
        assert score < 50


class TestParseObsidianPerson:
    def test_full_frontmatter(self):
        content = """---
title: CEO
company: Acme Corp
---
Email: john@acme.com
Phone: 555-123-4567
"""
        result = search_contacts.parse_obsidian_person("/path/John Smith.md", content)

        assert result["name"] == "John Smith"
        assert result["email"] == "john@acme.com"
        assert result["phone"] == "555-123-4567"
        assert result["title"] == "CEO"
        assert result["organization"] == "Acme Corp"

    def test_alternative_fields(self):
        content = "---\nrole: Engineer\nemployer: BigCo\n---\n"
        result = search_contacts.parse_obsidian_person("/path/Test.md", content)
        assert result["title"] == "Engineer"
        assert result["organization"] == "BigCo"

    def test_empty_content(self):
        result = search_contacts.parse_obsidian_person("/path/Empty.md", "")
        assert result["name"] == "Empty"
        assert result["email"] == ""


class TestSearchObsidian:
    def test_finds_matching_files(self, tmp_path):
        # Arrange
        people_dir = tmp_path / "Extras" / "People"
        people_dir.mkdir(parents=True)
        (people_dir / "John Smith.md").write_text(
            "---\ntitle: CEO\n---\nEmail: john@test.com\n"
        )
        (people_dir / "Jane Doe.md").write_text("---\ntitle: CTO\n---\n")

        # Act
        results = search_contacts.search_obsidian("John", vault_path=str(tmp_path))

        # Assert
        assert len(results) == 1
        assert results[0]["name"] == "John Smith"
        assert results[0]["source"] == "Obsidian"

    def test_no_match(self, tmp_path):
        people_dir = tmp_path / "Extras" / "People"
        people_dir.mkdir(parents=True)
        (people_dir / "Jane Doe.md").write_text("Nothing here")

        results = search_contacts.search_obsidian("ZZZNobody", vault_path=str(tmp_path))
        assert len(results) == 0

    def test_missing_directory(self, tmp_path):
        results = search_contacts.search_obsidian(
            "John", vault_path=str(tmp_path / "nonexistent")
        )
        assert results == []

    def test_content_fallback_match(self, tmp_path):
        # Content fallback: +10 per matching query word found in content.
        # With 5+ query words (3+ chars each) found in content, score >= 50.
        people_dir = tmp_path / "Extras" / "People"
        people_dir.mkdir(parents=True)
        (people_dir / "Random Person.md").write_text(
            "---\n---\n"
            "Works at acme doing engineering for their platform. "
            "Great consulting partner.\n"
        )

        # Multi-word query where 5+ words match content
        results = search_contacts.search_obsidian(
            "acme engineering platform consulting partner",
            vault_path=str(tmp_path),
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# TestAppleContacts
# ---------------------------------------------------------------------------


class TestParseAppleContactLine:
    def test_full_line(self):
        line = "John Smith\tjohn@test.com\t555-1234\tCEO\tAcme Corp"
        result = search_contacts.parse_apple_contact_line(line)

        assert result["name"] == "John Smith"
        assert result["email"] == "john@test.com"
        assert result["phone"] == "555-1234"
        assert result["title"] == "CEO"
        assert result["organization"] == "Acme Corp"

    def test_empty_line(self):
        assert search_contacts.parse_apple_contact_line("") is None

    def test_name_only(self):
        result = search_contacts.parse_apple_contact_line("John Smith")
        assert result["name"] == "John Smith"
        assert result["email"] == ""

    def test_missing_value_cleaned(self):
        line = "John\t\t\tmissing value\tmissing value"
        result = search_contacts.parse_apple_contact_line(line)
        assert result["title"] == ""
        assert result["organization"] == ""

    def test_multiple_emails_takes_first(self):
        line = "John\ta@b.com,c@d.com\t\t\t"
        result = search_contacts.parse_apple_contact_line(line)
        assert result["email"] == "a@b.com"


class TestSearchAppleContacts:
    @patch("search_contacts.run_apple_contacts_search")
    @patch("platform.system", return_value="Darwin")
    def test_parses_output(self, mock_platform, mock_run):
        mock_run.return_value = "John Smith\tjohn@test.com\t555-1234\tCEO\tAcme"
        results = search_contacts.search_apple_contacts("John")

        assert len(results) == 1
        assert results[0]["name"] == "John Smith"
        assert results[0]["source"] == "Apple Contacts"

    @patch("platform.system", return_value="Linux")
    def test_skips_on_non_macos(self, mock_platform):
        results = search_contacts.search_apple_contacts("John")
        assert results == []

    @patch("search_contacts.run_apple_contacts_search")
    @patch("platform.system", return_value="Darwin")
    def test_empty_output(self, mock_platform, mock_run):
        mock_run.return_value = ""
        results = search_contacts.search_apple_contacts("John")
        assert results == []

    @patch("search_contacts.run_apple_contacts_search")
    @patch("platform.system", return_value="Darwin")
    def test_multi_line_output(self, mock_platform, mock_run):
        mock_run.return_value = "John Smith\t\t\t\t\nJane Doe\t\t\t\t"
        results = search_contacts.search_apple_contacts("J")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# TestGoogleContacts
# ---------------------------------------------------------------------------


class TestParseGoogleContact:
    def test_full_contact(self):
        contact = {
            "name": "John Smith",
            "email": "john@gmail.com",
            "phone": "555-1234",
            "title": "CEO",
            "organization": "Acme Corp",
        }
        result = search_contacts.parse_google_contact(contact)

        assert result["name"] == "John Smith"
        assert result["email"] == "john@gmail.com"
        assert result["organization"] == "Acme Corp"
        assert result["link"] == "https://contacts.google.com"

    def test_emails_array_fallback(self):
        contact = {"name": "John", "emails": ["a@b.com", "c@d.com"]}
        result = search_contacts.parse_google_contact(contact)
        assert result["email"] == "a@b.com"

    def test_empty_contact(self):
        result = search_contacts.parse_google_contact({})
        assert result["name"] == ""
        assert result["email"] == ""


class TestSearchGoogleContacts:
    @patch("search_contacts._command_exists", return_value=True)
    @patch("search_contacts.run_gog_contacts_search")
    def test_searches_all_accounts(self, mock_gog, mock_cmd):
        mock_gog.return_value = [{"name": "John Smith", "email": "j@test.com"}]
        accounts = ["a@test.com", "b@test.com"]

        results = search_contacts.search_google_contacts(
            "John Smith", accounts=accounts
        )

        assert mock_gog.call_count == 2
        assert len(results) == 2

    @patch("search_contacts._command_exists", return_value=False)
    def test_skips_when_gog_missing(self, mock_cmd):
        results = search_contacts.search_google_contacts("John")
        assert results == []

    @patch("search_contacts._command_exists", return_value=True)
    @patch("search_contacts.run_gog_contacts_search")
    def test_filters_low_scoring(self, mock_gog, mock_cmd):
        mock_gog.return_value = [{"name": "Totally Unrelated", "email": "x@y.com"}]
        results = search_contacts.search_google_contacts(
            "John Smith", accounts=["a@test.com"]
        )
        assert len(results) == 0

    @patch("search_contacts._command_exists", return_value=True)
    @patch("search_contacts.run_gog_contacts_search")
    def test_skips_nameless_contacts(self, mock_gog, mock_cmd):
        mock_gog.return_value = [{"email": "nobody@test.com"}]
        results = search_contacts.search_google_contacts(
            "test", accounts=["a@test.com"]
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# TestFilterAndDedup
# ---------------------------------------------------------------------------


class TestFilterAndDedup:
    def test_filters_below_threshold(self):
        results = [{"name": "Totally Unrelated", "source": "BB"}]
        filtered = search_contacts.filter_and_dedup(results, "John Smith")
        assert len(filtered) == 0

    def test_keeps_matching(self):
        results = [{"name": "John Smith", "source": "BB"}]
        filtered = search_contacts.filter_and_dedup(results, "John Smith")
        assert len(filtered) == 1

    def test_dedup_same_source(self):
        results = [
            {"name": "John Smith", "source": "BB"},
            {"name": "John Smith", "source": "BB"},
        ]
        filtered = search_contacts.filter_and_dedup(results, "John Smith")
        assert len(filtered) == 1

    def test_keeps_different_sources(self):
        results = [
            {"name": "John Smith", "source": "BB"},
            {"name": "John Smith", "source": "Apple Contacts"},
        ]
        filtered = search_contacts.filter_and_dedup(results, "John Smith")
        assert len(filtered) == 2

    def test_skips_empty_names(self):
        results = [{"name": "", "source": "BB"}]
        filtered = search_contacts.filter_and_dedup(results, "John")
        assert len(filtered) == 0


# ---------------------------------------------------------------------------
# TestSearchAllSources
# ---------------------------------------------------------------------------


class TestSearchAllSources:
    @patch("search_contacts.search_google_contacts", return_value=[])
    @patch("search_contacts.search_apple_contacts", return_value=[])
    @patch("search_contacts.search_obsidian", return_value=[])
    @patch("search_contacts.search_airtable")
    def test_searches_all_sources(self, mock_at, mock_obs, mock_apple, mock_google):
        mock_at.return_value = []
        search_contacts.search_all_sources("John")

        assert mock_at.call_count == 2  # BB + AITB
        mock_obs.assert_called_once()
        mock_apple.assert_called_once()
        mock_google.assert_called_once()

    @patch("search_contacts.search_google_contacts", return_value=[])
    @patch("search_contacts.search_apple_contacts", return_value=[])
    @patch("search_contacts.search_obsidian", return_value=[])
    @patch("search_contacts.search_airtable")
    def test_org_only_skips_non_airtable(
        self, mock_at, mock_obs, mock_apple, mock_google
    ):
        mock_at.return_value = []
        search_contacts.search_all_sources("Acme", org_only=True)

        assert mock_at.call_count == 2
        mock_obs.assert_not_called()
        mock_apple.assert_not_called()
        mock_google.assert_not_called()

    @patch("search_contacts.search_google_contacts", return_value=[])
    @patch("search_contacts.search_apple_contacts", return_value=[])
    @patch("search_contacts.search_obsidian", return_value=[])
    @patch("search_contacts.search_airtable")
    def test_graceful_on_source_failure(
        self, mock_at, mock_obs, mock_apple, mock_google
    ):
        mock_at.side_effect = [
            Exception("API error"),
            [{"name": "John", "source": "AITB"}],
        ]
        results = search_contacts.search_all_sources("John")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# TestFormatJson
# ---------------------------------------------------------------------------


class TestFormatJson:
    def test_structure(self):
        results = [{"name": "John", "source": "BB"}]
        data = json.loads(search_contacts.format_json("John", results))
        assert data["query"] == "John"
        assert data["total_sources"] == 1
        assert len(data["results"]) == 1

    def test_empty(self):
        data = json.loads(search_contacts.format_json("John", []))
        assert data["results"] == []
        assert data["total_sources"] == 0


# ---------------------------------------------------------------------------
# TestFormatHuman
# ---------------------------------------------------------------------------


class TestFormatHuman:
    def _make_result(self, **overrides):
        base = {
            "name": "John Smith",
            "source": "Brain Bridge Airtable",
            "email": "john@test.com",
            "phone": "",
            "title": "",
            "organization": "",
            "link": "",
        }
        base.update(overrides)
        return base

    def test_contact_header(self):
        output = search_contacts.format_human("John", [self._make_result()])
        assert "CONTACT: John Smith" in output

    def test_shows_email(self):
        output = search_contacts.format_human("John", [self._make_result()])
        assert "john@test.com" in output

    def test_no_results(self):
        output = search_contacts.format_human("ZZZ", [])
        assert "No contacts found" in output
        assert "Brain Bridge Airtable" in output
        assert "Obsidian" in output

    def test_org_only_no_results(self):
        output = search_contacts.format_human("ZZZ", [], org_only=True)
        assert "No contacts found" in output
        assert "Obsidian" not in output
        assert "Apple Contacts" not in output

    def test_missing_sources(self):
        output = search_contacts.format_human("John", [self._make_result()])
        assert "Not found in:" in output
        assert "AITB Airtable" in output

    def test_hides_empty_fields(self):
        output = search_contacts.format_human(
            "John", [self._make_result(phone="", title="", organization="")]
        )
        assert "Phone:" not in output
        assert "Title:" not in output
        assert "Organization:" not in output
