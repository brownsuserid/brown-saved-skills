"""Tests for gog_config.py and config-driven script behavior."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from gog_config import (
    get_account_details,
    get_account_labels,
    get_accounts,
    load_config,
    resolve_config_path,
)

SAMPLE_CONFIG = {
    "accounts": {
        "personal": {
            "email": "user@gmail.com",
            "display_name": "Test User",
            "signature": "\n\nBest,\nTest User",
        },
        "work": {
            "email": "user@company.com",
            "display_name": "Test User | Company",
            "signature": "\n\nBest,\nTest User\nCompany Inc.",
        },
    }
}

SINGLE_ACCOUNT_CONFIG = {
    "accounts": {
        "work": {
            "email": "user@company.com",
            "display_name": "Test User | Company",
            "signature": "\n\nBest,\nTest User",
        },
    }
}


class TestResolveConfigPath:
    def test_cli_flag_takes_priority(self):
        with patch.dict("os.environ", {"GOG_ACCOUNTS_CONFIG": "/env/config.yaml"}):
            result = resolve_config_path("/cli/config.yaml")
            assert result == Path("/cli/config.yaml")

    def test_env_var_used_when_no_cli(self):
        with patch.dict("os.environ", {"GOG_ACCOUNTS_CONFIG": "/env/config.yaml"}):
            result = resolve_config_path(None)
            assert result == Path("/env/config.yaml")

    def test_default_when_no_cli_or_env(self):
        with patch.dict("os.environ", {}, clear=True):
            result = resolve_config_path(None)
            assert result.name == "personal.yaml"
            assert "configs" in str(result)

    def test_empty_string_cli_uses_env(self):
        with patch.dict("os.environ", {"GOG_ACCOUNTS_CONFIG": "/env/config.yaml"}):
            result = resolve_config_path("")
            assert result == Path("/env/config.yaml")


class TestLoadConfig:
    def test_loads_from_explicit_path(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            "accounts:\n  test:\n    email: test@example.com\n    display_name: Test\n"
        )
        result = load_config(str(config_file))
        assert "test" in result["accounts"]
        assert result["accounts"]["test"]["email"] == "test@example.com"

    def test_loads_from_env_var(self, tmp_path):
        config_file = tmp_path / "env.yaml"
        config_file.write_text(
            "accounts:\n  env:\n    email: env@example.com\n    display_name: Env\n"
        )
        with patch.dict("os.environ", {"GOG_ACCOUNTS_CONFIG": str(config_file)}):
            result = load_config()
            assert "env" in result["accounts"]

    def test_exits_on_missing_file(self):
        with pytest.raises(SystemExit):
            load_config("/nonexistent/config.yaml")


class TestGetAccounts:
    def test_returns_label_to_email_mapping(self):
        result = get_accounts(SAMPLE_CONFIG)
        assert result == {
            "personal": "user@gmail.com",
            "work": "user@company.com",
        }

    def test_single_account(self):
        result = get_accounts(SINGLE_ACCOUNT_CONFIG)
        assert result == {"work": "user@company.com"}

    def test_empty_config(self):
        result = get_accounts({"accounts": {}})
        assert result == {}

    def test_missing_accounts_key(self):
        result = get_accounts({})
        assert result == {}


class TestGetAccountLabels:
    def test_returns_email_to_label_mapping(self):
        result = get_account_labels(SAMPLE_CONFIG)
        assert result == {
            "user@gmail.com": "personal",
            "user@company.com": "work",
        }

    def test_single_account(self):
        result = get_account_labels(SINGLE_ACCOUNT_CONFIG)
        assert result == {"user@company.com": "work"}


class TestGetAccountDetails:
    def test_returns_full_details(self):
        result = get_account_details(SAMPLE_CONFIG)
        assert "personal" in result
        assert result["personal"]["email"] == "user@gmail.com"
        assert result["personal"]["display_name"] == "Test User"
        assert "signature" in result["personal"]

    def test_single_account(self):
        result = get_account_details(SINGLE_ACCOUNT_CONFIG)
        assert list(result.keys()) == ["work"]


class TestDraftEmailBuildBody:
    """Test build_body from draft_email.py with config-driven accounts."""

    def test_appends_signature(self):
        from draft_email import build_body

        accounts = SAMPLE_CONFIG["accounts"]
        result = build_body("Hello", "personal", accounts, include_signature=True)
        assert "Best," in result
        assert "Test User" in result

    def test_no_signature_when_suppressed(self):
        from draft_email import build_body

        accounts = SAMPLE_CONFIG["accounts"]
        result = build_body("Hello", "personal", accounts, include_signature=False)
        assert result == "Hello"

    def test_skips_double_signature(self):
        from draft_email import build_body

        accounts = SAMPLE_CONFIG["accounts"]
        result = build_body(
            "Hello\n\nBest,", "personal", accounts, include_signature=True
        )
        assert result.count("Best,") == 1

    def test_no_signature_field_graceful(self):
        from draft_email import build_body

        accounts = {"nosig": {"email": "x@y.com", "display_name": "X"}}
        result = build_body("Hello", "nosig", accounts, include_signature=True)
        assert result == "Hello"


class TestSearchDriveBuildQuery:
    """Test build_query from search_drive.py (no config dependency)."""

    def test_raw_query_passthrough(self):
        from search_drive import build_query

        query, is_raw = build_query("mimeType='application/pdf'", None, None, raw=True)
        assert query == "mimeType='application/pdf'"
        assert is_raw is True

    def test_plain_text_query(self):
        from search_drive import build_query

        query, is_raw = build_query("budget report", None, None, raw=False)
        assert query == "budget report"
        assert is_raw is False

    def test_type_filter_adds_mime(self):
        from search_drive import build_query

        query, is_raw = build_query("budget", "pdf", None, raw=False)
        assert "application/pdf" in query
        assert "fullText contains 'budget'" in query
        assert is_raw is True

    def test_recent_filter_adds_modified_time(self):
        from search_drive import build_query

        query, is_raw = build_query("notes", None, 7, raw=False)
        assert "modifiedTime >" in query
        assert is_raw is True


class TestSearchEmailBuildQuery:
    """Test build_query from search_email.py (no config dependency)."""

    def test_raw_query_passthrough(self):
        from search_email import build_query

        result = build_query("from:bob subject:meeting", None, raw=True)
        assert result == "from:bob subject:meeting"

    def test_plain_text_query(self):
        from search_email import build_query

        result = build_query("invoice", None, raw=False)
        assert result == "invoice"

    def test_recent_days_appended(self):
        from search_email import build_query

        result = build_query("invoice", 7, raw=False)
        assert "newer_than:7d" in result


class TestConfigIsolation:
    """Test that different configs produce different account sets."""

    def test_personal_config_has_all_accounts(self, tmp_path):
        config_file = tmp_path / "personal.yaml"
        config_file.write_text(
            "accounts:\n"
            "  personal:\n    email: a@gmail.com\n    display_name: A\n"
            "  work:\n    email: a@work.com\n    display_name: A Work\n"
        )
        config = load_config(str(config_file))
        assert len(get_accounts(config)) == 2

    def test_scoped_config_has_one_account(self, tmp_path):
        config_file = tmp_path / "work.yaml"
        config_file.write_text(
            "accounts:\n  work:\n    email: a@work.com\n    display_name: A Work\n"
        )
        config = load_config(str(config_file))
        accounts = get_accounts(config)
        assert len(accounts) == 1
        assert "work" in accounts
