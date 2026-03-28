# Deployment Best Practices

Safety checks, error handling patterns, and user feedback strategies for production-ready Python deploy scripts.

---

## 1. Safety Checks

### Pre-deployment Confirmation

For production deployments, require explicit confirmation:

```python
def confirm_production_deployment(env: str, customer: str) -> None:
    """Require explicit confirmation for production deployments."""
    if env != "prod":
        return

    print()
    print("=" * 40)
    print("  PRODUCTION DEPLOYMENT CONFIRMATION")
    print("=" * 40)
    print()
    print(f"  Customer: {customer}")
    print(f"  Environment: {env}")
    print()

    # Skip confirmation in CI
    if os.environ.get("CI") == "true":
        print("CI environment detected - skipping confirmation")
        return

    confirmation = input("Type 'deploy' to confirm: ")
    if confirmation != "deploy":
        print("Deployment cancelled")
        sys.exit(20)
```

### Account Mismatch Protection

```python
def verify_target_account(expected_account: str) -> None:
    """Verify authenticated AWS account matches expected account."""
    result = run_cmd(
        ["aws", "sts", "get-caller-identity", "--output", "json"],
        capture=True,
    )
    identity = json.loads(result.stdout)
    actual = identity["Account"]

    if actual != expected_account:
        print()
        print("=" * 40)
        print("  ACCOUNT MISMATCH DETECTED")
        print("=" * 40)
        print()
        print(f"Expected account: {expected_account}")
        print(f"Current account:  {actual}")
        print()
        print("Possible causes:")
        print("  1. Wrong AWS_PROFILE selected")
        print("  2. Customer env file has wrong account ID")
        print("  3. AWS credentials configured for different account")
        sys.exit(4)

    print(f"Target account verified: {expected_account}")
```

### Branch Protection

```python
def verify_deployment_branch(env: str) -> None:
    """Warn if deploying to production from non-main branch."""
    if env != "prod":
        return

    result = run_cmd(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture=True, check=False,
    )
    if result.returncode != 0:
        return  # Not in a git repo

    branch = result.stdout.strip()
    if branch not in ("main", "master"):
        print(f"WARNING: Deploying to production from branch '{branch}'")
        confirm = input("Continue anyway? (y/N): ")
        if confirm.lower() != "y":
            print("Deployment cancelled")
            sys.exit(20)
```

---

## 2. Error Handling

### Exit Codes

Use consistent, meaningful exit codes:

```python
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 1
EXIT_MISSING_DEPS = 2
EXIT_AWS_AUTH_FAILED = 3
EXIT_ACCOUNT_MISMATCH = 4
EXIT_ENV_FILE_MISSING = 5
EXIT_CDK_FAILED = 10
EXIT_HEALTH_CHECK_FAILED = 11
EXIT_USER_CANCELLED = 20
```

### Graceful Failure

Always provide context when failing:

```python
def fail_with_context(code: int, message: str, remediation: str) -> None:
    """Exit with actionable error information."""
    print()
    print("=" * 40)
    print("  DEPLOYMENT FAILED")
    print("=" * 40)
    print()
    print(f"Error: {message}")
    print(f"Code: {code}")
    print()
    print("Remediation:")
    print(remediation)
    print()
    print("For detailed logs, check:")
    print("  - cdk.out/logs/")
    print("  - CloudWatch Logs in AWS Console")
    sys.exit(code)
```

### Retry Logic

```python
import time

def retry_command(
    cmd: list[str],
    max_attempts: int = 3,
    delay: int = 5,
) -> subprocess.CompletedProcess:
    """Retry a command with exponential backoff."""
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result
        if attempt < max_attempts:
            print(f"Failed. Retrying in {delay}s...")
            time.sleep(delay)

    print(f"Command failed after {max_attempts} attempts")
    sys.exit(1)
```

### Cleanup with try/finally

Guaranteed cleanup on any exit:

```python
def main() -> None:
    args = parse_args()
    try:
        run_preflight_checks(args)
        run_cdk_deploy(args)
        run_health_checks(args)
    finally:
        cleanup()
```

---

## 3. User Feedback Patterns

### Logging Helpers

```python
def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")

def log_success(msg: str) -> None:
    print(f"[OK] {msg}")

def log_warning(msg: str) -> None:
    print(f"[WARN] {msg}")

def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)

VERBOSE = False

def log_debug(msg: str) -> None:
    if VERBOSE:
        print(f"[DEBUG] {msg}")
```

### Phase Progress

