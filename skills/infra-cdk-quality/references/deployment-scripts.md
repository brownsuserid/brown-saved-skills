# Multi-Customer Deployment Scripts

This guide covers best practices for creating robust deployment scripts that support multi-customer, multi-environment CDK deployments.

## Overview

A well-designed deploy.sh script should:
- Support multiple customers in separate AWS accounts
- Handle multiple environments (dev, staging, prod)
- Automatically manage AWS profiles based on target accounts
- Validate configuration before deployment
- Provide clear feedback and error handling
- Clean up resources and warm up services post-deployment

---

## Script Structure

### Essential Sections

A production-ready deploy.sh should include these sections in order:

```bash
#!/bin/bash
# 1. Header & Documentation
# 2. Argument Parsing
# 3. Validation & Help
# 4. AWS Profile Management
# 5. Environment Setup
# 6. Pre-deployment Validation
# 7. CDK Deployment
# 8. Post-deployment Tasks
# 9. Cleanup & Summary
```

---

## 1. Header & Documentation

Always include comprehensive documentation at the top:

```bash
#!/bin/bash
# Deploy the CDK stack to AWS with multi-environment support
#
# Usage: ./deploy.sh [options]
#
# Options:
#   -e, --environment ENV    Target environment (dev, prod). Default: dev
#   -c, --customer CUSTOMER  Customer name for multi-account deployment
#   -s, --stack-filter STACK Filter to deploy only specific stack
#   -h, --help              Show this help message
#
# Examples:
#   ./deploy.sh -e dev -c acme-corp
#   ./deploy.sh -e prod -c globex-inc
#   ./deploy.sh -e dev -c acme-corp -s MyApiStack
```

---

## 2. Argument Parsing

Use a consistent pattern for parsing command-line arguments:

```bash
# Default values
ENVIRONMENT="dev"
CUSTOMER=""
STACK_FILTER=""
HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--customer)
            CUSTOMER="$2"
            shift 2
            ;;
        -s|--stack-filter)
            STACK_FILTER="$2"
            shift 2
            ;;
        -h|--help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            HELP=true
            shift
            ;;
    esac
done
```

### Feature Flags Pattern

For optional integrations, support both enable and disable flags:

```bash
SLACK_ENABLED=""    # Will read from config by default
FEATURE_X_ENABLED=""    # Will read from config by default

# In argument parsing:
--slack-enabled)
    SLACK_ENABLED="true"
    shift
    ;;
--slack-disabled)
    SLACK_ENABLED="false"
    shift
    ;;
```

This allows overriding configuration file settings per deployment.

---

## 3. Validation & Help

### Help Message

Provide comprehensive help with examples:

```bash
if [ "$HELP" = true ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Target environment (dev, prod). Default: dev"
    echo "  -c, --customer CUSTOMER  Customer name for multi-account deployment"
    echo "  -s, --stack-filter STACK Filter to deploy only specific stack"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev -c acme-corp           # Deploy to dev"
    echo "  $0 -e prod -c globex-inc         # Deploy to customer account"
    echo "  $0 -e dev -c acme-corp -s Stack  # Deploy single stack"
    echo ""
    echo "AWS Account Management:"
    echo "  The script automatically switches AWS profiles based on target accounts."
    exit 0
fi
```

### Input Validation

Validate inputs early and provide helpful error messages:

```bash
# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'dev' or 'prod', got: $ENVIRONMENT"
    exit 1
fi

# Require customer specification
if [ -z "$CUSTOMER" ]; then
    echo "❌ Error: Customer parameter is required for all deployments"
    echo "💡 Please specify a customer with: -c|--customer CUSTOMER_NAME"
    echo ""
    echo "Available customers:"
    echo "  - acme-corp (for internal dev/testing)"
    echo "  - globex-inc (for Globex Inc production)"
    echo ""
    echo "Example: $0 -e dev -c acme-corp"
    exit 1
fi
```

---

## 4. AWS Profile Management

### Account-to-Profile Mapping

Map AWS accounts to named profiles for automatic switching:

