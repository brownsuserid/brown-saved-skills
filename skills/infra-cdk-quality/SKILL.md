---
name: infra-cdk-quality
description: Use this skill for ANY task involving AWS CDK infrastructure code or CDK deployment scripts. TRIGGER when the user mentions: cdk deploy, cdk/, stacks, CloudFormation exports, cross-stack references, cdk.out, CDK Stages, deploy.sh with cdk commands, deployment deadlocks between stacks, deploy script, deployment automation, "how do I deploy this", set up deployment, CI/CD for CDK, or adding new environments/customers to a deployment pipeline. Covers: pre-deploy and pre-PR CDK review, fixing "Export cannot be updated" errors, resolving stack dependency deadlocks, IAM/security/encryption audits on CDK resources, setting up cdk-nag/Checkov/cfn-lint, creating and evaluating deploy scripts for CDK projects, multi-customer CDK deployments, and multi-environment deployment automation. If the user has a cdk/ directory or describes multiple stacks sharing resources like DynamoDB tables — this is the right skill. Do NOT use for general code review, AWS cost/billing, Terraform, or loop detection.
---

# CDK Quality & Deployment Skill

This skill provides systematic evaluation of AWS CDK infrastructure code and production-ready deployment automation. It covers cross-stack dependency analysis, security scanning, best practices validation, and creating/evaluating deploy scripts.

This skill operates in two modes:

- **CDK Quality Review** (Phases 0-6, 8-9) — Analyze CDK code for dependency issues, security, and best practices
- **Deploy Script Creation** (Phase 7) — Create or evaluate production-ready Python deploy scripts

Both modes can be used together or independently.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 0: Understand Project Setup

Before running commands, detect the project type:

| Indicator Files | Language | CDK Command |
|-----------------|----------|-------------|
| `package.json`, `tsconfig.json` | TypeScript | `npx cdk` / `yarn cdk` |
| `app.py`, `pyproject.toml` | Python | `uv run cdk` / `poetry run cdk` |

```bash
# Detect package manager
ls package-lock.json yarn.lock uv.lock poetry.lock 2>/dev/null

# Check if cdk-nag already configured
grep -r "cdk-nag\|cdk_nag" . --include="*.ts" --include="*.py" 2>/dev/null
```

---

## ⚠️ CRITICAL: Parameter Store Synthesis-Time Misconception

**This is the #1 mistake when fixing cross-stack dependencies.**

**DO NOT** use SSM Parameter Store lookups at CDK synthesis time to avoid exports:

```python
# ❌ WRONG - This still creates cross-stack dependencies!
param = ssm.StringParameter.from_string_parameter_name(
    self, "Param", "/my/param"
)
value = param.string_value  # This is a TOKEN, not a string!
```

```typescript
// ❌ WRONG - Same problem in TypeScript
const param = ssm.StringParameter.fromStringParameterName(
    this, 'Param', '/my/param'
);
const value = param.stringValue;  // This is a TOKEN, not a string!
```

**Why this fails:**
1. `.string_value` / `.stringValue` returns a CloudFormation Token
2. Tokens resolve at **deploy time**, not synthesis time
3. Using this Token creates the exact cross-stack export you're trying to avoid

**Correct approaches:** See Phase 5 "Dependency Resolution Hierarchy"

---

## Phase 1: Analyze Stack Architecture

Map the CDK application structure and identify potential dependency issues.

### Identify All Stacks

```bash
# List all stacks in the CDK app
cd [CDK_PROJECT_ROOT]
npx cdk list
```

### Review Stack Structure

**Examine the CDK app entry point** (usually `bin/*.ts` or `app.py`):
- How many stacks are defined?
- Are stacks passing resources to each other?
- Is there explicit `addDependency()` usage?
- **Does the app use CDK Stages?** Stages group stacks into deployment units and create nested `assembly-*` directories in `cdk.out/`. If Stages are used, each Stage produces its own set of templates under `cdk.out/assembly-<StageName>/`.

**Check for proper layering:**
```
Foundation (VPC, networking) → Stateful (databases, S3) → Stateless (Lambda, API) → Presentation
```

### Identify Cross-Stack References

**Red flags to look for:**
- L2/L3 constructs passed between stack constructors
- Resources created in one stack, used in another
- `stack.exportValue()` calls
- Properties like `bucket`, `table`, `function` passed via props

