#!/usr/bin/env python3
"""Cross-validate deploy configuration across all three config layers.

Validates consistency between:
1. .env.{env}.{customer} — secrets and AWS targeting
2. config/customers/{customer}.yaml — customer feature flags and settings
3. cdk.json — CDK context and infrastructure config

CUSTOMIZE: Update REQUIRED_ENV_VARS and REQUIRED_YAML_KEYS for your project.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# CUSTOMIZE: Variables that must exist in .env files
REQUIRED_ENV_VARS: list[str] = [
    "AWS_ACCOUNT_ID",
    "AWS_REGION",
    "AWS_PROFILE",
]

# CUSTOMIZE: Keys that must exist in customer YAML files
REQUIRED_YAML_KEYS: list[str] = [
    "customer_name",
    "environment",
]

# CUSTOMIZE: Context keys that must exist in cdk.json
REQUIRED_CDK_CONTEXT: list[str] = []


def load_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, skipping comments and blank lines."""
    env_vars: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        env_vars[key.strip()] = value
    return env_vars


def load_customer_yaml(yaml_path: Path) -> dict:
    """Load customer YAML config."""
    return yaml.safe_load(yaml_path.read_text()) or {}


def load_cdk_json(cdk_path: Path) -> dict:
    """Load cdk.json and return the context dict."""
    data = json.loads(cdk_path.read_text())
    return data.get("context", {})


class ConfigValidationError:
    """A single validation finding."""

    def __init__(self, severity: str, source: str, message: str) -> None:
        self.severity = severity  # "error" or "warning"
        self.source = source
        self.message = message

    def __str__(self) -> str:
        icon = "ERROR" if self.severity == "error" else "WARN"
        return f"[{icon}] [{self.source}] {self.message}"


def validate_env(env_vars: dict[str, str], env_path: str) -> list[ConfigValidationError]:
    """Check .env file for required vars and placeholder values."""
    errors: list[ConfigValidationError] = []

    for var in REQUIRED_ENV_VARS:
        if var not in env_vars:
            errors.append(ConfigValidationError("error", env_path, f"Missing required var: {var}"))
        elif not env_vars[var] or env_vars[var].startswith("<"):
            errors.append(
                ConfigValidationError(
                    "error", env_path, f"Placeholder value for {var}: '{env_vars[var]}'"
                )
            )

    return errors


def validate_yaml(yaml_config: dict, yaml_path: str) -> list[ConfigValidationError]:
    """Check customer YAML for required keys."""
    errors: list[ConfigValidationError] = []

    for key in REQUIRED_YAML_KEYS:
        if key not in yaml_config:
            errors.append(ConfigValidationError("error", yaml_path, f"Missing required key: {key}"))

    return errors


def validate_cdk_context(context: dict, cdk_path: str) -> list[ConfigValidationError]:
    """Check cdk.json context for required keys."""
    errors: list[ConfigValidationError] = []

    for key in REQUIRED_CDK_CONTEXT:
        if key not in context:
            errors.append(
                ConfigValidationError("error", cdk_path, f"Missing required context key: {key}")
            )

    return errors


def cross_validate(
    env_vars: dict[str, str],
    yaml_config: dict,
    cdk_context: dict,
) -> list[ConfigValidationError]:
    """Cross-validate consistency between config layers.

    CUSTOMIZE: Add project-specific cross-validation rules.
    """
    errors: list[ConfigValidationError] = []

    # Check environment consistency
    env_from_dotenv = env_vars.get("ENVIRONMENT", "")
    env_from_yaml = yaml_config.get("environment", "")
    if env_from_dotenv and env_from_yaml and env_from_dotenv != env_from_yaml:
        errors.append(
            ConfigValidationError(
                "error",
                "cross-validation",
                f"Environment mismatch: .env has '{env_from_dotenv}', YAML has '{env_from_yaml}'",
            )
        )

    # Check customer name consistency
    customer_from_yaml = yaml_config.get("customer_name", "")
    customer_from_env = env_vars.get("CUSTOMER_NAME", "")
    if customer_from_env and customer_from_yaml and customer_from_env != customer_from_yaml:
        errors.append(
            ConfigValidationError(
                "error",
                "cross-validation",
                f"Customer mismatch: .env has '{customer_from_env}', "
                f"YAML has '{customer_from_yaml}'",
            )
        )

    # Check region consistency
    region_from_env = env_vars.get("AWS_REGION", "")
    region_from_yaml = yaml_config.get("aws_region", "")
    if region_from_env and region_from_yaml and region_from_env != region_from_yaml:
        errors.append(
            ConfigValidationError(
                "warning",
                "cross-validation",
                f"Region mismatch: .env has '{region_from_env}', "
                f"YAML has '{region_from_yaml}'. Verify this is intentional.",
            )
        )

    return errors


def validate_all(
    env_path: Path | None = None,
    yaml_path: Path | None = None,
    cdk_path: Path | None = None,
) -> list[ConfigValidationError]:
    """Run all validations and return combined errors."""
    all_errors: list[ConfigValidationError] = []

    env_vars: dict[str, str] = {}
    yaml_config: dict = {}
    cdk_context: dict = {}

    if env_path and env_path.exists():
        env_vars = load_env_file(env_path)
        all_errors.extend(validate_env(env_vars, str(env_path)))
    elif env_path:
        all_errors.append(ConfigValidationError("error", str(env_path), "File not found"))

    if yaml_path and yaml_path.exists():
        yaml_config = load_customer_yaml(yaml_path)
        all_errors.extend(validate_yaml(yaml_config, str(yaml_path)))
    elif yaml_path:
        all_errors.append(ConfigValidationError("warning", str(yaml_path), "File not found"))

    if cdk_path and cdk_path.exists():
        cdk_context = load_cdk_json(cdk_path)
        all_errors.extend(validate_cdk_context(cdk_context, str(cdk_path)))

    # Cross-validate if we have multiple sources
    if env_vars and yaml_config:
        all_errors.extend(cross_validate(env_vars, yaml_config, cdk_context))

    return all_errors


def main() -> None:
    """CLI entry point for standalone validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-validate deploy configuration layers")
    parser.add_argument("-e", "--env-file", type=Path, help=".env file path")
    parser.add_argument("-y", "--yaml-file", type=Path, help="Customer YAML path")
    parser.add_argument("-k", "--cdk-json", type=Path, help="cdk.json path")
    args = parser.parse_args()

    if not any([args.env_file, args.yaml_file, args.cdk_json]):
        parser.error("Provide at least one config file to validate")

    errors = validate_all(args.env_file, args.yaml_file, args.cdk_json)

    if not errors:
        print("All config validations passed.")
        sys.exit(0)

    has_errors = False
    for err in errors:
        print(err)
        if err.severity == "error":
            has_errors = True

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
