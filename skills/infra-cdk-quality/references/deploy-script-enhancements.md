# Deploy Script Enhancements

Additions to the `infra-cdk-quality` skill based on lessons learned.

---

## Environment Guardrails

Prevent accidental cross-environment deployments with template validation.

### Pattern Counting Guardrail

Before deploying, synthesize the CDK template and verify environment patterns appear:

```python
import re
from pathlib import Path

def validate_environment_guardrails(synth_dir: str, env: str) -> None:
    """Verify synthesized templates contain correct environment patterns."""
    templates = list(Path(synth_dir).glob("*.template.json"))
    if not templates:
        log_warning(f"No templates found in {synth_dir}")
        return

    template_text = templates[0].read_text()

    # Count expected environment patterns (should be > 5 for typical stack)
    env_pattern = f"-{env}-"
    env_count = template_text.count(env_pattern)
    if env_count < 5:
        log_error(f"Found only {env_count} '{env_pattern}' patterns")
        log_error("Resources may not be properly suffixed for this environment")
        sys.exit(EXIT_CDK_FAILED)

    log_success(f"Naming guardrail passed: {env_count} '{env_pattern}' patterns")

    # Safety: Verify NO wrong-environment patterns
    wrong_envs = {"dev", "staging", "prod"} - {env}
    for wrong in wrong_envs:
        wrong_pattern = f"-{wrong}-"
        wrong_count = template_text.count(wrong_pattern)
        if wrong_count > 0:
            log_error(
                f"SAFETY GUARDRAIL FAILED: Found {wrong_count} "
                f"'{wrong_pattern}' patterns in {env} template!"
            )
            sys.exit(EXIT_CDK_FAILED)

    log_success("Safety guardrail passed: no cross-environment resources")
```

### Why This Matters

- Prevents deploying to wrong account/environment
- Catches misconfigured CDK context
- Provides early failure before CloudFormation starts

---

## Post-Deployment Lambda Configuration

When CDK outputs aren't reliable, update Lambda env vars directly.

```python
def configure_lambda_env(
    function_name: str,
    env_vars: dict[str, str],
    region: str,
) -> None:
    """Update Lambda function environment variables."""
    vars_str = ",".join(f"{k}={v}" for k, v in env_vars.items())

    result = run_cmd(
        ["aws", "lambda", "update-function-configuration",
         "--function-name", function_name,
         "--environment", f"Variables={{{vars_str}}}",
         "--region", region],
        capture=True, check=False,
    )

    if result.returncode == 0:
        log_success(f"Lambda {function_name} configured")
    else:
        log_warning(f"Lambda update failed for {function_name}")
        print(f"  Run manually:")
        print(f"    aws lambda update-function-configuration \\")
        print(f"      --function-name {function_name} \\")
        print(f"      --environment 'Variables={{{vars_str}}}'")
```

---

## Secrets Manager Integration

Push credentials to Secrets Manager before CDK deploy.

### Create or Update Pattern

```python
def push_secret(
    secret_name: str,
    secret_data: dict[str, str],
    region: str,
) -> None:
    """Create or update a secret in Secrets Manager."""
    secret_json = json.dumps(secret_data)

    # Check if secret exists
    check = run_cmd(
        ["aws", "secretsmanager", "describe-secret",
         "--secret-id", secret_name,
         "--region", region],
        capture=True, check=False,
    )

    if check.returncode == 0:
        # Update existing
        result = run_cmd(
            ["aws", "secretsmanager", "put-secret-value",
             "--secret-id", secret_name,
             "--secret-string", secret_json,
             "--region", region],
            capture=True, check=False,
        )
        if result.returncode == 0:
            log_success(f"Updated secret: {secret_name}")
        else:
            log_error(f"Failed to update secret: {secret_name}")
            sys.exit(1)
    else:
        log_warning(f"Secret {secret_name} not found - should be created by CDK")
```

### Placeholder Detection

```python
def check_for_placeholders(env_vars: dict[str, str]) -> list[str]:
    """Find env vars with placeholder values."""
    placeholders = []
    for key, value in env_vars.items():
        if not value or value.startswith("<") or "PLACEHOLDER" in value.upper():
            placeholders.append(key)
    return placeholders
```

---

## Enhanced Deployment Summary

Show actionable next steps after deployment.

```python
def show_next_steps(
    env: str,
    customer: str,
    outputs_file: str | None = None,
) -> None:
    """Display actionable next steps after deployment."""
    oauth_url = None

    if outputs_file and Path(outputs_file).exists():
        outputs = json.loads(Path(outputs_file).read_text())
        # Search for OAuth URL in outputs
        for stack_outputs in outputs.values():
            if isinstance(stack_outputs, dict):
                oauth_url = stack_outputs.get("OAuthStartUrl")
                if oauth_url:
                    break

    print()
    print("=" * 40)
    print("  NEXT STEPS")
    print("=" * 40)
    print()

    if oauth_url:
        print(f"  1. Visit OAuth URL: {oauth_url}")
        print("  2. Authenticate with your account")
        print("  3. Credentials auto-save to Secrets Manager")
    else:
        print("  1. Verify deployment in AWS Console")
        print(f"  2. Test: aws lambda list-functions --region <region>")

    print()
```

---

## Checklist Additions

**Environment Guardrails:**
- [ ] Pattern counting validates environment suffix
- [ ] Cross-environment safety check (no -prod- in dev)
- [ ] Synthesis validation before deploy

**Post-Deployment:**
- [ ] Lambda env var update with fallback
- [ ] Secrets Manager credential push
- [ ] Placeholder detection in env vars
- [ ] Manual instructions when automation fails

**Error Handling:**
- [ ] JSON parsing with fallbacks
- [ ] Graceful degradation with warnings
- [ ] Clear manual remediation steps