**Document findings:**
- Stack names and their purposes
- Resources shared between stacks
- Direction of dependencies (A → B)

---

## Phase 2: Detect Cross-Stack Dependencies

Synthesize templates and scan for problematic exports.

### Quick Scan with Script

Use the provided script for automated detection:

```bash
# Run the dependency check script
./scripts/check-cdk-dependencies.sh

# Or with a specific CDK command prefix (for Python/uv projects)
CDK_CMD="uv run cdk" ./scripts/check-cdk-dependencies.sh
```

### Manual Detection

**Synthesize CloudFormation Templates:**

```bash
cd [CDK_PROJECT_ROOT]
# Use appropriate command for your project (see Phase 0)
npx cdk synth --all --quiet      # TypeScript/npm
uv run cdk synth --all --quiet   # Python/uv
```

**Scan for Exports (including CDK Stages):**

```bash
# List all assemblies (CDK Stages create nested assemblies)
ls cdk.out/

# Check for Exports in all templates (including nested assemblies)
grep -r '"Export"' cdk.out/*.template.json cdk.out/assembly-*/*.template.json 2>/dev/null

# Check for Fn::ImportValue (the consuming side)
grep -r 'Fn::ImportValue' cdk.out/*.template.json cdk.out/assembly-*/*.template.json 2>/dev/null
```

### Check Existing AWS Exports

```bash
# List all CloudFormation exports in the account
aws cloudformation list-exports --query 'Exports[*].[Name,ExportingStackId]' --output table

# List imports for a specific export
aws cloudformation list-imports --export-name [EXPORT_NAME]
```

### Identify Dependency Issues

**Critical issues:**
- Circular dependencies (Stack A → B → A)
- Long dependency chains (A → B → C → D)
- Exports that prevent stack updates

**Use the dependency test:** Can you update each stack independently? If not, you have a problem.

**Complete detection guide:** See `references/cross-stack-dependencies.md`

---

## Phase 3: Run Security & Compliance Scanning

Execute automated scanning tools to identify security and compliance issues.

### Run cdk-nag

```typescript
// Add to your CDK app (TypeScript)
import { Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';

Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
```

```python
# Add to your CDK app (Python)
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks

Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
```

```bash
# Run synthesis to trigger cdk-nag
npx cdk synth --all 2>&1 | tee cdk-nag-report.txt
```

### Run Checkov on Synthesized Templates

```bash
# Scan all synthesized CloudFormation templates
checkov -d cdk.out/ --framework cloudformation --output cli

# For JSON output
checkov -d cdk.out/ --framework cloudformation --output json > checkov-report.json
```

### Run cfn-lint

```bash
# Lint all synthesized templates
cfn-lint cdk.out/*.template.json
```

### Categorize Findings

**Critical (Must Fix):**
- Security vulnerabilities (open security groups, unencrypted storage)
- IAM policy issues (overly permissive, wildcard resources)
- Compliance violations (HIPAA, PCI DSS if applicable)

**Important (Should Fix):**
- Best practice violations
- Resource configuration issues
- Missing tags or logging

**Suggestions:**
- Optimization opportunities
- Code style improvements

**Complete scanning guide:** See `references/cdk-security-scanning.md`

---

## Phase 4: Validate CDK Best Practices

Check code against AWS CDK best practices.

### Stack Organization

**Check:**
- [ ] Constructs used for logical units, stacks for deployment
- [ ] Stateful resources (DBs, S3) in separate stacks with termination protection
- [ ] Stack size reasonable (< 500 resources)
- [ ] No hardcoded resource names (use generated names)

### Cross-Stack Reference Patterns

**Verify safe patterns are used:**
- L1 (Cfn) constructs with plain strings for cross-stack refs
- SSM Parameter Store for sharing resource IDs
- `fromXxxArn()` or `fromXxxAttributes()` with string ARNs
- Config files storing resource IDs after initial creation

**Flag dangerous patterns:**
- L2/L3 constructs passed between stacks
- Direct resource references across stacks
- Implicit exports from CDK

### IAM Best Practices

**Check:**
- [ ] Using grant methods (`bucket.grantRead(lambda)`) vs explicit policies
- [ ] No wildcard resources in IAM policies
- [ ] Least privilege principle applied
- [ ] Service roles properly scoped

