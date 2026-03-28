# Deploy Script Patterns

Essential patterns for building production-ready Python deploy scripts for CDK-based AWS projects. All examples use Python 3.10+ and `subprocess.run()` for shell commands.

---

## 1. CLI Argument Parsing

Use `argparse` for cross-platform argument parsing:

```python
import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy CDK stacks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py -e dev -c acme
  python deploy.py -e prod -c acme -s "Lambda*"
  python deploy.py -e dev -c acme --dry-run
        """,
    )
    parser.add_argument("-e", "--environment", required=True,
                        choices=["dev", "staging", "prod"])
    parser.add_argument("-c", "--customer", required=True)
    parser.add_argument("-s", "--stack-filter", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-health-check", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()
```

`argparse` handles `--help` automatically and validates choices.

---

## 2. Running Shell Commands

Use `subprocess.run()` with explicit error handling:

```python
import subprocess
import sys

def run_cmd(
    cmd: list[str],
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command with consistent error handling."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            print(result.stderr)
        sys.exit(result.returncode)
    return result
```

---

## 3. AWS Profile Management

```python
import json
import os

# CUSTOMIZE: Map account IDs to AWS profile names
ACCOUNT_PROFILES: dict[str, str] = {
    "123456789012": "default",
    "987654321098": "production",
}

def set_aws_profile(target_account: str) -> None:
    """Switch AWS profile based on target account."""
    profile = ACCOUNT_PROFILES.get(target_account)
    if profile:
        os.environ["AWS_PROFILE"] = profile
        print(f"Set AWS_PROFILE={profile} for account {target_account}")

    # Verify credentials match expected account
    result = run_cmd(
        ["aws", "sts", "get-caller-identity", "--output", "json"],
        capture=True,
    )
    identity = json.loads(result.stdout)
    actual = identity["Account"]

    if actual != target_account:
        print(f"Account mismatch: authenticated as {actual}, expected {target_account}")
        sys.exit(1)

    print(f"Authenticated: account={actual}, arn={identity['Arn']}")
```

---

## 4. Three-Layer Config Loading

### Layer 1: Secrets (.env files)

```python
from pathlib import Path

def load_env_file(env: str, customer: str) -> dict[str, str]:
    """Load secrets from .env.{env}.{customer} file."""
    env_path = Path(f".env.{env}.{customer}")
    if not env_path.exists():
        print(f"Missing env file: {env_path}")
        sys.exit(1)

    env_vars: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip().strip("'\"")

    return env_vars
```

### Layer 2: Customer Config (YAML)

```python
import yaml

def load_customer_config(customer: str) -> dict:
    """Load customer settings from config/customers/{customer}.yaml."""
    yaml_path = Path(f"config/customers/{customer}.yaml")
    if not yaml_path.exists():
        return {}  # Optional — not all projects use customer YAML
    return yaml.safe_load(yaml_path.read_text()) or {}
```

### Layer 3: CDK Context (cdk.json)

```python
def load_cdk_context() -> dict:
    """Load context from cdk.json."""
    cdk_path = Path("cdk.json")
    if not cdk_path.exists():
        print("cdk.json not found")
        sys.exit(1)
    return json.loads(cdk_path.read_text()).get("context", {})
```

---

## 5. Pre-flight Checks

```python
import shutil

def check_required_tools() -> None:
    """Verify all required CLI tools are installed."""
    required = ["aws", "cdk", "docker", "python3"]
    missing = [t for t in required if not shutil.which(t)]
    if missing:
        print(f"Missing required tools: {', '.join(missing)}")
        sys.exit(1)
    print("All required tools present")

def check_env_vars(env_vars: dict[str, str]) -> None:
    """Validate required env vars are set and not placeholders."""
    required = ["AWS_ACCOUNT_ID", "AWS_REGION", "AWS_PROFILE"]
    for var in required:
        value = env_vars.get(var, "")
        if not value or value.startswith("<"):
            print(f"Missing or placeholder: {var}={value!r}")
            sys.exit(1)
```

---

## 6. CDK Deploy Command

```python
def build_cdk_command(
    env: str,
    customer: str,
    account_id: str,
    region: str,
    stack_filter: str = "",
) -> list[str]:
    """Build the CDK deploy command with context flags."""
    cmd = [
        "cdk", "deploy",
        "--require-approval", "never",
        "-c", f"environment={env}",
        "-c", f"customer={customer}",
        "-c", f"accountId={account_id}",
        "-c", f"region={region}",
    ]

    if stack_filter:
        cmd.append(stack_filter)
    else:
        cmd.append("--all")

    return cmd
```

---

## 7. CDK Bootstrap Check

```python
def ensure_cdk_bootstrap(account_id: str, region: str) -> None:
    """Check CDK bootstrap status and bootstrap if needed."""
    result = run_cmd(
        ["aws", "cloudformation", "describe-stacks",
         "--stack-name", "CDKToolkit",
         "--region", region,
         "--query", "Stacks[0].StackStatus",
         "--output", "text"],
        capture=True, check=False,
    )

    status = result.stdout.strip() if result.returncode == 0 else "DOES_NOT_EXIST"

    if status in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        print(f"CDK bootstrapped for {account_id}/{region}")
    elif status in ("DOES_NOT_EXIST", "DELETE_COMPLETE"):
        print("CDK not bootstrapped. Running bootstrap...")
        run_cmd(["cdk", "bootstrap", f"aws://{account_id}/{region}"])
    else:
        print(f"CDKToolkit in unexpected state: {status}")
```

---

## 8. Cleanup Pattern

```python
import shutil as shutil_mod

def cleanup() -> None:
    """Remove build artifacts and prune Docker resources."""
    # Remove CDK output
    cdk_out = Path("cdk.out")
    if cdk_out.exists():
        shutil_mod.rmtree(cdk_out)

    # Prune dangling Docker images
    run_cmd(["docker", "image", "prune", "-f"], check=False, capture=True)

    # Prune stopped containers
    run_cmd(["docker", "container", "prune", "-f"], check=False, capture=True)

    print("Cleanup complete")
```

Use `try/finally` to guarantee cleanup runs even on failure:

```python
def main() -> None:
    args = parse_args()
    try:
        run_preflight_checks()
        run_cdk_deploy(args)
        run_health_checks(args)
    finally:
        cleanup()
```

---

## Summary Checklist

- [ ] `argparse` for CLI with choices validation
- [ ] `subprocess.run()` wrapper with error handling
- [ ] AWS profile switching with account verification
- [ ] Three-layer config: .env secrets, customer YAML, cdk.json
- [ ] Pre-flight: tools, credentials, env vars, bootstrap
- [ ] CDK command builder with context flags
- [ ] `try/finally` for guaranteed cleanup
- [ ] Docker pruning after builds

**Related references:**
- `deployment-best-practices.md` — Safety checks, error handling, user feedback
- `deploy-script-enhancements.md` — Secrets Manager integration, environment guardrails
- `pre-deploy-loop-checks.md` — cfn-lint, Checkov, loop detection
