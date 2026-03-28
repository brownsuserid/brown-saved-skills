# Project Resource Discovery Guide

Guide for analyzing codebases to understand AWS resource usage before conducting project-level cost audits.

## Overview

Before auditing a specific project's AWS costs, you need to understand what resources the project deploys. This guide covers:
1. Analyzing Infrastructure-as-Code (IaC) to identify resources
2. Understanding naming conventions and tagging strategies
3. Using the discovery script to find deployed resources
4. Filtering cost queries to project-specific resources

---

## Analyzing CDK Projects

### TypeScript CDK Projects

**Entry point analysis:**
```bash
# Find the CDK app entry point
cat bin/*.ts

# Look for stack definitions
rg "new.*Stack\(" bin/*.ts
```

**Resource identification in lib/:**
```bash
# Find all AWS service imports
rg "from 'aws-cdk-lib" lib/*.ts

# Find specific service usage
rg "new lambda\." lib/*.ts -i
rg "new dynamodb\." lib/*.ts -i
rg "new s3\." lib/*.ts -i
rg "new rds\." lib/*.ts -i
rg "new apigateway\." lib/*.ts -i
rg "new ecs\." lib/*.ts -i
rg "new ec2\." lib/*.ts -i
rg "new elasticache\." lib/*.ts -i
```

**Extract resource names:**
```bash
# Find function names
rg "functionName:" lib/*.ts

# Find table names
rg "tableName:" lib/*.ts

# Find bucket names
rg "bucketName:" lib/*.ts
```

### Python CDK Projects

**Entry point analysis:**
```bash
# Find the CDK app entry point
cat app.py

# Look for stack instantiation
rg "Stack\(" app.py
```

**Resource identification:**
```bash
# Find AWS service imports
rg "from aws_cdk import" **/*.py
rg "from aws_cdk\." **/*.py

# Find specific constructs
rg "lambda_\.Function\(" **/*.py
rg "dynamodb\.Table\(" **/*.py
rg "s3\.Bucket\(" **/*.py
rg "rds\.DatabaseInstance\(" **/*.py
```

---

## Analyzing CloudFormation Templates

### YAML Templates

```bash
# Find all CloudFormation templates
find . -name "*.yaml" -o -name "*.yml" | xargs grep -l "AWSTemplateFormatVersion\|Resources:"

# List resource types in a template
yq '.Resources | keys' template.yaml
yq '.Resources | to_entries | .[].value.Type' template.yaml
```

### JSON Templates

```bash
# Find resource types
jq '.Resources | to_entries | .[].value.Type' template.json

# Find Lambda functions
jq '.Resources | to_entries | .[] | select(.value.Type == "AWS::Lambda::Function") | .key' template.json
```

---

## Analyzing Terraform Projects

```bash
# Find all Terraform files
ls *.tf **/*.tf

# List resource types
rg "^resource \"aws_" *.tf

# Find specific resources
rg "resource \"aws_lambda_function\"" *.tf
rg "resource \"aws_dynamodb_table\"" *.tf
rg "resource \"aws_s3_bucket\"" *.tf
rg "resource \"aws_rds_" *.tf
```

---

## Analyzing SAM Templates

```bash
# Check for SAM template
cat template.yaml | head -20

# Find serverless functions
yq '.Resources | to_entries | .[] | select(.value.Type == "AWS::Serverless::Function") | .key' template.yaml

# Find API definitions
yq '.Resources | to_entries | .[] | select(.value.Type == "AWS::Serverless::Api") | .key' template.yaml
```

---

## Understanding Naming Conventions

### Common Patterns

| Pattern | Example | Components |
|---------|---------|------------|
| `{app}-{env}-{resource}` | `myapp-prod-users-table` | Application, environment, resource |
| `{company}-{project}-{env}-{resource}` | `acme-billing-dev-api` | Company, project, environment, resource |
| `{stack}-{resource}` | `BillingStack-ProcessorFunction` | CDK stack name, logical ID |

### Identify Project Prefix

```bash
# Look for consistent prefixes in CDK
rg "const.*prefix\s*=" **/*.ts
rg "app_name\s*=" **/*.py

# Check environment variables
rg "process\.env\." **/*.ts | grep -i "prefix\|name\|project"

# Look in configuration files
cat cdk.json | jq '.context'
cat samconfig.toml 2>/dev/null
```

### Extract Environment Names

```bash
# Find environment definitions
rg "environment" cdk.json
rg "stage\s*=" **/*.py
rg "env:" **/*.yaml
```

---

## Understanding Tagging Strategy

### Check Existing Tags in Code