### Logical ID Stability

**For stateful resources, verify:**
- Construct IDs haven't changed
- Resources haven't moved in construct tree
- Unit tests exist to assert logical ID stability

**Complete best practices guide:** See `references/cdk-best-practices.md`

---

## Phase 5: Provide Remediation Guidance

Generate prioritized remediation plan with specific fixes.

### Prioritize Issues

**Order by impact:**
1. Cross-stack dependencies causing deployment blocks
2. Security vulnerabilities
3. Compliance violations
4. Best practice violations
5. Optimization suggestions

### Dependency Resolution Hierarchy

**Choose the simplest approach that works. Prefer free options over paid AWS services.**

| Priority | Approach | Cost | When to Use |
|----------|----------|------|-------------|
| 1st | Stack constructor props with plain strings | Free | Known stable values (ARNs, names) |
| 2nd | Config files with resource IDs | Free | Values known after first deploy |
| 3rd | SSM Parameter Store (runtime lookup) | Free* | Dynamic non-sensitive values |
| 4th | Secrets Manager (runtime lookup) | $0.40/secret/mo | Sensitive values (API keys, creds) |

*SSM Parameter Store Standard tier is free for up to 10,000 parameters.

### Pattern 1: Stack Props with Plain Strings (Preferred)

```python
# config.py - Plain strings, no Tokens
RESOURCES = {
    "prod": {
        "vpc_id": "vpc-abc123",
        "bucket_name": "myapp-prod-data-xyz789",
        "table_arn": "arn:aws:dynamodb:us-east-1:123456789:table/MyTable",
    }
}

# stack.py - Import using plain strings
from config import RESOURCES
bucket = s3.Bucket.from_bucket_name(self, "Bucket", RESOURCES["prod"]["bucket_name"])
```

### Pattern 2: Secrets Manager for Sensitive Values

```python
# Stack A: Store sensitive config in Secrets Manager
secret_name = f"myapp/{environment}/api-credentials"
secret = secretsmanager.Secret(self, "ApiCreds", secret_name=secret_name)

# Stack B: Import using plain string path - NO export created
secret = secretsmanager.Secret.from_secret_name_v2(
    self, "ImportedSecret",
    secret_name=f"myapp/{environment}/api-credentials"  # Plain string!
)
secret.grant_read(my_lambda)
# Lambda reads actual secret values at RUNTIME via SDK
```

### Pattern 3: SSM Parameter Store for Non-Sensitive Values

```python
# Stack A: Write parameter (creates the parameter, not an export)
ssm.StringParameter(self, "ApiUrlParam",
    parameter_name=f"/myapp/{environment}/api-url",
    string_value=api.url,
)

# Stack B: Lambda reads at RUNTIME (not synthesis!)
# Pass parameter NAME as env var, read VALUE in Lambda code
handler = lambda_.Function(self, "Handler",
    environment={"API_URL_PARAM": f"/myapp/{environment}/api-url"}
)
# In Lambda: ssm_client.get_parameter(Name=os.environ['API_URL_PARAM'])
```

### When to Use Secrets Manager vs Parameter Store

| Use Case | Storage | Why |
|----------|---------|-----|
| API keys, tokens | Secrets Manager | Automatic rotation, encryption |
| Database passwords | Secrets Manager | Audit logging, fine-grained access |
| Resource IDs, ARNs | Config file | Free, version controlled |
| Feature flags | Parameter Store | Free, simple key-value |
| Service URLs | Parameter Store | Free, can change without redeploy |

### Migration Strategy

1. **Fix one stack at a time** - incremental is safer
2. **Delete old routes before deploying L1 replacements** (API Gateway)
3. **Verify with AWS CLI** after each change
4. **Test stack updates independently**

**Complete patterns guide:** See `references/cross-stack-dependencies.md`
**Use template:** See `templates/cdk-quality-report.md`

---

## Phase 6: Verify Fixes

Confirm all issues are resolved and no new problems introduced.

### Re-run Synthesis

```bash
# Use appropriate command for your project (see Phase 0)
npx cdk synth --all --quiet      # TypeScript/npm
uv run cdk synth --all --quiet   # Python/uv
```

### Verify No New Exports (Including CDK Stages)

CDK with Stages creates nested assemblies. Check all of them:

