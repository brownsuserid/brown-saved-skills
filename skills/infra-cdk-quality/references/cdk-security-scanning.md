# CDK Security Scanning Guide

This guide covers setup and usage of security scanning tools for AWS CDK: cdk-nag, Checkov, and cfn-lint.

## Tool Overview

| Tool | Purpose | Checks At | Language Support |
|------|---------|-----------|------------------|
| cdk-nag | Security & compliance rules | Synthesis time | TS, Python, Java, .NET |
| Checkov | IaC security scanning | Post-synthesis | Any (scans CloudFormation) |
| cfn-lint | CloudFormation validation | Post-synthesis | Any (scans CloudFormation) |

---

## cdk-nag

cdk-nag validates CDK constructs against security and compliance rule packs during synthesis.

### Installation

```bash
# TypeScript/JavaScript
npm install cdk-nag

# Python
pip install cdk-nag
```

### Available Rule Packs

| Rule Pack | Description | Use Case |
|-----------|-------------|----------|
| `AwsSolutionsChecks` | General AWS best practices | Default for all projects |
| `HIPAASecurityChecks` | Healthcare compliance | Healthcare applications |
| `NIST80053R4Checks` | Federal security (rev 4) | Government/regulated |
| `NIST80053R5Checks` | Federal security (rev 5) | Government/regulated |
| `PCIDSS321Checks` | Payment card industry | E-commerce, payments |
| `ServerlessChecks` | Serverless best practices | Lambda-heavy apps |

### Basic Setup (TypeScript)

```typescript
import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';

const app = new App();
const stack = new MyStack(app, 'MyStack');

// Add cdk-nag checks
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

// Multiple rule packs can be combined
Aspects.of(app).add(new NIST80053R5Checks());
```

### Basic Setup (Python)

```python
from aws_cdk import App, Aspects
from cdk_nag import AwsSolutionsChecks, NagSuppressions

app = App()
stack = MyStack(app, "MyStack")

# Add cdk-nag checks
Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
```

### Running cdk-nag

```bash
# cdk-nag runs during synthesis
npx cdk synth 2>&1 | tee cdk-nag-output.txt

# Errors will fail synthesis, warnings are informational
```

### Suppressing Rules

Sometimes rules need to be suppressed with justification:

```typescript
import { NagSuppressions } from 'cdk-nag';

// Suppress on a specific resource
NagSuppressions.addResourceSuppressions(myBucket, [
  {
    id: 'AwsSolutions-S1',
    reason: 'Access logs stored in centralized logging bucket',
  },
]);

// Suppress on entire stack
NagSuppressions.addStackSuppressions(stack, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'Using AWS managed policies is acceptable for this use case',
  },
]);

// Suppress with path pattern
NagSuppressions.addResourceSuppressionsByPath(stack, '/MyStack/MyFunction/ServiceRole/Resource', [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'Lambda execution role requires managed policy',
  },
]);
```

### Common cdk-nag Rules

| Rule ID | Description | Fix |
|---------|-------------|-----|
| AwsSolutions-S1 | S3 bucket without access logs | Enable access logging |
| AwsSolutions-S2 | S3 bucket without public access block | Add public access block |
| AwsSolutions-S3 | S3 bucket without SSL enforcement | Add bucket policy requiring SSL |
| AwsSolutions-IAM4 | Using AWS managed policies | Use customer managed policies |
| AwsSolutions-IAM5 | Wildcard permissions | Scope down to specific resources |
| AwsSolutions-L1 | Lambda not using latest runtime | Update runtime version |
| AwsSolutions-RDS10 | RDS without deletion protection | Enable deletion protection |
| AwsSolutions-DDB3 | DynamoDB without PITR | Enable point-in-time recovery |

### Unit Testing with cdk-nag

```typescript
import { Annotations, Match } from 'aws-cdk-lib/assertions';
import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';

test('No cdk-nag errors', () => {
  const app = new App();
  const stack = new MyStack(app, 'TestStack');

  Aspects.of(app).add(new AwsSolutionsChecks());

  const annotations = Annotations.fromStack(stack);

  // Assert no errors
  annotations.hasNoError('*', Match.anyValue());

  // Or check for specific warnings
  annotations.hasWarning('*', Match.stringLikeRegexp('AwsSolutions-S1'));
});
```

---

## Checkov

Checkov scans synthesized CloudFormation templates for security misconfigurations.

### Installation

```bash
pip install checkov

# Or with pipx for isolation
pipx install checkov
```

### Basic Usage

```bash
# Synthesize CDK first
npx cdk synth --all --quiet

# Scan all templates
checkov -d cdk.out/ --framework cloudformation

# Scan specific template
checkov -f cdk.out/MyStack.template.json --framework cloudformation
```

### Output Formats

```bash
# CLI output (default)
checkov -d cdk.out/ --framework cloudformation

# JSON output for CI/CD
checkov -d cdk.out/ --framework cloudformation --output json > checkov-report.json

# JUnit XML for test reporting
checkov -d cdk.out/ --framework cloudformation --output junitxml > checkov-junit.xml

# SARIF for GitHub code scanning
checkov -d cdk.out/ --framework cloudformation --output sarif > checkov.sarif
```

### Filtering Results

```bash
# Only show failed checks
checkov -d cdk.out/ --framework cloudformation --compact

# Run specific checks
checkov -d cdk.out/ --framework cloudformation --check CKV_AWS_18,CKV_AWS_19

# Skip specific checks
checkov -d cdk.out/ --framework cloudformation --skip-check CKV_AWS_18

# Filter by severity
checkov -d cdk.out/ --framework cloudformation --check-severity HIGH,CRITICAL
```