```bash
# CDK tags
rg "Tags\.of\(" **/*.ts
rg "cdk\.Tags\.of\(" **/*.ts
rg "tags=" **/*.py

# CloudFormation tags
yq '.Resources[].Properties.Tags' template.yaml

# Terraform tags
rg "tags\s*=" *.tf -A 5
```

### Common Cost Allocation Tags

| Tag Key | Purpose |
|---------|---------|
| `Project` | Project identifier |
| `Environment` | dev/staging/prod |
| `CostCenter` | Financial tracking |
| `Owner` | Team or individual |
| `Application` | Application name |

### Verify Tags in AWS

```bash
# Check tags on a Lambda function
aws lambda list-tags --resource arn:aws:lambda:REGION:ACCOUNT:function:FUNCTION_NAME

# Check tags on an EC2 instance
aws ec2 describe-tags --filters "Name=resource-id,Values=i-xxx"

# List all tags in use
aws resourcegroupstaggingapi get-tag-keys
```

---

## Using the Discovery Script

### Basic Usage

```bash
# By prefix
./scripts/discover-project-resources.sh -p "myapp-prod"

# By tag
./scripts/discover-project-resources.sh -t "Project=myapp"

# Multiple tags
./scripts/discover-project-resources.sh -t "Project=myapp" -t "Environment=prod"

# By CloudFormation stack pattern
./scripts/discover-project-resources.sh -s "MyAppProd"
```

### Output Format

The script generates `project-resources.json`:

```json
{
  "lambda_functions": [
    ["myapp-prod-processor", "python3.11", 512, 30, "2025-01-15T..."]
  ],
  "dynamodb_tables": [
    ["myapp-prod-users", "ACTIVE", 1500, 524288, "PAY_PER_REQUEST"]
  ],
  "s3_buckets": [
    "myapp-prod-uploads",
    "myapp-prod-logs"
  ],
  "rds_instances": [],
  "api_gateway": [
    ["myapp-prod-api", "abc123", "HTTP", "https://abc123.execute-api..."]
  ]
}
```

### Using Results for Cost Filtering

```bash
# Extract Lambda function names for cost filtering
jq -r '.lambda_functions[][0]' project-resources.json

# Extract DynamoDB table names
jq -r '.dynamodb_tables[][0]' project-resources.json

# Get all resource identifiers
jq -r '.. | strings' project-resources.json | grep -E "^(arn:|myapp-)"
```

---

## Filtering Cost Explorer by Project

### By Resource Tags

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "Tags": {
      "Key": "Project",
      "Values": ["myapp"]
    }
  }'
```

### By Service and Resource

```bash
# Filter to specific Lambda functions
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "And": [
      {"Dimensions": {"Key": "SERVICE", "Values": ["AWS Lambda"]}},
      {"Tags": {"Key": "Project", "Values": ["myapp"]}}
    ]
  }'
```

### Combine Multiple Tags

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "And": [
      {"Tags": {"Key": "Project", "Values": ["myapp"]}},
      {"Tags": {"Key": "Environment", "Values": ["prod"]}}
    ]
  }'
```

---

## Common Resource Types to Find

### High-Cost Resources

| Service | What to Look For | Cost Impact |
|---------|------------------|-------------|
| EC2 | Instance types, reserved/spot usage | High |
| RDS | Instance class, storage, multi-AZ | High |
| ElastiCache | Node types, cluster size | Medium-High |
| NAT Gateway | Data processing | Medium |
| Lambda | Memory size, duration, invocations | Variable |
| DynamoDB | Provisioned vs on-demand, storage | Variable |
| S3 | Storage class, data transfer | Variable |
| CloudWatch | Log retention, custom metrics | Low-Medium |

### Often-Forgotten Resources

- **Log Groups** - Can grow indefinitely without retention
- **Snapshots** - Old EBS snapshots pile up
- **Secrets** - $0.40/month each
- **NAT Gateways** - $32+/month each
- **Elastic IPs** - $3.60/month when unattached
- **Load Balancers** - $16+/month minimum

---

## Checklist Before Audit

- [ ] IaC type identified (CDK/CloudFormation/Terraform/SAM)
- [ ] Resource naming pattern understood
- [ ] Project prefix documented
- [ ] Tagging strategy documented
- [ ] Environments identified (dev/staging/prod)
- [ ] Discovery script executed
- [ ] Resource list reviewed and saved
- [ ] Cost allocation tags verified in AWS

---

## Summary

1. **Analyze code first** - Understand what the project deploys
2. **Identify naming patterns** - Find the prefix used for resources
3. **Check tagging strategy** - Tags enable cost filtering
4. **Run discovery script** - Get actual deployed resources
5. **Use results for filtering** - Focus cost queries on project resources