```bash
# List all assemblies
ls cdk.out/

# Check for Exports in ALL templates (including nested assemblies)
grep -r '"Export"' cdk.out/*.template.json cdk.out/assembly-*/*.template.json 2>/dev/null

# Check for Fn::ImportValue
grep -r 'Fn::ImportValue' cdk.out/*.template.json cdk.out/assembly-*/*.template.json 2>/dev/null

# Or use the script
./scripts/check-cdk-dependencies.sh
```

### Test Independent Deployment

```bash
# Each stack should be deployable independently
npx cdk diff [STACK_NAME]
npx cdk deploy [STACK_NAME] --require-approval never

# For Python projects
uv run cdk diff [STACK_NAME]
uv run cdk deploy [STACK_NAME] --require-approval never
```

### Final Verification with AWS CLI

```bash
# Confirm no new exports in AWS
aws cloudformation list-exports --query 'Exports[*].Name' --output text

# Check specific stack for exports
aws cloudformation describe-stacks --stack-name [STACK_NAME] --query 'Stacks[0].Outputs[?ExportName]'
```

---

## Phase 7: Deploy Script Creation & Validation

This phase covers both creating new deploy scripts and validating existing ones. Python is the deploy script language because it runs identically on macOS, Linux, Windows, and WSL — no need for separate bash and PowerShell scripts.

### Getting Started (New Script)

Copy and customize the template:

```bash
cp templates/deploy-script-template.py deploy.py
```

Search for `CUSTOMIZE:` comments in the template and update for your project.

### Config Separation

Deploy scripts use a three-layer config model:

| Layer | Location | Contains | Git |
|-------|----------|----------|-----|
| Secrets | `.env.{env}.{customer}` | API keys, tokens, credentials | Ignored |
| Customer config | `config/customers/{customer}.yaml` | Feature flags, settings, domain | Committed |
| Infrastructure | `cdk.json` | CDK context, stack settings | Committed |

**Critical**: `.env` files contain secrets and MUST be git-ignored. Only `.env.TEMPLATE` gets committed.

### Deploy Script Phases

#### 7a. Analyze Project Requirements

Before writing or customizing, understand what the project needs:
- **CDK structure**: Find `cdk.json`, `app.py`, or `bin/*.ts` entry points. Run `cdk list` to see existing stacks.
- **Deployment dimensions**: How many environments (dev/staging/prod)? Multi-customer with dedicated AWS accounts? Single or multi-region?
- **Dependencies**: What tools are required (aws, cdk, docker, python)?
- **Integrations**: Slack notifications, monitoring, post-deploy webhooks?

#### 7b. Define AWS Account Configuration

Map AWS accounts to profiles so the script can automatically switch credentials. Each customer+environment combination gets an `.env` file for secrets and a YAML file for config:

```
.env.TEMPLATE                      # Placeholder values (committed)
.env.dev.customer-a                # Secrets (git-ignored)
.env.prod.customer-a               # Secrets (git-ignored)
config/customers/customer-a.yaml   # Feature flags, settings (committed)
```

See `references/deploy-script-patterns.md` for profile switching and env file loading patterns.

#### 7c. Design CLI Interface

The template uses `argparse` for cross-platform argument parsing:

| Flag | Short | Required | Purpose |
|------|-------|----------|---------|
| `--environment` | `-e` | Yes | Target environment (dev/staging/prod) |
| `--customer` | `-c` | Yes | Customer name for config lookup |
| `--stack-filter` | `-s` | No | Deploy only matching stacks |
| `--dry-run` | | No | Preview without deploying |
| `--skip-health-check` | | No | Skip post-deploy verification |
| `--verbose` | `-v` | No | Debug output |

#### 7d. Implement Pre-flight Checks

Pre-flight checks catch errors before any infrastructure changes happen:
1. **Required tools** — verify aws, cdk, docker, python are installed
2. **AWS credentials** — `aws sts get-caller-identity` must succeed
3. **Account verification** — authenticated account must match expected account from .env
4. **Config validation** — cross-validate .env, customer YAML, and cdk.json
5. **CDK bootstrap** — CDKToolkit stack exists or auto-bootstrap
6. **Pending operations** — warn if CloudFormation stacks are mid-update

See `references/deployment-best-practices.md` for safety patterns.