```bash
set_aws_profile_for_account() {
    local target_account="$1"
    local suggested_profile=""

    # Account to profile mapping
    case "$target_account" in
        "111111111111")
            suggested_profile="default"         # Internal account
            ;;
        "222222222222")
            suggested_profile="globex-inc"   # Customer account
            ;;
        "333333333333")
            suggested_profile="customer-c"          # Another customer
            ;;
    esac

    if [ -n "$suggested_profile" ]; then
        echo "🔧 Setting AWS profile to '$suggested_profile' for account $target_account"
        export AWS_PROFILE="$suggested_profile"

        # Verify the profile works and points to correct account
        local current_account=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
        if [ $? -ne 0 ]; then
            echo "❌ Error: Failed to access AWS account with profile '$suggested_profile'"
            echo "💡 Please configure AWS CLI profile: aws configure --profile $suggested_profile"
            exit 1
        fi

        if [ "$current_account" != "$target_account" ]; then
            echo "❌ Error: Profile '$suggested_profile' points to account $current_account, but we need $target_account"
            exit 1
        fi

        echo "✅ Successfully switched to account $target_account"
    else
        echo "⚠️  Warning: Unknown account $target_account - no automatic profile available"
    fi
}
```

### Customer Environment Loading

Load customer-specific environment variables:

```bash
if [ -n "$CUSTOMER" ]; then
    echo "🏢 Customer deployment mode: $CUSTOMER"

    # Check if customer environment file exists
    CUSTOMER_ENV_FILE="../.env.$ENVIRONMENT.$CUSTOMER"
    if [ ! -f "$CUSTOMER_ENV_FILE" ]; then
        echo "❌ Error: Customer environment file not found: $CUSTOMER_ENV_FILE"
        echo "💡 Please create customer environment file first"
        exit 1
    fi

    # Load customer environment variables
    echo "📋 Loading customer environment from: $CUSTOMER_ENV_FILE"
    set -a  # automatically export all variables
    source "$CUSTOMER_ENV_FILE"
    set +a  # stop automatically exporting

    # Validate required environment variables
    if [ -z "$CDK_DEFAULT_ACCOUNT" ]; then
        echo "❌ Error: CDK_DEFAULT_ACCOUNT not set in customer environment file"
        exit 1
    fi

    # Switch to correct AWS profile
    set_aws_profile_for_account "$CDK_DEFAULT_ACCOUNT"

    echo "✅ AWS Account validation successful"
    echo "   Account ID: $CDK_DEFAULT_ACCOUNT"
    echo "   Region:     $CDK_DEFAULT_REGION"
    echo "   Profile:    $AWS_PROFILE"
    echo "   Customer:   $CUSTOMER"
fi
```

---

## 5. Environment Setup

### Directory Management

```bash
# Ensure we're in the CDK directory
cd "$(dirname "$0")"

# Clean up old cdk.out directory (preserves last run for debugging)
echo "Cleaning up old CDK output files from previous run..."
if [ -d "cdk.out" ]; then
    rm -rf cdk.out
    echo "Removed previous cdk.out directory"
fi

# Record start time for elapsed time calculation
START_TIME=$(date +%s)
echo "Deployment started at $(date) for $ENVIRONMENT environment"
```

### Python Environment

```bash
# Use the main project's virtual environment
if [ -d "../.venv" ]; then
    echo "Using main project's virtual environment..."
    source ../.venv/bin/activate
elif [ ! -d ".venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Set PYTHONPATH for consistent module resolution
export PYTHONPATH="$(dirname "$(pwd)")"
echo "🐍 Set PYTHONPATH to project root: $PYTHONPATH"
```

### CDK Bootstrap Check

```bash
echo "Checking if AWS CDK is bootstrapped in your account..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &>/dev/null; then
    echo "CDK not bootstrapped yet. Running bootstrap..."
    cdk bootstrap
else
    echo "CDK already bootstrapped. Skipping bootstrap step."
fi
```

---

## 6. Pre-deployment Validation

### Configuration Validation

Always validate configuration files before deployment:

```bash
echo "🔍 Validating YAML configuration files..."
cd ..  # Go to project root

if [ -n "$CUSTOMER" ]; then
    echo "Validating configuration for customer: $CUSTOMER"
    CUSTOMER_NAME="$CUSTOMER" uv run python3 scripts/validate_customer_deployment.py "$CUSTOMER" "$ENVIRONMENT"
else
    echo "Validating standard configuration..."
    # Validate default agent configs
    uv run python3 -c "
import sys
import yaml
from pathlib import Path

config_dir = Path('config/agents')
for config_path in config_dir.glob('*.yaml'):
    try:
        with open(config_path, 'r') as f:
            yaml.safe_load(f)
        print(f'✅ {config_path.name} is valid')
    except yaml.YAMLError as e:
        print(f'❌ {config_path.name} has errors: {e}')
        sys.exit(1)
"
fi

if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed. Please fix errors before deployment."
    exit 1
fi
cd cdk  # Return to CDK directory
```

### Custom Domain Validation

For deployments with custom domains:

```bash
if [ -n "$CUSTOMER" ]; then
    echo "🔍 Validating custom domain configuration..."
    uv run python3 -c "
import json
from pathlib import Path
from validators.custom_domain_validator import validate_custom_domain_config

config_file = f'cdk/config/customers/{\"$CUSTOMER\"}-{\"$ENVIRONMENT\"}.json'
with open(config_file, 'r') as f:
    config = json.load(f)

errors = validate_custom_domain_config(config)
if errors:
    print('❌ Custom domain configuration errors:')
    for error in errors:
        print(f'   - {error}')
    sys.exit(1)
print('✅ Custom domain configuration is valid')
"
    if [ $? -ne 0 ]; then
        echo "❌ Custom domain validation failed."
        exit 1
    fi
fi
```

### Secrets Setup

```bash
if [ -n "$CUSTOMER" ]; then
    echo "Setting up secrets for customer: $CUSTOMER ($ENVIRONMENT environment)..."
    python3 scripts/setup-secrets.py $ENVIRONMENT $CUSTOMER
else
    echo "Setting up secrets for $ENVIRONMENT environment..."
    python3 scripts/setup-secrets.py $ENVIRONMENT
fi
if [ $? -ne 0 ]; then
    echo "Failed to set up secrets. Exiting."
    exit 1
fi
```

---

## 7. CDK Deployment

### Stage Name Computation

Match the CDK app.py logic for stage naming:

```bash
# Compute stage name based on customer and environment
if [ -n "$CUSTOMER" ]; then
    # Remove hyphens/underscores and capitalize
    CUSTOMER_NAME=$(echo "$CUSTOMER" | sed 's/[-_]//g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
    ENV_NAME=$(echo "$ENVIRONMENT" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')
    STAGE_NAME="App${CUSTOMER_NAME}${ENV_NAME}Stage"
else
    if [ "$ENVIRONMENT" = "prod" ]; then
        STAGE_NAME="AppProdStage"
    else
        STAGE_NAME="AppDevStage"
    fi
fi

echo "📦 Computed stage name: $STAGE_NAME"
```

### Stack Pattern and Deploy Command

```bash
# Determine stack pattern
if [ -n "$STACK_FILTER" ]; then
    STACK_PATTERN="\"$STAGE_NAME/$STACK_FILTER\""
    echo "🎯 Stack filter applied: deploying only $STACK_FILTER"
else
    STACK_PATTERN="\"$STAGE_NAME/*\""
fi

# Build deploy command with context flags
CDK_CONTEXT_FLAGS=""
if [ -n "$SLACK_ENABLED" ]; then
    CDK_CONTEXT_FLAGS="$CDK_CONTEXT_FLAGS --context slack_enabled=$SLACK_ENABLED"
fi

if [ -n "$CUSTOMER" ]; then
    DEPLOY_CMD="cdk deploy $STACK_PATTERN --require-approval never --context environment=$ENVIRONMENT --context customer=$CUSTOMER $CDK_CONTEXT_FLAGS"
else
    DEPLOY_CMD="cdk deploy $STACK_PATTERN --require-approval never --context environment=$ENVIRONMENT $CDK_CONTEXT_FLAGS"
fi

echo "🔧 Deploy command: $DEPLOY_CMD"

# Execute deployment and capture output
eval "$DEPLOY_CMD" | tee cdk_deploy_output.txt
status=${PIPESTATUS[0]}
```

