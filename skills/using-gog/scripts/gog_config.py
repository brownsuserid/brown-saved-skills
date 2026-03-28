"""Shared config loading for gog scripts.

Config resolution: --config flag > GOG_ACCOUNTS_CONFIG env var > ../configs/personal.yaml
"""

import os
import sys
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "personal.yaml"


def resolve_config_path(cli_config: str | None = None) -> Path:
    """Resolve config file path: --config flag > env var > default."""
    if cli_config:
        return Path(cli_config)
    env_config = os.environ.get("GOG_ACCOUNTS_CONFIG")
    if env_config:
        return Path(env_config)
    return DEFAULT_CONFIG_PATH


def load_config(config_path: str | Path | None = None) -> dict:
    """Load gog accounts configuration from a YAML config file."""
    path = resolve_config_path(str(config_path) if config_path else None)
    if not path.exists():
        print(f"Error: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def get_accounts(config: dict) -> dict[str, str]:
    """Return {label: email} mapping from config."""
    return {label: acct["email"] for label, acct in config.get("accounts", {}).items()}


def get_account_labels(config: dict) -> dict[str, str]:
    """Return {email: label} reverse mapping."""
    return {acct["email"]: label for label, acct in config.get("accounts", {}).items()}


def get_account_details(config: dict) -> dict[str, dict]:
    """Return full account details keyed by label."""
    return config.get("accounts", {})