#### 7e. Pre-Deploy Structural Checks

After `cdk synth` but before `cdk deploy`, run automated scanning:
- **cfn-lint** (blocking) — catches circular dependencies (E3004) and structural errors
- **Checkov** (non-blocking) — security scanning at HIGH/CRITICAL severity
- **Event-driven loop heuristics** (non-blocking) — detects DynamoDB stream loops, S3 self-triggering

See `references/pre-deploy-loop-checks.md` for implementation details.

#### 7f. Push Secrets to AWS Secrets Manager

Before CDK deploy, push credentials from the `.env` file to Secrets Manager. Use consistent naming: `{project}/{customer}/{purpose}`.

See `references/deploy-script-enhancements.md` for the full secrets integration pattern.

#### 7g. Execute CDK Deployment

Build the CDK command with context flags and execute using `subprocess.run()`:
- Clean stale `cdk.out/` before deploying
- Pass environment, customer, accountId, region, and integration toggles as CDK context
- Use `--require-approval never` for non-interactive deployment
- Apply stack filter if provided, otherwise deploy `--all`
- Track per-phase timing with `PhaseTimer` for performance analysis

#### 7h. Post-Deployment Verification and Cleanup

After successful deployment:
1. **Health check warm-up** — invoke key Lambda functions to avoid cold starts
2. **DNS/API verification** — check health endpoints if domain is configured
3. **Performance analysis** — print phase timing summary, flag slow phases
4. **Cleanup** — remove `cdk.out/`, prune dangling Docker images, remove temp files (in `try/finally`)

### Validating an Existing Deploy Script

```bash
# Check if deploy script exists
ls deploy.sh deploy.py cdk/deploy.sh cdk/deploy.py scripts/deploy.sh scripts/deploy.py 2>/dev/null
```

**Verify the script includes:**
- [ ] **Argument parsing** — Accepts `-e/--environment` and `-c/--customer` flags
- [ ] **Help message** — `--help` with usage examples
- [ ] **Input validation** — Rejects invalid environments, requires customer for multi-account
- [ ] **AWS profile switching** — Maps account IDs to named profiles, verifies with `sts get-caller-identity`
- [ ] **Environment file loading** — Sources `.env.<environment>.<customer>` with `CDK_DEFAULT_ACCOUNT`
- [ ] **CDK Stage name computation** — Matches the `app.py` / `bin/*.ts` Stage naming convention
- [ ] **Pre-deployment checks** — Config validation, CDK bootstrap check, secrets setup
- [ ] **Post-deployment tasks** — Lambda warm-up (health endpoint curl), Docker cleanup, deployment summary
- [ ] **Error handling** — `set -euo pipefail` (bash) or `try/finally` (Python), helpful error messages

**Red flags:**
- Script just runs `cdk deploy --all` with no arguments
- No AWS profile management (assumes default credentials)
- No post-deployment verification

### Deploy Script Quality Checklist

- [ ] Uses `argparse` for CLI with all standard flags
- [ ] `try/finally` pattern for guaranteed cleanup
- [ ] Help output with usage, flags, examples, and exit codes
- [ ] Three-layer config loaded: `.env` secrets, customer YAML, `cdk.json`
- [ ] Config cross-validation via `validate_config.py`
- [ ] `.env` files git-ignored; `.env.TEMPLATE` committed
- [ ] AWS credentials verified before any deployment
- [ ] Account mismatch protection (expected vs authenticated)
- [ ] Secrets pushed to Secrets Manager before CDK deploy
- [ ] CDK bootstrap checked/executed if needed
- [ ] Pre-deploy structural checks (cfn-lint, Checkov)
- [ ] Dry run mode shows what would happen
- [ ] Production deployment requires confirmation
- [ ] Post-deployment health checks
- [ ] PhaseTimer tracking with performance trend analysis
- [ ] Docker cleanup (dangling images, stopped containers)
- [ ] Passes ruff check and mypy

---

## Phase 8: Post-Deployment Verification (Optional)

After successful CDK deployment, verify Lambda configs, Secrets Manager access, Step Function definitions, and CloudWatch for errors.