### Common Checkov Rules

| Check ID | Description | Severity |
|----------|-------------|----------|
| CKV_AWS_18 | S3 access logging disabled | Medium |
| CKV_AWS_19 | S3 encryption disabled | High |
| CKV_AWS_20 | S3 public access not blocked | Critical |
| CKV_AWS_21 | S3 versioning disabled | Medium |
| CKV_AWS_23 | Security group allows 0.0.0.0/0 | High |
| CKV_AWS_24 | Security group allows SSH from 0.0.0.0/0 | Critical |
| CKV_AWS_33 | KMS key rotation disabled | Medium |
| CKV_AWS_45 | Lambda in VPC | Low |
| CKV_AWS_116 | Lambda DLQ not configured | Medium |
| CKV_AWS_117 | Lambda not in VPC | Low |

### Suppressing Checkov Rules

Create `.checkov.yaml` in project root:

```yaml
skip-check:
  - CKV_AWS_18  # S3 access logging - using centralized logging
  - CKV_AWS_45  # Lambda VPC - not required for this use case

# Or skip by path pattern
skip-path:
  - cdk.out/TestStack.template.json
```

Or inline in CloudFormation (add via CDK escape hatch):

```typescript
const cfnBucket = bucket.node.defaultChild as s3.CfnBucket;
cfnBucket.addMetadata('checkov', {
  skip: [
    {
      id: 'CKV_AWS_18',
      comment: 'Access logs stored in centralized logging bucket',
    },
  ],
});
```

---

## cfn-lint

cfn-lint validates CloudFormation templates against AWS specifications and best practices.

### Installation

```bash
pip install cfn-lint

# Or with pipx
pipx install cfn-lint
```

### Basic Usage

```bash
# Synthesize CDK first
npx cdk synth --all --quiet

# Lint all templates
cfn-lint cdk.out/*.template.json

# Lint specific template
cfn-lint cdk.out/MyStack.template.json
```

### Output Formats

```bash
# Default parseable format
cfn-lint cdk.out/*.template.json

# JSON format
cfn-lint cdk.out/*.template.json -f json

# JUnit XML for CI
cfn-lint cdk.out/*.template.json -f junit > cfn-lint-junit.xml
```

### Rule Categories

| Prefix | Category | Example |
|--------|----------|---------|
| E | Error | E3012 - Invalid property value |
| W | Warning | W2001 - Unused parameter |
| I | Info | I3042 - Hardcoded partition |

### Common cfn-lint Rules

| Rule | Description | Action |
|------|-------------|--------|
| E1001 | Basic template errors | Fix template syntax |
| E3001 | Invalid resource type | Use correct resource type |
| E3012 | Invalid property value | Fix property value |
| W1001 | Unused mapping | Remove or use mapping |
| W2001 | Unused parameter | Remove or use parameter |
| W3010 | Hardcoded availability zone | Use intrinsic functions |

### CDK Compatibility Notes

CDK-generated templates may trigger some false positives:

```bash
# Common CDK-related warnings to ignore
cfn-lint cdk.out/*.template.json \
  --ignore-checks W2001 \  # Unused parameters (CDK generates these)
  --ignore-checks W3010    # AZ handling (CDK manages this)
```

### Configuration File

Create `.cfnlintrc.yaml`:

```yaml
templates:
  - cdk.out/*.template.json

ignore_checks:
  - W2001  # CDK generates unused parameters
  - W3010  # CDK handles AZ selection

configure_rules:
  E3012:
    strict: false  # Relax strictness for CDK
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: CDK Quality Checks

on: [push, pull_request]

jobs:
  cdk-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          npm ci
          pip install checkov cfn-lint

      - name: CDK Synth (includes cdk-nag)
        run: npx cdk synth --all

      - name: Run Checkov
        run: |
          checkov -d cdk.out/ \
            --framework cloudformation \
            --output junitxml > checkov-results.xml
        continue-on-error: true

      - name: Run cfn-lint
        run: cfn-lint cdk.out/*.template.json

      - name: Upload Checkov Results
        uses: actions/upload-artifact@v4
        with:
          name: checkov-results
          path: checkov-results.xml
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: cdk-synth
        name: CDK Synth
        entry: npx cdk synth --all --quiet
        language: system
        pass_filenames: false
        files: ^(lib|bin)/.*\.(ts|py)$

      - id: cfn-lint
        name: cfn-lint
        entry: cfn-lint cdk.out/*.template.json
        language: system
        pass_filenames: false
        files: ^(lib|bin)/.*\.(ts|py)$
```

---

## Severity Mapping

When prioritizing fixes, map findings to severity levels:

| Severity | Examples | Action |
|----------|----------|--------|
| Critical | Public S3, open security groups, hardcoded secrets | Fix immediately |
| High | Missing encryption, wildcard IAM, no logging | Fix before merge |
| Medium | Missing PITR, no versioning, managed policies | Fix soon |
| Low | Lambda not in VPC, missing tags | Nice to have |

---

## Summary: Running All Scans

```bash
#!/bin/bash
# cdk-quality-scan.sh

set -e

echo "=== CDK Synth (with cdk-nag) ==="
npx cdk synth --all 2>&1 | tee cdk-nag-output.txt

echo "=== Checkov Scan ==="
checkov -d cdk.out/ --framework cloudformation --compact

echo "=== cfn-lint ==="
cfn-lint cdk.out/*.template.json

echo "=== All scans complete ==="
```
