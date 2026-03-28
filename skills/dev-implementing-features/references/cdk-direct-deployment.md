# Direct CDK Deployment Commands

Step-by-step instructions for deploying CDK stacks directly via `npx cdk`, bypassing deploy scripts when needed.

## Table of Contents

- [When to Use Direct Commands](#when-to-use-direct-commands)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Deployment Commands](#deployment-commands)
- [Stage Naming Convention](#stage-naming-convention)
- [Deployment Verification](#deployment-verification)
- [Troubleshooting](#troubleshooting)

---

## When to Use Direct Commands

Use direct CDK commands instead of `deploy.sh` when:
- **Windows environment** — `deploy.sh` uses Unix paths that may fail
- **Debugging deployment** — need exact CDK output without script processing
- **Partial deployments** — need finer control over which stacks deploy

Use `deploy.sh` when on Unix/Mac and running standard full deployments.

---

## Prerequisites

```bash
# AWS CLI installed and configured
aws --version
aws configure list-profiles
aws sts get-caller-identity --profile YOUR_PROFILE

# For SSO profiles, ensure login
aws sso login --profile YOUR_SSO_PROFILE

# Node.js and CDK available
node --version
npx cdk --version
```

---

## Environment Variables

These MUST be set before running CDK:

| Variable | Description | Example |
|----------|-------------|---------|
| `CDK_DEFAULT_ACCOUNT` | AWS Account ID | `123456789012` |
| `CDK_DEFAULT_REGION` | AWS Region | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile | `your-profile-name` |
| `PYTHONPATH` | Project root for imports | `/path/to/project` |

Projects typically have customer-specific env files at the project root (e.g., `.env.dev.customer-name`).

---

## Deployment Commands

### Deploy All Stacks for a Stage

```bash
cd PROJECT_ROOT/cdk

export CDK_DEFAULT_ACCOUNT=YOUR_ACCOUNT_ID
export CDK_DEFAULT_REGION=us-east-1
export AWS_PROFILE=YOUR_AWS_PROFILE
export PYTHONPATH="$(dirname $(pwd))"

npx cdk deploy "STAGE_NAME/*" \
  --require-approval never \
  --context environment=ENVIRONMENT \
  --context customer=CUSTOMER \
  --profile YOUR_AWS_PROFILE
```

### Deploy Specific Stacks

```bash
# Single stack
npx cdk deploy "STAGE_NAME/StackName" \
  --require-approval never \
  --context environment=dev \
  --context customer=customer-name \
  --profile YOUR_AWS_PROFILE

# Multiple specific stacks
npx cdk deploy "STAGE_NAME/ApiStack" "STAGE_NAME/AgentsStack" \
  --require-approval never \
  --context environment=dev \
  --context customer=customer-name \
  --profile YOUR_AWS_PROFILE
```

### Windows (PowerShell)

```powershell
cd C:\path\to\project\cdk

$env:CDK_DEFAULT_ACCOUNT = "YOUR_ACCOUNT_ID"
$env:CDK_DEFAULT_REGION = "us-east-1"
$env:AWS_PROFILE = "YOUR_AWS_PROFILE"
$env:PYTHONPATH = (Get-Item ..).FullName

npx cdk deploy "STAGE_NAME/*" `
  --require-approval never `
  --context environment=dev `
  --context customer=customer-name `
  --profile YOUR_AWS_PROFILE
```

---

## Stage Naming Convention

CDK stages follow this pattern (defined in `cdk/app.py`):

```
AIT{CustomerName}{Environment}Stage
```

Where `CustomerName` has hyphens/underscores removed and is title-cased, and `Environment` is `Dev` or `Prod`.

**Examples:**

| Customer | Environment | Stage Name |
|----------|-------------|------------|
| `my-customer` | `dev` | `AITMycustomerDevStage` |
| `my-customer` | `prod` | `AITMycustomerProdStage` |

---

## Deployment Verification

```bash
# Check CloudFormation stack status
aws cloudformation list-stacks \
  --profile YOUR_PROFILE \
  --query "StackSummaries[?contains(StackName, 'AIT') && StackStatus=='CREATE_COMPLETE' || StackStatus=='UPDATE_COMPLETE'].[StackName,StackStatus]" \
  --output table

# Get API URL from stack outputs
aws cloudformation describe-stacks \
  --stack-name STAGE_NAME-ApiStack \
  --profile YOUR_PROFILE \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].OutputValue" \
  --output text

# Test health endpoint
curl -s https://YOUR_API_URL/dev/health

# List Lambda functions
aws lambda list-functions \
  --profile YOUR_PROFILE \
  --query "Functions[?contains(FunctionName, 'ait')].[FunctionName,LastModified]" \
  --output table
```

---

## Troubleshooting

### "Unable to parse environment specification"

```
Unable to parse environment specification "aws:///us-east-1".
Expected format: aws://account/region
```

Fix: Set `CDK_DEFAULT_ACCOUNT`:
```bash
export CDK_DEFAULT_ACCOUNT=YOUR_ACCOUNT_ID
```

### "No credentials have been configured"

```
Need to perform AWS calls for account XXXX, but no credentials have been configured
```

Fix:
1. Ensure AWS profile is configured
2. Run SSO login if using SSO: `aws sso login --profile YOUR_PROFILE`
3. Add `--profile` flag to CDK command

### "The config profile could not be found"

Fix: Configure the profile in `~/.aws/config`:
```ini
[profile your-profile]
sso_start_url = https://your-sso-url.awsapps.com/start
sso_region = us-east-1
sso_account_id = YOUR_ACCOUNT_ID
sso_role_name = YourRoleName
region = us-east-1
```

### Docker Build Failures

If Lambda Docker builds fail:
1. Ensure Docker is running
2. For ARM64 Lambda builds on x86, Docker BuildX with QEMU is needed:
```bash
docker run --privileged --rm tonistiigi/binfmt --install all
docker buildx ls
```

### Stack Export Errors

If deployment fails with circular dependency or export errors, deploy stacks individually in dependency order. Check `cdk synth` output to understand stack dependencies.