```bash
# Verify Lambda configurations
aws lambda get-function-configuration --function-name [FUNCTION_NAME] \
  --query '{Runtime:Runtime,Timeout:Timeout,MemorySize:MemorySize,Environment:Environment.Variables}'

# Verify Secrets Manager access
aws secretsmanager get-secret-value --secret-id [SECRET_NAME] --query 'Name'

# Check CloudWatch for recent errors
aws logs filter-log-events --log-group-name /aws/lambda/[FUNCTION_NAME] \
  --filter-pattern "ERROR" --start-time $(date -d '-1 hour' +%s000 2>/dev/null || date -v-1H +%s000)
```

**Investigate failures:** See `../infra-cloudwatch-investigation/SKILL.md`
**Complete verification commands:** See `references/cdk-best-practices.md`

---

## Phase 9: Validate the Deploy Script

Before committing, verify the script runs correctly:

```bash
python deploy.py --help                          # Help renders
python deploy.py -e dev -c test --dry-run        # Dry run works
uv run --active ruff check deploy.py             # Linting passes
uv run --active mypy deploy.py                   # Type checking passes
```

---

## Supporting Files Reference

### CDK Quality
- `references/cross-stack-dependencies.md` — Detection, prevention, and migration strategies
- `references/cdk-security-scanning.md` — cdk-nag, Checkov, cfn-lint setup and usage
- `references/cdk-best-practices.md` — Stack organization, constructs, IAM, naming
- `references/deployment-scripts.md` — Multi-customer deployment script patterns (bash)
- `templates/cdk-quality-report.md` — Quality assessment output template
- `scripts/check-cdk-dependencies.sh` — Automated dependency detection script

### Deploy Script Creation
- `templates/deploy-script-template.py` — Complete Python template with all phases implemented
- `scripts/validate_config.py` — Cross-validates .env, customer YAML, and cdk.json config layers
- `scripts/validate_deploy_script.py` — Validates deploy script completeness
- `references/deploy-script-patterns.md` — CLI parsing, AWS profile switching, env file loading
- `references/deployment-best-practices.md` — Safety checks, error handling, recovery patterns
- `references/deploy-script-enhancements.md` — Secrets Manager integration, environment guardrails
- `references/pre-deploy-loop-checks.md` — cfn-lint, Checkov, event-driven loop detection

### Related Skills
- `../dev-implementing-features/SKILL.md` — Feature implementation with deployment verification
- `../infra-auditing-aws-spending/SKILL.md` — Cost analysis for infrastructure changes
- `../infra-detecting-loops/SKILL.md` — Detect infinite loops in Step Functions and event-driven architectures
- `../infra-cloudwatch-investigation/SKILL.md` — Investigate Lambda and Step Function failures via CloudWatch

---

## Key Principles

- **Prevention over remediation:** Catch issues before deployment
- **Plain strings for cross-stack:** Avoid implicit exports from Tokens
- **Incremental fixes:** One stack at a time
- **Verify with AWS CLI:** Trust but verify
- **Python deploy scripts:** Cross-platform, same language as CDK

## Success Criteria

### Static Analysis & Synthesis
- [ ] No circular dependencies between stacks
- [ ] No unnecessary CloudFormation exports
- [ ] cdk-nag/Checkov scans pass (or suppressed with justification)
- [ ] Each stack deployable independently

### Deploy Script (if applicable)
- [ ] All quality checklist items pass
- [ ] `--help` renders correctly
- [ ] `--dry-run` works
- [ ] Passes ruff check and mypy

### Post-Deployment (if applicable)
- [ ] Lambda configurations verified (env vars, secrets, IAM)
- [ ] Secrets Manager accessible
- [ ] Step Function definitions reference correct Lambda ARNs
- [ ] Live AWS tests pass
- [ ] No CloudWatch errors

## When to Use This Skill

- **Before PR review** — Validate CDK changes
- **After AI generates CDK code** — Check for dependency issues
- **Before production deployment** — Final quality gate
- **Creating a new deploy script** — Multi-environment/multi-customer deployment automation
- **Adding new customers/environments** — Extend existing deployment pipeline

## Common Mistakes

**Don't:** Pass L2/L3 constructs between stacks, use Parameter Store lookups at synthesis time, ignore cdk-nag warnings, write deploy scripts that assume default AWS credentials

**Do:** Use plain strings for cross-stack refs, store resource IDs in config, verify with `aws cloudformation list-exports`, fix one stack at a time, use three-layer config separation in deploy scripts
