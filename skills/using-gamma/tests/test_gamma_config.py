"""Tests for gamma_config.py — API key and header configuration."""

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "scripts"),
)

import gamma_config


class TestGetApiKey:
    """get_api_key() reads GAMMA_API_KEY from environment."""

    def test_returns_key_from_env(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("GAMMA_API_KEY", "test-key-123")

        # Act
        result = gamma_config.get_api_key()

        # Assert
        assert result == "test-key-123"

    def test_missing_key_exits(self, monkeypatch):
        # Arrange
        monkeypatch.delenv("GAMMA_API_KEY", raising=False)

        # Act & Assert
        with pytest.raises(SystemExit):
            gamma_config.get_api_key()


class TestGetHeaders:
    """get_headers() builds auth headers for API requests."""

    def test_includes_api_key(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("GAMMA_API_KEY", "my-key")

        # Act
        headers = gamma_config.get_headers()

        # Assert
        assert headers["X-API-KEY"] == "my-key"
        assert headers["Content-Type"] == "application/json"


class TestConstants:
    """Module-level constants have expected values."""

    def test_api_base_url(self):
        assert "gamma.app" in gamma_config.API_BASE_URL

    def test_valid_formats(self):
        assert "presentation" in gamma_config.VALID_FORMATS
        assert "document" in gamma_config.VALID_FORMATS

    def test_defaults(self):
        assert gamma_config.DEFAULT_FORMAT == "presentation"
        assert gamma_config.DEFAULT_NUM_CARDS == 10
