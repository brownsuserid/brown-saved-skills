# Pre-Deploy Loop and Structural Checks

Automated checks to run after `cdk synth` but before `cdk deploy` to catch circular dependencies, structural issues, and potential event-driven loops in synthesized CloudFormation templates.

---

## Overview

These checks catch two categories of problems:

1. **Infrastructure-level cycles:** Circular dependencies between CloudFormation resources (deterministic, always caught)
2. **Structural loop risks:** Event-driven patterns that could cause infinite loops at runtime (heuristic, best-effort)

---

## Tool Installation

```bash
pip install cfn-lint    # CloudFormation linter with circular dependency detection
pip install checkov     # IaC security and structural scanning
```

---

## 1. cfn-lint: Circular Dependency Detection

cfn-lint rule `E3004` specifically detects circular dependencies in the CloudFormation resource graph by traversing `DependsOn`, `Ref`, `Fn::Sub`, and `Fn::GetAtt` references.

### Deploy Script Integration

```python
from pathlib import Path

def run_cfn_lint(synth_dir: str) -> bool:
    """Run cfn-lint on synthesized templates. Returns True if passed."""
    templates = list(Path(synth_dir).glob("*.template.json"))
    if not templates:
        log_warning(f"No CloudFormation templates found in {synth_dir}")
        return True

    log_info("Running cfn-lint on synthesized templates...")

    has_errors = False
    for template in templates:
        stack_name = template.stem.replace(".template", "")
        log_info(f"  Checking: {stack_name}")

        result = run_cmd(
            ["cfn-lint", str(template)],
            capture=True, check=False,
        )

        output = result.stdout + result.stderr

        # Check for circular dependencies (E3004) - blocking
        circular_lines = [l for l in output.splitlines() if "E3004" in l]
        if circular_lines:
            log_error(f"CIRCULAR DEPENDENCY in {stack_name}:")
            for line in circular_lines:
                print(f"  {line}")
            has_errors = True

        # Other errors - informational
        error_lines = [
            l for l in output.splitlines()
            if l.startswith("E") and "E3004" not in l
        ]
        if error_lines:
            log_warning(f"cfn-lint errors in {stack_name}:")
            for line in error_lines[:10]:
                print(f"  {line}")

    if has_errors:
        log_error("Fix circular dependencies before deploying")
        return False

    log_success("cfn-lint passed: no circular dependencies")
    return True
```

### Configuration File

Create `.cfnlintrc.yaml` in the project root:

```yaml
templates:
  - cdk.out/*.template.json

# CDK-generated templates trigger some false positives
ignore_checks:
  - W2001  # Unused parameters (CDK generates these)
  - W3010  # Hardcoded AZ (CDK handles this)

configure_rules:
  E3012:
    strict: false  # Relax for CDK token values
```

---

## 2. Checkov: Structural and Security Scanning

Checkov uses graph-based analysis on CloudFormation templates. While its primary focus is security misconfigurations, it catches structural issues that can behave like logical loops (retry storms, miswired triggers).

### Deploy Script Integration

```python
def run_checkov(synth_dir: str, severity: str = "HIGH,CRITICAL") -> None:
    """Run Checkov on synthesized templates (non-blocking)."""
    log_info("Running Checkov on synthesized templates...")

    result = run_cmd(
        ["checkov", "-d", synth_dir,
         "--framework", "cloudformation",
         "--check-severity", severity,
         "--compact", "--quiet"],
        capture=True, check=False,
    )

    output = result.stdout + result.stderr
    failed_lines = [l for l in output.splitlines() if "FAILED" in l]

    if failed_lines:
        log_warning(f"Checkov found {len(failed_lines)} issue(s) at {severity}:")
        for line in failed_lines[:20]:
            print(f"  {line}")
    else:
        log_success(f"Checkov passed: no {severity} issues")
```

### Suppressions

Create `.checkov.yaml` for project-specific suppressions:

```yaml
skip-check:
  - CKV_AWS_45   # Lambda VPC - not required for all use cases
  - CKV_AWS_117  # Lambda VPC - same as above

skip-path:
  - cdk.out/assembly-*  # Skip CDK pipeline artifacts
```

---

## 3. Event-Driven Loop Heuristic Checks

These checks analyze synthesized templates for patterns known to cause runtime loops.

### Deploy Script Integration