### Extract Deployment Outputs

```bash
# Look for the API URL in the output
if [ -f "cdk_deploy_output.txt" ]; then
    api_url=$(grep "ApiGatewayUrl" cdk_deploy_output.txt | awk -F' = ' '{print $2}')

    if [ -z "$api_url" ]; then
        echo "⚠️ Could not parse API URL from output, querying AWS directly..."
        STACK_NAME="${STAGE_NAME}-ApiStack"

        stack_outputs=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs" \
            --output json 2>/dev/null)

        if [ $? -eq 0 ]; then
            api_url=$(echo $stack_outputs | grep -o '"OutputValue": "[^"]*"' | grep "https" | cut -d'"' -f4)
        fi
    fi
fi

# Clean up output file
rm -f cdk_deploy_output.txt
```

---

## 8. Post-deployment Tasks

### Lambda Warm-up

```bash
if [ $status -eq 0 ] && [ -n "$api_url" ]; then
    echo "Warming up the Lambda function..."
    api_url=${api_url%/}  # Remove trailing slash

    if [ "$ENVIRONMENT" = "prod" ]; then
        health_url="$api_url/health"
    else
        health_url="$api_url/$ENVIRONMENT/health"
    fi

    health_response=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null)

    if [ "$health_response" == "200" ]; then
        echo "✅ Lambda warm-up successful!"
        echo "🌐 API Base URL: $api_url"
    else
        echo "⚠️ Warm-up returned status: $health_response (non-critical)"
    fi
fi
```

### Orphaned Secrets Cleanup

```bash
if [ $status -eq 0 ]; then
    echo "🗑️  Running orphaned secrets cleanup..."
    cd ..

    if [ -f "scripts/cleanup-orphaned-secrets.py" ]; then
        echo "🧹 Cleaning up orphaned secrets older than 24 hours..."
        uv run python scripts/cleanup-orphaned-secrets.py --execute --older-than-hours 24
    fi

    cd cdk
fi
```

### Custom Domain DNS Verification

```bash
verify_custom_domain_dns() {
    local customer_config="config/customers/${CUSTOMER}-${ENVIRONMENT}.json"

    if [ ! -f "$customer_config" ]; then
        return 0
    fi

    # Extract custom domain info
    local domain_name=$(jq -r '.customDomain.domainName // ""' "$customer_config")
    local domain_enabled=$(jq -r '.customDomain.enabled // false' "$customer_config")

    if [ "$domain_enabled" != "true" ] || [ -z "$domain_name" ]; then
        return 0
    fi

    echo "🔍 Testing DNS resolution for: $domain_name"

    # Test DNS resolution with retries
    for attempt in {1..6}; do
        if nslookup "$domain_name" >/dev/null 2>&1; then
            echo "✅ DNS resolution successful"

            # Test endpoint
            local custom_health_url="https://$domain_name/$ENVIRONMENT/health"
            local response=$(curl -s -o /dev/null -w "%{http_code}" "$custom_health_url")

            if [ "$response" == "200" ]; then
                echo "✅ Custom domain working: $domain_name"
            fi
            return 0
        fi
        sleep 10
    done

    echo "⚠️ DNS not resolving for $domain_name"
}

if [ $status -eq 0 ] && [ -n "$CUSTOMER" ]; then
    verify_custom_domain_dns
fi
```

---

## 9. Cleanup & Summary

### Docker Cleanup

CDK builds can leave many unused Docker images:

```bash
cleanup_docker_resources() {
    echo "🧹 Cleaning up Docker resources..."

    # Remove dangling images
    docker image prune -f >/dev/null 2>&1

    # Remove unused containers, volumes, networks
    docker container prune -f >/dev/null 2>&1
    docker volume prune -f >/dev/null 2>&1
    docker network prune -f >/dev/null 2>&1

    # Remove build cache
    docker builder prune -a -f >/dev/null 2>&1

    # Aggressive cleanup of unused images
    docker image prune -a -f >/dev/null 2>&1

    # System-wide cleanup
    docker system prune -a -f --volumes >/dev/null 2>&1

    # Clean CDK temp files
    find /tmp -name "cdk*" -type d -mtime +0 -exec rm -rf {} + 2>/dev/null

    echo "✅ Docker cleanup completed"
}

cleanup_docker_resources
```