```python
def show_phase(num: int, name: str, total: int = 6) -> None:
    """Show progress through deployment phases."""
    print()
    print("=" * 40)
    print(f"  Phase {num}/{total}: {name}")
    print("=" * 40)
    print()
```

### Deployment Summary

```python
from datetime import datetime

def show_deployment_summary(
    start_time: float,
    env: str,
    customer: str,
    phase_timings: list[tuple[str, float]],
) -> None:
    """Print deployment summary with timing breakdown."""
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)

    print()
    print("=" * 40)
    print("  DEPLOYMENT COMPLETE")
    print("=" * 40)
    print()
    print(f"Environment: {env}")
    print(f"Customer: {customer}")
    print(f"Duration: {minutes}m {seconds}s")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if phase_timings:
        print()
        print("Phase Timing:")
        for name, duration in phase_timings:
            print(f"  {name}: {duration:.1f}s")
    print()
```

### Dry Run Mode

```python
def handle_dry_run(args: argparse.Namespace, cdk_cmd: list[str]) -> None:
    """Show what would happen without deploying."""
    if not args.dry_run:
        return

    print()
    print("DRY RUN SUMMARY")
    print(f"Would deploy to:")
    print(f"  Environment: {args.environment}")
    print(f"  Customer: {args.customer}")
    print()
    print(f"CDK command: {' '.join(cdk_cmd)}")
    print()
    print("Use without --dry-run to actually deploy")
    sys.exit(0)
```

---

## 4. Recovery Patterns

### Rollback Guidance

```python
def handle_deployment_failure(
    failed_stack: str, env: str, customer: str
) -> None:
    """Provide rollback options on failure."""
    print()
    print("=" * 40)
    print("  DEPLOYMENT FAILED - ROLLBACK OPTIONS")
    print("=" * 40)
    print()
    print(f"Failed stack: {failed_stack}")
    print()
    print("CDK automatically rolls back failed stack updates.")
    print()
    print("Manual options:")
    print("  1. Redeploy previous version:")
    print("     git checkout <previous-commit>")
    print(f"     python deploy.py -e {env} -c {customer}")
    print()
    print("  2. Check CloudFormation events:")
    print(f"     aws cloudformation describe-stack-events \\")
    print(f"       --stack-name {failed_stack}")
```

### Pending Operations Check

```python
def check_pending_operations(region: str) -> None:
    """Warn if CloudFormation stacks are mid-update."""
    result = run_cmd(
        ["aws", "cloudformation", "list-stacks",
         "--stack-status-filter",
         "UPDATE_IN_PROGRESS", "CREATE_IN_PROGRESS", "DELETE_IN_PROGRESS",
         "--query", "StackSummaries[].StackName",
         "--output", "text",
         "--region", region],
        capture=True, check=False,
    )

    pending = result.stdout.strip()
    if pending:
        log_warning("Stacks with pending operations:")
        for stack in pending.split():
            print(f"  - {stack}")
        print()
        print("Wait for operations to complete or cancel in CloudFormation console.")
        sys.exit(1)

    log_success("No pending CloudFormation operations")
```

### Deployment Audit

```python
def record_deployment(status: str, env: str, customer: str, account: str) -> None:
    """Record deployment metadata for audit trail."""
    branch_result = run_cmd(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture=True, check=False,
    )
    commit_result = run_cmd(
        ["git", "rev-parse", "--short", "HEAD"],
        capture=True, check=False,
    )

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "environment": env,
        "customer": customer,
        "account": account,
        "user": os.getenv("USER", "unknown"),
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown",
        "commit": commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown",
    }

    with open("deployments.log", "a") as f:
        f.write(json.dumps(record) + "\n")
```

---

## Summary Checklists

**Safety:**
- [ ] Production confirmation prompt
- [ ] Account mismatch protection
- [ ] Branch protection for production
- [ ] Dry run mode support

**Error Handling:**
- [ ] Consistent exit codes
- [ ] try/finally cleanup
- [ ] Graceful failure with context
- [ ] Retry logic for transient failures

**User Feedback:**
- [ ] Phase progress indicators
- [ ] Deployment summary with timing
- [ ] Actionable error messages
- [ ] Verbose/debug mode

**Recovery:**
- [ ] Rollback guidance on failure
- [ ] Pending operation detection
- [ ] Deployment audit logging

**Related references:**
- `deploy-script-patterns.md` — CLI parsing, AWS profile management, config loading
- `deploy-script-enhancements.md` — Secrets Manager, environment guardrails