```python
def check_event_driven_loops(synth_dir: str) -> int:
    """Check for potential event-driven loop patterns. Returns warning count."""
    log_info("Checking for potential event-driven loop patterns...")

    warnings = 0

    for template_path in Path(synth_dir).glob("*.template.json"):
        stack_name = template_path.stem.replace(".template", "")
        template = json.loads(template_path.read_text())
        resources = template.get("Resources", {})

        # Check 1: DynamoDB Stream -> Lambda writing to same table
        stream_tables = [
            name for name, res in resources.items()
            if res.get("Type") == "AWS::DynamoDB::Table"
            and res.get("Properties", {}).get("StreamSpecification")
        ]
        if stream_tables:
            log_warning(f"[{stack_name}] DynamoDB tables with streams: {', '.join(stream_tables)}")
            log_warning("  Verify: Lambda handlers do NOT write back to these tables")
            warnings += 1

        # Check 2: S3 bucket notifications
        s3_notifications = [
            name for name, res in resources.items()
            if res.get("Type") == "Custom::S3BucketNotifications"
        ]
        if s3_notifications:
            log_warning(f"[{stack_name}] S3 bucket notifications detected")
            log_warning("  Verify: Lambda does NOT write to the SAME bucket that triggers it")
            warnings += 1

        # Check 3: Unbounded Lambda concurrency with event sources
        unbounded_lambdas = [
            name for name, res in resources.items()
            if res.get("Type") == "AWS::Lambda::Function"
            and not res.get("Properties", {}).get("ReservedConcurrentExecutions")
        ]
        event_sources = [
            name for name, res in resources.items()
            if res.get("Type") == "AWS::Lambda::EventSourceMapping"
        ]
        if unbounded_lambdas and event_sources:
            log_info(f"[{stack_name}] Lambdas with event sources but no concurrency limit")
            log_info("  Consider adding ReservedConcurrentExecutions")

        # Check 4: EventBridge rules
        eb_rules = [
            name for name, res in resources.items()
            if res.get("Type") == "AWS::Events::Rule"
        ]
        if eb_rules:
            log_info(f"[{stack_name}] Found {len(eb_rules)} EventBridge rule(s)")
            log_info("  Verify: Target Lambdas clear the trigger condition on all code paths")

    if warnings > 0:
        log_warning(f"Found {warnings} potential loop risk(s) - review before deploying")
    else:
        log_success("No obvious event-driven loop patterns detected")

    return warnings
```

---

## 4. Step Function Validation

```python
def check_step_functions(synth_dir: str) -> int:
    """Validate Step Function definitions. Returns warning count."""
    log_info("Validating Step Function definitions...")

    warnings = 0

    for template_path in Path(synth_dir).glob("*.template.json"):
        template = json.loads(template_path.read_text())
        resources = template.get("Resources", {})
        stack_name = template_path.stem.replace(".template", "")

        sfn_resources = {
            name: res for name, res in resources.items()
            if res.get("Type") == "AWS::StepFunctions::StateMachine"
        }

        for name, res in sfn_resources.items():
            definition = res.get("Properties", {}).get("DefinitionString", "")
            if isinstance(definition, dict):
                definition = json.dumps(definition)

            # Check for Map states without MaxConcurrency
            map_count = definition.count('"Type": "Map"')
            max_concurrency_count = definition.count('"MaxConcurrency"')
            if map_count > 0 and max_concurrency_count < map_count:
                log_warning(f"[{stack_name}] Map state(s) without MaxConcurrency")
                log_warning("  Unbounded Map states can cause Lambda throttling storms")
                warnings += 1

            # Check for Retry without Catch
            retry_count = definition.count('"Retry"')
            catch_count = definition.count('"Catch"')
            if retry_count > catch_count:
                log_warning(
                    f"[{stack_name}] {retry_count} Retry config(s) "
                    f"but only {catch_count} Catch config(s)"
                )
                warnings += 1

    if warnings > 0:
        log_warning(f"Found {warnings} Step Function issue(s)")
    else:
        log_success("Step Function definitions look good")

    return warnings
```

---

## 5. Combined Pre-Deploy Check Function

```python
import shutil

def run_pre_deploy_checks(synth_dir: str = "cdk.out") -> None:
    """Run all pre-deploy structural checks."""
    print()
    print("=" * 40)
    print("  PRE-DEPLOY STRUCTURAL CHECKS")
    print("=" * 40)
    print()

    failed = False

    # 1. cfn-lint (blocking)
    if shutil.which("cfn-lint"):
        if not run_cfn_lint(synth_dir):
            failed = True
    else:
        log_warning("cfn-lint not installed - skipping circular dependency check")
        log_warning("Install with: pip install cfn-lint")

    # 2. Checkov (non-blocking)
    if shutil.which("checkov"):
        run_checkov(synth_dir)
    else:
        log_info("Checkov not installed - skipping security scan")

    # 3. Event-driven loop heuristics (non-blocking)
    check_event_driven_loops(synth_dir)
    check_step_functions(synth_dir)

    print()

    if failed:
        log_error("Pre-deploy checks FAILED - fix blocking issues before deploying")
        sys.exit(EXIT_CDK_FAILED)

    log_success("Pre-deploy checks complete")
```

---

## Checklist

- [ ] cfn-lint runs on all synthesized templates
- [ ] Circular dependency check (E3004) blocks deployment
- [ ] Checkov runs at HIGH/CRITICAL severity
- [ ] DynamoDB stream and S3 notification loop heuristics
- [ ] Step Function Map states have MaxConcurrency
- [ ] Step Function Retry configs paired with Catch
- [ ] Tools fail gracefully when not installed (warning, not error)

## Limitations

These checks cannot catch:
- Application-level logic loops (halting problem)
- Event chains that span multiple stacks/accounts
- Loops caused by external systems (third-party webhooks)
- Race conditions in concurrent Lambda executions

For deeper analysis, use the `infra-detecting-loops` skill which performs manual code-level analysis of trigger chains.