### Deployment Summary

```bash
# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED_TIME / 60))
SECONDS=$((ELAPSED_TIME % 60))

echo "🎉 Deployment completed in ${MINUTES}m ${SECONDS}s"

# Show deployment status
if [ $status -eq 0 ]; then
    echo ""
    echo "📋 Deployment Summary:"
    echo "   Environment: $ENVIRONMENT"
    echo "   Customer:    $CUSTOMER"
    echo "   API URL:     $api_url"
    echo ""
    echo "📋 Next Steps:"
    if [ "$ENVIRONMENT" = "dev" ]; then
        echo "1. Test the deployment with development workspace"
        echo "2. Monitor CloudWatch logs and metrics"
    else
        echo "1. Verify production functionality"
        echo "2. Monitor CloudWatch metrics"
    fi
fi

# Display API endpoints
if [ $status -eq 0 ] && [ -n "$api_url" ]; then
    echo ""
    echo "🌐 API Endpoints:"
    echo "📍 Base URL:     $api_url"
    echo "📍 Health:       $api_url/health"
fi

exit $status
```

---

## File Organization

### Recommended Directory Structure

```
project/
├── cdk/
│   ├── deploy.sh              # Main deployment script
│   ├── config/
│   │   ├── dev.json           # Default dev config
│   │   ├── prod.json          # Default prod config
│   │   └── customers/
│   │       ├── acme-corp-dev.json
│   │       ├── acme-corp-prod.json
│   │       ├── globex-inc-prod.json
│   │       └── ...
│   ├── scripts/
│   │   ├── setup-secrets.py
│   │   └── validate_customer_deployment.py
│   └── validators/
│       └── custom_domain_validator.py
├── .env.dev.acme-corp      # Customer env files at project root
├── .env.prod.acme-corp
├── .env.prod.globex-inc
└── scripts/
    └── cleanup-orphaned-secrets.py
```

### Customer Environment File Format

`.env.prod.customer-name`:
```bash
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1
AWS_PROFILE=customer-profile    # Optional - auto-detected if not set

# Customer-specific settings
CUSTOMER_API_KEY=xxx
CUSTOMER_WEBHOOK_URL=https://...
```

---

## Best Practices Summary

### Do's

- ✅ Require explicit customer specification for all deployments
- ✅ Validate configuration before deployment
- ✅ Automatically switch AWS profiles based on target account
- ✅ Verify AWS credentials work for target account
- ✅ Clean up Docker resources after deployment
- ✅ Warm up Lambda functions post-deployment
- ✅ Display deployment summary with URLs and credentials
- ✅ Calculate and display elapsed time
- ✅ Provide comprehensive help with examples

### Don'ts

- ❌ Don't assume default AWS profile works
- ❌ Don't skip configuration validation
- ❌ Don't leave cdk.out from previous runs
- ❌ Don't hardcode account IDs in the script logic
- ❌ Don't proceed if environment file is missing
- ❌ Don't skip CDK bootstrap check

---

## Troubleshooting

### Common Issues

**"Failed to access AWS account with profile"**
- Verify AWS CLI is configured: `aws configure list`
- Check profile exists: `aws configure list-profiles`
- Test credentials: `aws sts get-caller-identity --profile PROFILE_NAME`

**"Customer environment file not found"**
- Create `.env.ENVIRONMENT.CUSTOMER` at project root
- Ensure `CDK_DEFAULT_ACCOUNT` is set
- Verify file naming matches customer name exactly

**"CDK_DEFAULT_ACCOUNT not set"**
- Add `CDK_DEFAULT_ACCOUNT=123456789012` to customer env file
- Ensure file is being sourced correctly (check path)

**Stack deployment fails with export errors**
- See `cross-stack-dependencies.md` for resolution
- Use `--stack-filter` to deploy specific stacks in order

**Docker disk space issues**
- Run `cleanup_docker_resources` function manually
- Check disk space: `df -h /var/lib/docker`
- Consider more aggressive cleanup: `docker system prune -a --volumes`
