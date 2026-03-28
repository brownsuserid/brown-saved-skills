"""Tests for config_manager module.

BUG: These tests pass individually but fail when run together.
Running `pytest tests/test_config_manager.py` produces failures
because tests pollute each other through the module-level _config_cache
and environment variables.
"""

import os

from src.config_manager import (
    clear_cache,
    get_cached_config,
    get_database_url,
    load_config,
)


class TestLoadConfig:
    def test_development_defaults(self):
        config = load_config("development")
        assert config["debug"] is True
        assert config["log_level"] == "DEBUG"
        assert config["database"]["host"] == "localhost"

    def test_production_config(self):
        config = load_config("production")
        assert config["debug"] is False
        assert config["log_level"] == "INFO"
        assert config["database"]["host"] == "prod-db.internal"

    def test_api_config_from_env(self):
        os.environ["API_BASE_URL"] = "https://api.staging.example.com"
        os.environ["API_TIMEOUT"] = "60"
        os.environ["API_KEY"] = "staging-secret-key"

        config = load_config("staging")
        assert config["api"]["base_url"] == "https://api.staging.example.com"
        assert config["api"]["timeout"] == 60
        assert config["api"]["api_key"] == "staging-secret-key"

    def test_api_defaults_without_env(self):
        # BUG: This test expects default values, but test_api_config_from_env
        # set environment variables that persist across tests
        config = load_config("development")
        assert config["api"]["base_url"] == "http://localhost:8000"
        assert config["api"]["timeout"] == 30
        assert config["api"]["api_key"] == "dev-key-placeholder"


class TestGetCachedConfig:
    def test_returns_none_when_not_cached(self):
        # BUG: This test expects None, but load_config in previous tests
        # populated _config_cache at the module level
        result = get_cached_config("test-env-that-was-never-loaded")
        assert result is None

    def test_cache_hit_after_load(self):
        load_config("development")
        cached = get_cached_config("development")
        assert cached is not None
        assert cached["app_name"] == "MyApp"

    def test_clear_cache_works(self):
        load_config("development")
        clear_cache()
        assert get_cached_config("development") is None


class TestGetDatabaseUrl:
    def test_development_url(self):
        config = load_config("development")
        url = get_database_url(config)
        assert url == "postgresql://localhost:5432/myapp_dev"

    def test_production_url(self):
        config = load_config("production")
        url = get_database_url(config)
        assert url == "postgresql://prod-db.internal:5432/myapp_prod"
