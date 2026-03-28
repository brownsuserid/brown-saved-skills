#!/usr/bin/env python3
"""CDK deployment script with multi-environment and multi-customer support.

Usage:
    python deploy.py -e ENVIRONMENT -c CUSTOMER [OPTIONS]

CUSTOMIZATION REQUIRED:
Search for "CUSTOMIZE:" comments and update values for your project:
  - PROJECT_NAME: Your project identifier
  - VALID_ENVIRONMENTS: Allowed environment names
  - ACCOUNT_PROFILE_MAP: AWS account-to-profile mappings
  - REQUIRED_ENV_VARS: Variables required in .env files
  - REQUIRED_CONFIG_FIELDS: Fields required in customer YAML configs
  - CDK context flags in build_cdk_command()
  - Health check endpoints in run_post_deployment_checks()
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Try to import yaml — fail gracefully with install instructions
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(2)


# ============================================================================
# Configuration — CUSTOMIZE: Update these for your project
# ============================================================================

# CUSTOMIZE: Project name (used in prefixes and logging)
PROJECT_NAME = "my-project"

# CUSTOMIZE: Valid environments
VALID_ENVIRONMENTS = ["dev", "staging", "prod"]

# CUSTOMIZE: AWS account ID to profile mapping
ACCOUNT_PROFILE_MAP: dict[str, str] = {
    # "123456789012": "default",
    # "987654321098": "production",
}

# CUSTOMIZE: Required variables in .env files (secrets)
REQUIRED_ENV_VARS = ["AWS_ACCOUNT_ID", "AWS_REGION", "PROJECT_PREFIX"]

# CUSTOMIZE: Required fields in customer YAML config
REQUIRED_CONFIG_FIELDS = ["customer_name", "project_prefix"]

# CUSTOMIZE: Required CLI tools
REQUIRED_TOOLS = ["aws", "cdk", "jq"]
OPTIONAL_TOOLS = ["docker", "cfn-lint", "checkov"]

# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 1
EXIT_MISSING_DEPS = 2
EXIT_AWS_AUTH_FAILED = 3
EXIT_ACCOUNT_MISMATCH = 4
EXIT_CONFIG_INVALID = 5
EXIT_SECRETS_FAILED = 6
EXIT_CDK_FAILED = 10
EXIT_HEALTH_CHECK_FAILED = 11
EXIT_USER_CANCELLED = 20


# ============================================================================
# Config Separation
# ============================================================================
#
# This project separates configuration into three layers:
#
#   .env.{env}.{customer}                  — Secrets only (API keys, tokens)
#                                            Git-ignored. Never committed.
#
#   config/customers/{customer}.yaml       — Customer config (feature flags,
#                                            preferences, non-secret settings)
#                                            Committed to git.
#
#   cdk.json / cdk.context.json            — Infrastructure config (stack
#                                            settings, CDK context defaults)
#                                            Committed to git.
#
# The deploy script loads all three and validates consistency between them.
# Secrets go in .env. Everything else goes in YAML or cdk.json.
# ============================================================================


# ============================================================================
# Timing and Performance Tracking
# ============================================================================


@dataclass
class PhaseTimer:
    """Track timing for each deployment phase."""

    phases: list[dict[str, Any]] = field(default_factory=list)
    _current_phase: str | None = None
    _phase_start: float | None = None
    deploy_start: float = field(default_factory=time.time)

    def start_phase(self, name: str) -> None:
        if self._current_phase:
            self.end_phase()
        self._current_phase = name
        self._phase_start = time.time()
        log_phase(name)

    def end_phase(self) -> None:
        if self._current_phase and self._phase_start:
            elapsed = time.time() - self._phase_start
            self.phases.append(
                {
                    "phase": self._current_phase,
                    "duration_seconds": round(elapsed, 1),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            log_info(f"  Phase completed in {elapsed:.1f}s")
        self._current_phase = None
        self._phase_start = None

    def total_duration(self) -> float:
        return round(time.time() - self.deploy_start, 1)

    def summary(self) -> str:
        lines = ["Phase Timing Summary:", "-" * 50]
        for p in self.phases:
            lines.append(f"  {p['phase']:<35} {p['duration_seconds']:>6.1f}s")
        lines.append("-" * 50)
        lines.append(f"  {'TOTAL':<35} {self.total_duration():>6.1f}s")

        # Flag slow phases (>60s)
        slow = [p for p in self.phases if p["duration_seconds"] > 60]
        if slow:
            lines.append("")
            lines.append("Performance Notes:")
            for p in slow:
                lines.append(
                    f"  - {p['phase']} took {p['duration_seconds']:.1f}s — consider optimization"
                )
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        data = {
            "total_duration_seconds": self.total_duration(),
            "phases": self.phases,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path.write_text(json.dumps(data, indent=2))
        log_info(f"Timing data saved to {path}")


# ============================================================================
# Logging
# ============================================================================

_verbose = False


def log_info(msg: str) -> None:
    print(msg)


def log_error(msg: str) -> None:
    print(msg, file=sys.stderr)


def log_warning(msg: str) -> None:
    print(f"WARNING: {msg}")


def log_verbose(msg: str) -> None:
    if _verbose:
        print(f"[DEBUG] {msg}")


def log_phase(name: str) -> None:
    print()
    print("=" * 50)
    print(f"  {name}")
    print("=" * 50)
    print()


# ============================================================================
# Shell Command Helpers
# ============================================================================


def run_cmd(
    cmd: list[str] | str,
    *,
    capture: bool = False,
    check: bool = True,
    shell: bool = False,
) -> subprocess.CompletedProcess:
    """Run a shell command with consistent error handling."""
    log_verbose(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
            shell=shell,
        )
        return result
    except subprocess.CalledProcessError as e:
        if capture:
            log_error(f"Command failed: {cmd}")
            if e.stdout:
                log_error(f"stdout: {e.stdout.strip()}")
            if e.stderr:
                log_error(f"stderr: {e.stderr.strip()}")
        raise


def tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


# ============================================================================
# Configuration Loading
# ============================================================================


def load_env_file(env: str, customer: str) -> dict[str, str]:
    """Load secrets from .env.{env}.{customer} file.

    These files contain ONLY secrets (API keys, tokens, credentials).
    Non-secret config belongs in customer YAML files.
    """
    env_file = Path(f".env.{env}.{customer}")
    if not env_file.exists():
        log_error(f"ERROR: Secrets file not found: {env_file}")
        log_error(f"  Create from template: cp .env.TEMPLATE {env_file}")
        log_error("  Then fill in real credentials.")
        sys.exit(EXIT_CONFIG_INVALID)

    env_vars: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip().strip('"').strip("'")

    # Validate required vars
    missing = [v for v in REQUIRED_ENV_VARS if v not in env_vars or not env_vars[v]]
    if missing:
        log_error(f"ERROR: Missing required variables in {env_file}:")
        for v in missing:
            log_error(f"  - {v}")
        sys.exit(EXIT_CONFIG_INVALID)

    # Warn about placeholder values
    placeholders = [
        k
        for k, v in env_vars.items()
        if "placeholder" in v.lower() or "your_" in v.lower() or v.endswith("_here")
    ]
    if placeholders:
        log_warning(f"Placeholder values detected in {env_file}:")
        for k in placeholders:
            log_warning(f"  - {k} = {env_vars[k]}")

    return env_vars


def load_customer_config(customer: str) -> dict[str, Any]:
    """Load customer config from config/customers/{customer}.yaml.

    These files contain non-secret customer configuration:
    feature flags, preferences, integration settings.
    Committed to git.
    """
    config_path = Path(f"config/customers/{customer}.yaml")
    if not config_path.exists():
        log_error(f"ERROR: Customer config not found: {config_path}")
        log_error("  Create the file with customer-specific settings.")
        log_error(f"  Required fields: {', '.join(REQUIRED_CONFIG_FIELDS)}")
        sys.exit(EXIT_CONFIG_INVALID)

    config = yaml.safe_load(config_path.read_text()) or {}

    # Validate required fields
    missing = [f for f in REQUIRED_CONFIG_FIELDS if f not in config]
    if missing:
        log_error(f"ERROR: Missing required fields in {config_path}:")
        for f in missing:
            log_error(f"  - {f}")
        sys.exit(EXIT_CONFIG_INVALID)

    return config


def validate_config_consistency(
    env: str,
    customer: str,
    env_vars: dict[str, str],
    customer_config: dict[str, Any],
) -> None:
    """Validate that .env secrets and customer YAML are consistent.

    Catches mismatches like different project prefixes or customer names
    that could cause deployment to the wrong resources.
    """
    errors: list[str] = []

    # Check customer name matches
    config_customer = customer_config.get("customer_name", "")
    if config_customer and config_customer != customer:
        errors.append(
            f"Customer name mismatch: YAML has '{config_customer}', expected '{customer}'"
        )

    # Check project prefix consistency
    env_prefix = env_vars.get("PROJECT_PREFIX", "")
    config_prefix = customer_config.get("project_prefix", "")
    if env_prefix and config_prefix and env_prefix != config_prefix:
        errors.append(
            f"Project prefix mismatch: .env has '{env_prefix}', YAML has '{config_prefix}'"
        )

    if errors:
        log_error("ERROR: Configuration consistency check failed:")
        for e in errors:
            log_error(f"  - {e}")
        log_error("")
        log_error(f"  Secrets file: .env.{env}.{customer}")
        log_error(f"  Config file:  config/customers/{customer}.yaml")
        sys.exit(EXIT_CONFIG_INVALID)

    log_info("Config consistency validated")


# ============================================================================
# AWS Authentication
# ============================================================================


def set_aws_profile(account_id: str) -> None:
    """Set AWS_PROFILE based on account ID mapping."""
    profile = ACCOUNT_PROFILE_MAP.get(account_id)
    if profile:
        os.environ["AWS_PROFILE"] = profile
        log_info(f"AWS profile set to '{profile}' for account {account_id}")
    else:
        log_warning(f"No profile mapping for account {account_id}")
        log_info("Using current AWS credentials")


def verify_aws_credentials() -> dict[str, str]:
    """Verify AWS credentials and return identity info."""
    log_info("Verifying AWS credentials...")
    try:
        result = run_cmd(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture=True,
        )
        identity = json.loads(result.stdout)
        log_info(f"  Account: {identity['Account']}")
        log_info(f"  Identity: {identity['Arn']}")
        return identity
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        log_error("ERROR: AWS credentials not configured or expired")
        log_error("  Run 'aws configure' or refresh your SSO session")
        sys.exit(EXIT_AWS_AUTH_FAILED)


def verify_target_account(expected_account: str) -> None:
    """Verify the authenticated account matches expectations."""
    identity = verify_aws_credentials()
    actual = identity["Account"]
    if actual != expected_account:
        log_error("")
        log_error("=" * 50)
        log_error("  ACCOUNT MISMATCH DETECTED")
        log_error("=" * 50)
        log_error(f"  Expected: {expected_account}")
        log_error(f"  Actual:   {actual}")
        log_error("")
        log_error("Possible causes:")
        log_error("  1. Wrong AWS_PROFILE selected")
        log_error("  2. .env file has wrong AWS_ACCOUNT_ID")
        log_error("  3. Credentials configured for different account")
        sys.exit(EXIT_ACCOUNT_MISMATCH)
    log_info(f"Target account verified: {expected_account}")


# ============================================================================
# Pre-flight Checks
# ============================================================================


def check_dependencies() -> None:
    """Verify required and optional tools are installed."""
    log_info("Checking dependencies...")
    for tool in REQUIRED_TOOLS:
        if not tool_exists(tool):
            log_error(f"ERROR: Required tool '{tool}' not found")
            log_error(f"  Install {tool} before running deployment")
            sys.exit(EXIT_MISSING_DEPS)
    log_info("Required tools present")

    for tool in OPTIONAL_TOOLS:
        if not tool_exists(tool):
            log_info(f"  Optional: {tool} not installed — some checks will be skipped")


def ensure_cdk_bootstrap(account_id: str, region: str) -> None:
    """Check CDK bootstrap status, bootstrap if needed."""
    log_info("Checking CDK bootstrap status...")
    try:
        result = run_cmd(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "CDKToolkit",
                "--region",
                region,
                "--query",
                "Stacks[0].StackStatus",
                "--output",
                "text",
            ],
            capture=True,
        )
        status = result.stdout.strip()
        if status in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
            log_info(f"CDK bootstrapped for {account_id}/{region}")
            return
    except subprocess.CalledProcessError:
        status = "DOES_NOT_EXIST"

    log_info("CDK not bootstrapped. Running bootstrap...")
    run_cmd(["cdk", "bootstrap", f"aws://{account_id}/{region}"])
    log_info("CDK bootstrap complete")


def check_pending_operations(*, force: bool = False) -> None:
    """Check for in-progress CloudFormation operations."""
    log_info("Checking for pending CloudFormation operations...")
    try:
        result = run_cmd(
            [
                "aws",
                "cloudformation",
                "list-stacks",
                "--stack-status-filter",
                "UPDATE_IN_PROGRESS",
                "CREATE_IN_PROGRESS",
                "DELETE_IN_PROGRESS",
                "--query",
                "StackSummaries[].StackName",
                "--output",
                "text",
            ],
            capture=True,
            check=False,
        )
        pending = result.stdout.strip()
        if pending:
            log_warning("Stacks with pending operations:")
            for stack in pending.split():
                log_warning(f"  - {stack}")
            if not force:
                log_error("Aborting. Use --force to continue anyway.")
                sys.exit(EXIT_CDK_FAILED)
        else:
            log_info("No pending operations")
    except Exception:
        log_info("Could not check pending operations — continuing")


def confirm_production(env: str, customer: str, *, ci: bool = False) -> None:
    """Require confirmation for production deployments."""
    if env != "prod":
        return
    print()
    print("=" * 50)
    print("  PRODUCTION DEPLOYMENT CONFIRMATION")
    print("=" * 50)
    print(f"  Customer:    {customer}")
    print(f"  Environment: {env}")
    print()

    if ci:
        log_info("CI environment detected — skipping confirmation")
        return

    answer = input("Type 'deploy' to confirm: ")
    if answer != "deploy":
        log_error("Deployment cancelled")
        sys.exit(EXIT_USER_CANCELLED)


# ============================================================================
# Pre-Deploy Structural Checks
# ============================================================================


def run_pre_deploy_checks(synth_dir: str = "cdk.out") -> None:
    """Run cfn-lint, Checkov, and loop heuristics on synthesized templates."""
    log_info("Running pre-deploy structural checks...")

    # cfn-lint (blocking)
    if tool_exists("cfn-lint"):
        log_info("  Running cfn-lint...")
        result = run_cmd(
            ["cfn-lint", f"{synth_dir}/*.template.json"],
            capture=True,
            check=False,
            shell=True,
        )
        if "E3004" in (result.stdout + result.stderr):
            log_error("CIRCULAR DEPENDENCY detected — fix before deploying")
            log_error(result.stdout)
            sys.exit(EXIT_CDK_FAILED)
        log_info("  cfn-lint passed")
    else:
        log_info("  cfn-lint not installed — skipping")

    # Checkov (non-blocking)
    if tool_exists("checkov"):
        log_info("  Running Checkov...")
        result = run_cmd(
            [
                "checkov",
                "-d",
                synth_dir,
                "--framework",
                "cloudformation",
                "--check-severity",
                "HIGH,CRITICAL",
                "--compact",
                "--quiet",
            ],
            capture=True,
            check=False,
        )
        failed_count = result.stdout.count("FAILED")
        if failed_count > 0:
            log_warning(f"Checkov found {failed_count} HIGH/CRITICAL issue(s)")
        else:
            log_info("  Checkov passed")
    else:
        log_info("  Checkov not installed — skipping")


# ============================================================================
# Secrets Management
# ============================================================================


def push_secrets(
    env: str,
    customer: str,
    env_vars: dict[str, str],
    region: str,
) -> None:
    """Push secrets from .env to AWS Secrets Manager.

    CUSTOMIZE: Define your secret groups and their env var mappings.
    """
    log_info("Pushing secrets to AWS Secrets Manager...")
    prefix = env_vars.get("PROJECT_PREFIX", PROJECT_NAME)
    log_info(f"Using secret prefix: {prefix}/{customer}")

    # CUSTOMIZE: Map env vars to secret groups
    # Example:
    # secret_groups = {
    #     f"{prefix}/{customer}/api-credentials": {
    #         "ANTHROPIC_API_KEY": env_vars.get("ANTHROPIC_API_KEY", ""),
    #     },
    #     f"{prefix}/{customer}/slack": {
    #         "SLACK_BOT_TOKEN": env_vars.get("SLACK_BOT_TOKEN", ""),
    #         "SLACK_SIGNING_SECRET": env_vars.get("SLACK_SIGNING_SECRET", ""),
    #     },
    # }
    #
    # for secret_name, secret_data in secret_groups.items():
    #     secret_json = json.dumps(secret_data)
    #     try:
    #         run_cmd(
    #             ["aws", "secretsmanager", "describe-secret",
    #              "--secret-id", secret_name, "--region", region],
    #             capture=True,
    #         )
    #         # Update existing
    #         run_cmd(
    #             ["aws", "secretsmanager", "put-secret-value",
    #              "--secret-id", secret_name,
    #              "--secret-string", secret_json,
    #              "--region", region],
    #             capture=True,
    #         )
    #         log_info(f"  Updated: {secret_name}")
    #     except subprocess.CalledProcessError:
    #         # Create new
    #         run_cmd(
    #             ["aws", "secretsmanager", "create-secret",
    #              "--name", secret_name,
    #              "--secret-string", secret_json,
    #              "--region", region],
    #             capture=True,
    #         )
    #         log_info(f"  Created: {secret_name}")

    log_info("Secrets management complete")


# ============================================================================
# CDK Deployment
# ============================================================================


def build_cdk_command(
    env: str,
    customer: str,
    env_vars: dict[str, str],
    customer_config: dict[str, Any],
    *,
    stack_filter: str | None = None,
    slack_enabled: bool = True,
) -> list[str]:
    """Build the CDK deploy command with context flags."""
    cmd = ["cdk", "deploy", "--require-approval", "never"]

    # Core context
    cmd += ["-c", f"environment={env}"]
    cmd += ["-c", f"customer={customer}"]
    cmd += ["-c", f"accountId={env_vars.get('AWS_ACCOUNT_ID', '')}"]
    cmd += ["-c", f"region={env_vars.get('AWS_REGION', '')}"]

    # CUSTOMIZE: Add integration toggles from customer config
    cmd += ["-c", f"slackEnabled={'true' if slack_enabled else 'false'}"]

    # Stack filter or deploy all
    if stack_filter:
        cmd.append(stack_filter)
    else:
        cmd.append("--all")

    return cmd


def run_cdk_deploy(cmd: list[str]) -> None:
    """Execute CDK deployment."""
    log_info(f"CDK command: {' '.join(cmd)}")
    print()

    # Clean stale artifacts
    cdk_out = Path("cdk.out")
    if cdk_out.exists():
        shutil.rmtree(cdk_out)

    try:
        run_cmd(cmd)
        log_info("CDK deployment completed")
    except subprocess.CalledProcessError:
        log_error("")
        log_error("=" * 50)
        log_error("  DEPLOYMENT FAILED")
        log_error("=" * 50)
        log_error("")
        log_error("CDK automatically rolls back failed stack updates.")
        log_error("")
        log_error("Manual options:")
        log_error("  1. Check CloudFormation console for details")
        log_error("  2. Redeploy previous version:")
        log_error("     git checkout <previous-commit>")
        log_error("     python deploy.py -e ENV -c CUSTOMER")
        sys.exit(EXIT_CDK_FAILED)


# ============================================================================
# Post-Deployment
# ============================================================================


def run_post_deployment_checks(
    env_vars: dict[str, str],
    *,
    skip: bool = False,
) -> None:
    """Run health checks after deployment."""
    if skip:
        log_info("Skipping post-deployment health checks (--skip-health-check)")
        return

    log_info("Running post-deployment checks...")

    # CUSTOMIZE: Add health check endpoints
    # Example:
    # prefix = env_vars.get("PROJECT_PREFIX", "")
    # env = env_vars.get("ENVIRONMENT", "")
    # function_name = f"{prefix}-{env}-api"
    # try:
    #     run_cmd(
    #         ["aws", "lambda", "invoke",
    #          "--function-name", function_name,
    #          "--payload", '{"path": "/health", "httpMethod": "GET"}',
    #          "/dev/null"],
    #         capture=True,
    #     )
    #     log_info(f"  Lambda warm-up: {function_name} OK")
    # except subprocess.CalledProcessError:
    #     log_warning(f"  Lambda warm-up failed: {function_name}")

    log_info("Post-deployment checks complete")


# ============================================================================
# Cleanup
# ============================================================================


def cleanup() -> None:
    """Clean up temporary files, dangling Docker resources, and CDK artifacts.

    Called on both success and failure via try/finally.
    """
    log_info("Cleaning up...")

    # Remove CDK synthesis output
    cdk_out = Path("cdk.out")
    if cdk_out.exists():
        shutil.rmtree(cdk_out)
        log_verbose("  Removed cdk.out/")

    # Clean dangling Docker images and build cache from CDK asset builds
    if tool_exists("docker"):
        try:
            # Remove dangling images (untagged layers from CDK builds)
            result = run_cmd(
                ["docker", "image", "prune", "-f", "--filter", "until=24h"],
                capture=True,
                check=False,
            )
            pruned = result.stdout.strip()
            if pruned and "Total reclaimed space: 0B" not in pruned:
                log_verbose(f"  Docker cleanup: {pruned.splitlines()[-1]}")

            # Remove stopped CDK asset containers
            run_cmd(
                ["docker", "container", "prune", "-f", "--filter", "until=1h"],
                capture=True,
                check=False,
            )
        except Exception:
            log_verbose("  Docker cleanup skipped (not available)")

    # Remove any temp files created during deployment
    for pattern in ["deploy-output-*.json", "synth-output-*"]:
        for f in Path(".").glob(pattern):
            f.unlink()
            log_verbose(f"  Removed {f}")

    log_info("Cleanup complete")


# ============================================================================
# Performance Analysis
# ============================================================================


def analyze_performance(timer: PhaseTimer) -> None:
    """Analyze deployment performance and suggest optimizations."""
    print()
    print(timer.summary())

    # Save timing data for trend analysis
    timing_dir = Path(".deploy-timing")
    timing_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    timer.save(timing_dir / f"deploy-{timestamp}.json")

    # Check for optimization opportunities
    suggestions: list[str] = []

    for phase in timer.phases:
        name = phase["phase"]
        duration = phase["duration_seconds"]

        if "CDK Deployment" in name and duration > 300:
            suggestions.append(
                f"CDK deploy took {duration:.0f}s. Consider:\n"
                "    - Deploying changed stacks only (-s flag)\n"
                "    - Using CDK hotswap for Lambda-only changes (--hotswap)\n"
                "    - Checking if Docker builds can use layer caching"
            )
        if "Structural Checks" in name and duration > 30:
            suggestions.append(
                f"Pre-deploy checks took {duration:.0f}s. Consider:\n"
                "    - Running Checkov on changed templates only\n"
                "    - Caching cfn-lint results between runs"
            )
        if "Secrets" in name and duration > 15:
            suggestions.append(
                f"Secrets push took {duration:.0f}s. Consider:\n"
                "    - Only updating changed secrets (compare hashes)\n"
                "    - Batching secret updates"
            )

    if suggestions:
        print()
        print("Optimization Suggestions:")
        for s in suggestions:
            print(f"  - {s}")

    # Check historical trends
    timing_files = sorted(timing_dir.glob("deploy-*.json"))
    if len(timing_files) >= 3:
        recent = []
        for tf in timing_files[-5:]:
            try:
                data = json.loads(tf.read_text())
                recent.append(data["total_duration_seconds"])
            except (json.JSONDecodeError, KeyError):
                continue
        if recent:
            avg = sum(recent) / len(recent)
            current = timer.total_duration()
            if current > avg * 1.5:
                log_warning(
                    f"This deploy ({current:.0f}s) was significantly slower "
                    f"than recent average ({avg:.0f}s)"
                )


# ============================================================================
# CLI
# ============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} CDK deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py -e dev -c acme              Deploy all stacks
  python deploy.py -e prod -c acme -s "Lambda*" Deploy matching stacks
  python deploy.py -e dev -c acme --dry-run     Preview without deploying

Config files:
  .env.{env}.{customer}             Secrets (git-ignored)
  config/customers/{customer}.yaml   Customer config (committed)
  cdk.json                            Infrastructure config (committed)

Exit codes:
  0   Success           5   Config invalid
  1   Invalid args      6   Secrets push failed
  2   Missing deps     10   CDK deploy failed
  3   AWS auth failed  11   Health check failed
  4   Account mismatch 20   User cancelled
""",
    )

    parser.add_argument(
        "-e",
        "--environment",
        required=True,
        choices=VALID_ENVIRONMENTS,
        help="Target environment",
    )
    parser.add_argument(
        "-c",
        "--customer",
        required=True,
        help="Customer name for config lookup",
    )
    parser.add_argument(
        "-s",
        "--stack-filter",
        help="Deploy only stacks matching pattern",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without deploying")
    parser.add_argument(
        "--skip-health-check", action="store_true", help="Skip post-deploy verification"
    )
    parser.add_argument("--slack-disabled", action="store_true", help="Deploy without Slack")
    parser.add_argument("--force", action="store_true", help="Continue despite pending operations")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug output")

    return parser.parse_args()


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    args = parse_args()

    global _verbose
    _verbose = args.verbose

    timer = PhaseTimer()
    ci_mode = os.environ.get("CI", "false").lower() == "true"

    print()
    print("=" * 50)
    print(f"  {PROJECT_NAME.upper()} DEPLOYMENT")
    print("=" * 50)

    try:
        # Phase 1: Pre-flight checks
        timer.start_phase("Pre-flight Checks")
        check_dependencies()

        # Phase 2: Load and validate configuration
        timer.start_phase("Configuration")
        env_vars = load_env_file(args.environment, args.customer)
        customer_config = load_customer_config(args.customer)
        validate_config_consistency(
            args.environment,
            args.customer,
            env_vars,
            customer_config,
        )
        log_info(f"  Account:  {env_vars.get('AWS_ACCOUNT_ID', 'N/A')}")
        log_info(f"  Region:   {env_vars.get('AWS_REGION', 'N/A')}")
        log_info(f"  Prefix:   {env_vars.get('PROJECT_PREFIX', 'N/A')}")

        # Phase 3: AWS authentication
        timer.start_phase("AWS Authentication")
        set_aws_profile(env_vars["AWS_ACCOUNT_ID"])
        verify_target_account(env_vars["AWS_ACCOUNT_ID"])

        # Phase 4: Pre-deployment checks
        timer.start_phase("Pre-deployment Checks")
        check_pending_operations(force=args.force)
        ensure_cdk_bootstrap(env_vars["AWS_ACCOUNT_ID"], env_vars["AWS_REGION"])
        confirm_production(args.environment, args.customer, ci=ci_mode)

        # Phase 5: Push secrets
        timer.start_phase("Secrets Management")
        push_secrets(args.environment, args.customer, env_vars, env_vars["AWS_REGION"])

        # Phase 6: CDK synth + structural checks
        timer.start_phase("Pre-deploy Structural Checks")
        log_info("Synthesizing CDK templates...")
        run_cmd(["cdk", "synth", "--all", "--quiet", "--output", "cdk.out"])
        run_pre_deploy_checks("cdk.out")

        # Dry run — show summary and exit
        if args.dry_run:
            timer.end_phase()
            cdk_cmd = build_cdk_command(
                args.environment,
                args.customer,
                env_vars,
                customer_config,
                stack_filter=args.stack_filter,
                slack_enabled=not args.slack_disabled,
            )
            print()
            print("DRY RUN — would execute:")
            print(f"  {' '.join(cdk_cmd)}")
            print()
            print("Use without --dry-run to deploy.")
            sys.exit(EXIT_SUCCESS)

        # Phase 7: CDK deployment
        timer.start_phase("CDK Deployment")
        cdk_cmd = build_cdk_command(
            args.environment,
            args.customer,
            env_vars,
            customer_config,
            stack_filter=args.stack_filter,
            slack_enabled=not args.slack_disabled,
        )
        run_cdk_deploy(cdk_cmd)

        # Phase 8: Post-deployment
        timer.start_phase("Post-deployment Verification")
        run_post_deployment_checks(env_vars, skip=args.skip_health_check)

        timer.end_phase()

        # Deployment summary
        print()
        print("=" * 50)
        print("  DEPLOYMENT COMPLETE")
        print("=" * 50)
        print(f"  Environment: {args.environment}")
        print(f"  Customer:    {args.customer}")
        print(f"  Account:     {env_vars.get('AWS_ACCOUNT_ID', 'N/A')}")
        print(f"  Region:      {env_vars.get('AWS_REGION', 'N/A')}")
        print(f"  Duration:    {timer.total_duration():.1f}s")
        print()

        # Phase 9: Performance analysis
        timer.start_phase("Performance Analysis")
        analyze_performance(timer)
        timer.end_phase()

    except SystemExit:
        raise
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        if _verbose:
            import traceback

            traceback.print_exc()
        sys.exit(EXIT_CDK_FAILED)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
