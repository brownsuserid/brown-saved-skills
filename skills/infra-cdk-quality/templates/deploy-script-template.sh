#!/bin/bash
# ============================================================================
# Deploy Script Template
# ============================================================================
# Description: CDK deployment script with multi-environment and multi-customer support
# Usage: ./deploy.sh -e ENVIRONMENT -c CUSTOMER [OPTIONS]
#
# CUSTOMIZATION REQUIRED:
# Search for "CUSTOMIZE:" comments and update values for your project:
#   - PROJECT_NAME: Your project identifier
#   - AWS account mappings in set_aws_profile_for_account()
#   - Required environment variables in validate_customer_env_file()
#   - CDK context flags in build_cdk_command()
#   - Health check endpoints in run_post_deployment_checks()
# ============================================================================

set -euo pipefail

# ============================================================================
# Configuration - CUSTOMIZE: Update these for your project
# ============================================================================

# CUSTOMIZE: Project name (used in prefixes and logging)
readonly PROJECT_NAME="my-project"

# Valid environments
readonly VALID_ENVIRONMENTS="dev staging prod"

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_INVALID_ARGS=1
readonly EXIT_MISSING_DEPS=2
readonly EXIT_AWS_AUTH_FAILED=3
readonly EXIT_ACCOUNT_MISMATCH=4
readonly EXIT_ENV_FILE_MISSING=5
readonly EXIT_SECRETS_FAILED=6
readonly EXIT_CDK_FAILED=10
readonly EXIT_HEALTH_CHECK_FAILED=11
readonly EXIT_USER_CANCELLED=20

# Script directory (for relative paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# Default Values
# ============================================================================

ENVIRONMENT=""
CUSTOMER=""
STACK_FILTER=""
HELP=false
VERBOSE=false
DRY_RUN=false
SKIP_HEALTH_CHECK=false
FORCE=false

# Integration toggles - CUSTOMIZE: Add/remove as needed
SLACK_ENABLED=true
# LINDY_ENABLED=true

# Deployment tracking
DEPLOYMENT_START_TIME=""
DEPLOYED_STACKS=0
TEMP_FILES=()

# Loaded from customer env file
AWS_ACCOUNT_ID=""
AWS_REGION=""
PROJECT_PREFIX=""

# ============================================================================
# Cleanup Handler
# ============================================================================

cleanup() {
    local exit_code=$?

    # Remove temporary files
    for temp_file in "${TEMP_FILES[@]}"; do
        [ -f "$temp_file" ] && rm -f "$temp_file"
    done

    # Report final status
    if [ $exit_code -eq 0 ]; then
        if [ -n "$DEPLOYMENT_START_TIME" ]; then
            show_deployment_summary
        fi
    else
        echo ""
        echo "Deployment exited with code $exit_code"
    fi

    exit $exit_code
}

trap cleanup EXIT

# ============================================================================
# Logging Functions
# ============================================================================

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "[DEBUG] $*"
    fi
}

log_info() {
    echo "$*"
}

log_error() {
    echo "$*" >&2
}

show_phase() {
    local phase_num="$1"
    local phase_name="$2"
    local total_phases="${3:-6}"

    echo ""
    echo "========================================"
    echo "  Phase $phase_num/$total_phases: $phase_name"
    echo "========================================"
    echo ""
}

# ============================================================================
# Help System
# ============================================================================

show_help() {
    cat << 'EOF'
Usage: ./deploy.sh -e ENVIRONMENT -c CUSTOMER [OPTIONS]

Deploy CDK stacks for a specific customer environment.

Required:
  -e, --environment ENV   Target environment (dev, staging, prod)
  -c, --customer NAME     Customer name for configuration lookup

Options:
  -s, --stack-filter PAT  Deploy only stacks matching pattern
  --skip-health-check     Skip post-deployment health verification
  --slack-disabled        Deploy without Slack integration
  --dry-run               Show what would be deployed without deploying
  --force                 Continue even with pending CloudFormation operations
  -v, --verbose           Enable verbose output for debugging
  -h, --help              Show this help message

Examples:
  # Deploy all stacks to dev for customer 'acme'
  ./deploy.sh -e dev -c acme

  # Deploy only Lambda stacks to production
  ./deploy.sh -e prod -c acme -s "Lambda*"

  # Preview deployment without making changes
  ./deploy.sh -e dev -c acme --dry-run

  # Deploy without Slack notifications
  ./deploy.sh -e dev -c acme --slack-disabled

  # Verbose deployment for troubleshooting
  ./deploy.sh -e dev -c acme -v

Environment Files:
  Customer secrets should be in: .env.{environment}.{customer}
  Template with placeholders:    .env.TEMPLATE (committed to git)

  NOTE: .env files contain secrets and are git-ignored.
  Feature flags belong in config files, NOT in .env.

  Required variables:
    AWS_ACCOUNT_ID="123456789012"
    AWS_REGION="us-east-1"
    PROJECT_PREFIX="acme"

  Secrets (example):
    ANTHROPIC_API_KEY="sk-ant-..."
    SLACK_BOT_TOKEN="xoxb-..."
    SLACK_SIGNING_SECRET="..."

AWS Profile Management:
  The script automatically selects AWS profile based on target account.
  Profile mapping is configured in set_aws_profile_for_account().

  To add a new account mapping:
    1. Edit the case statement in set_aws_profile_for_account()
    2. Add: "ACCOUNT_ID") suggested_profile="profile-name" ;;

Exit Codes:
  0   Success
  1   Invalid arguments
  2   Missing dependencies
  3   AWS authentication failed
  4   Account mismatch
  5   Environment file missing
  6   Secrets push failed
  10  CDK deployment failed
  11  Health check failed
  20  User cancelled

EOF
}

# ============================================================================
# Argument Parsing
# ============================================================================

parse_arguments() {
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
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --slack-disabled)
                SLACK_ENABLED=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                echo "Dry run mode enabled - no changes will be made"
                shift
                ;;
            --force)
                FORCE=true
                echo "Force mode enabled"
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
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

    # Show help if requested or unknown options found
    if [ "$HELP" = true ]; then
        show_help
        exit $EXIT_SUCCESS
    fi
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_required_args() {
    local missing=()

    [ -z "${ENVIRONMENT:-}" ] && missing+=("ENVIRONMENT (-e)")
    [ -z "${CUSTOMER:-}" ] && missing+=("CUSTOMER (-c)")

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Error: Missing required parameters:"
        for var in "${missing[@]}"; do
            log_error "   - $var"
        done
        echo ""
        log_error "Run './deploy.sh --help' for usage information"
        exit $EXIT_INVALID_ARGS
    fi
}

validate_environment() {
    local env="$1"
    local valid=false

    for valid_env in $VALID_ENVIRONMENTS; do
        if [ "$env" = "$valid_env" ]; then
            valid=true
            break
        fi
    done

    if [ "$valid" = false ]; then
        log_error "Error: Invalid environment '$env'"
        log_error "Allowed values: $VALID_ENVIRONMENTS"
        exit $EXIT_INVALID_ARGS
    fi

    log_info "Environment '$env' is valid"
}

validate_dependencies() {
    log_info "Checking required tools..."

    # CUSTOMIZE: Add/remove required tools for your project
    local required_tools=("aws" "cdk" "jq")

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Error: Required tool '$tool' not found"
            log_error "Install $tool before running deployment"
            exit $EXIT_MISSING_DEPS
        fi
    done

    log_info "Required tools present"
}

validate_customer_env_file() {
    local customer="$1"
    # CUSTOMIZE: Adjust path pattern for your project
    local env_file=".env.${ENVIRONMENT}.${customer}"

    if [ ! -f "$env_file" ]; then
        log_error "Error: Customer environment file not found"
        log_error "   Expected: $env_file"
        echo ""
        log_error "Create from template:"
        log_error "   cp .env.TEMPLATE $env_file"
        log_error "   # Then edit with real credentials"
        echo ""
        log_error "Required variables:"
        # CUSTOMIZE: List required variables for your project
        log_error "   AWS_ACCOUNT_ID=\"your-account-id\""
        log_error "   AWS_REGION=\"us-east-1\""
        log_error "   PROJECT_PREFIX=\"project-prefix\""
        log_error "   ANTHROPIC_API_KEY=\"your-api-key\""
        exit $EXIT_ENV_FILE_MISSING
    fi

    if [ ! -r "$env_file" ]; then
        log_error "Error: Cannot read environment file: $env_file"
        exit $EXIT_ENV_FILE_MISSING
    fi

    log_info "Customer environment file exists: $env_file"
}

# ============================================================================
# AWS Profile Management
# ============================================================================

# CUSTOMIZE: Add your AWS account to profile mappings
set_aws_profile_for_account() {
    local target_account="$1"
    local suggested_profile=""

    # Map accounts to profiles
    case "$target_account" in
        # CUSTOMIZE: Add your account mappings here
        # "123456789012")
        #     suggested_profile="default"
        #     ;;
        # "987654321098")
        #     suggested_profile="production"
        #     ;;
        # "555555555555")
        #     suggested_profile="staging"
        #     ;;
        *)
            echo "Warning: Unknown AWS account: $target_account"
            echo "Using current profile. Verify manually with: aws sts get-caller-identity"
            return 0
            ;;
    esac

    if [ -n "$suggested_profile" ]; then
        export AWS_PROFILE="$suggested_profile"
        log_info "Setting AWS profile to '$suggested_profile' for account $target_account"

        # Verify profile works
        local current_account
        current_account=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
            log_error "Error: Failed to authenticate with profile '$suggested_profile'"
            log_error "Please run: aws configure --profile $suggested_profile"
            exit $EXIT_AWS_AUTH_FAILED
        }

        if [ "$current_account" != "$target_account" ]; then
            log_error "Error: Profile '$suggested_profile' is for account $current_account, not $target_account"
            log_error "Check your AWS profile configuration in ~/.aws/credentials"
            exit $EXIT_ACCOUNT_MISMATCH
        fi

        log_info "Successfully authenticated with account $target_account"
    fi
}

verify_aws_credentials() {
    log_info "Verifying AWS credentials..."

    local identity
    identity=$(aws sts get-caller-identity 2>/dev/null) || {
        log_error "Error: AWS credentials not configured or expired"
        log_error "Run 'aws configure' or refresh your SSO session"
        exit $EXIT_AWS_AUTH_FAILED
    }

    local account_id
    local arn
    account_id=$(echo "$identity" | jq -r '.Account')
    arn=$(echo "$identity" | jq -r '.Arn')

    log_info "   Account: $account_id"
    log_info "   Identity: $arn"
    log_info "AWS credentials verified"
}

verify_target_account() {
    local expected_account="$1"
    local current_account

    current_account=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
        log_error "Error: Cannot determine current AWS account"
        exit $EXIT_AWS_AUTH_FAILED
    }

    if [ "$current_account" != "$expected_account" ]; then
        echo ""
        echo "========================================"
        echo "  ACCOUNT MISMATCH DETECTED"
        echo "========================================"
        echo ""
        log_error "Expected account: $expected_account"
        log_error "Current account:  $current_account"
        echo ""
        log_error "Possible causes:"
        log_error "  1. Wrong AWS_PROFILE selected"
        log_error "  2. Customer environment file has wrong account ID"
        log_error "  3. AWS credentials configured for different account"
        echo ""
        log_error "Run 'aws sts get-caller-identity' to check your current credentials."
        exit $EXIT_ACCOUNT_MISMATCH
    fi

    log_info "Target account verified: $expected_account"
}

# ============================================================================
# Environment Loading
# ============================================================================

load_customer_environment() {
    local customer="$1"
    # CUSTOMIZE: Adjust path pattern for your project
    local env_file=".env.${ENVIRONMENT}.${customer}"

    log_info "Loading customer environment from: $env_file"

    # Source the file (exports variables)
    # shellcheck source=/dev/null
    source "$env_file"

    # CUSTOMIZE: Update required variables for your project
    local required_vars=("AWS_ACCOUNT_ID" "AWS_REGION" "PROJECT_PREFIX")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Error: Required variable '$var' not set in $env_file"
            exit $EXIT_ENV_FILE_MISSING
        fi
    done

    log_info "Customer environment loaded"
    log_info "   Account: $AWS_ACCOUNT_ID"
    log_info "   Region: $AWS_REGION"
    log_info "   Prefix: $PROJECT_PREFIX"
}

# ============================================================================
# CDK Bootstrap Check
# ============================================================================

ensure_cdk_bootstrap() {
    local account_id="$1"
    local region="$2"

    log_info "Checking CDK bootstrap status..."

    local stack_status
    stack_status=$(aws cloudformation describe-stacks \
        --stack-name CDKToolkit \
        --region "$region" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null) || stack_status="DOES_NOT_EXIST"

    case "$stack_status" in
        "CREATE_COMPLETE"|"UPDATE_COMPLETE")
            log_info "CDK already bootstrapped for $account_id/$region"
            ;;
        "DOES_NOT_EXIST"|"DELETE_COMPLETE")
            log_info "CDK not bootstrapped. Running bootstrap..."
            cdk bootstrap "aws://$account_id/$region" || {
                log_error "CDK bootstrap failed"
                exit $EXIT_CDK_FAILED
            }
            log_info "CDK bootstrap complete"
            ;;
        *)
            echo "CDKToolkit stack in unexpected state: $stack_status"
            echo "May need manual intervention"
            ;;
    esac
}

# ============================================================================
# Pending Operations Check
# ============================================================================

check_pending_operations() {
    log_info "Checking for pending CloudFormation operations..."

    local pending_stacks
    pending_stacks=$(aws cloudformation list-stacks \
        --stack-status-filter UPDATE_IN_PROGRESS CREATE_IN_PROGRESS DELETE_IN_PROGRESS \
        --query 'StackSummaries[].StackName' \
        --output text 2>/dev/null) || true

    if [ -n "$pending_stacks" ]; then
        echo ""
        echo "WARNING: Stacks with pending operations detected:"
        echo "$pending_stacks" | tr '\t' '\n' | while read -r stack; do
            [ -n "$stack" ] && echo "  - $stack"
        done
        echo ""
        echo "Options:"
        echo "  1. Wait for operations to complete"
        echo "  2. Cancel operations in CloudFormation console"
        echo "  3. Use --force flag to continue anyway (risky)"
        echo ""

        if [ "$FORCE" != true ]; then
            log_error "Aborting deployment. Use --force to continue anyway."
            exit $EXIT_CDK_FAILED
        fi
    else
        log_info "No pending CloudFormation operations"
    fi
}

# ============================================================================
# Production Confirmation
# ============================================================================

confirm_production_deployment() {
    local environment="$1"
    local customer="$2"

    if [ "$environment" = "prod" ]; then
        echo ""
        echo "========================================"
        echo "  PRODUCTION DEPLOYMENT CONFIRMATION"
        echo "========================================"
        echo ""
        echo "You are about to deploy to PRODUCTION"
        echo "  Customer: $customer"
        echo "  Environment: $environment"
        echo ""

        # Skip confirmation in CI environment
        if [ "${CI:-false}" = "true" ]; then
            echo "CI environment detected - skipping confirmation"
            return 0
        fi

        # Skip confirmation in dry run
        if [ "$DRY_RUN" = true ]; then
            return 0
        fi

        read -p "Type 'deploy' to confirm: " confirmation
        if [ "$confirmation" != "deploy" ]; then
            log_error "Deployment cancelled"
            exit $EXIT_USER_CANCELLED
        fi
        echo ""
    fi
}

# ============================================================================
# Secrets Management - Push .env secrets to AWS Secrets Manager
# ============================================================================

push_secrets_to_secrets_manager() {
    log_info "Pushing secrets from .env to AWS Secrets Manager..."

    # CUSTOMIZE: Add a setup-secrets.py script for your project, or use the
    # inline bash approach below. The Python approach is recommended for
    # projects with many secrets organized by purpose.

    # Option 1: Python script (recommended for complex projects)
    # if [ -f "scripts/setup-secrets.py" ]; then
    #     python scripts/setup-secrets.py "$ENVIRONMENT" "$CUSTOMER" || {
    #         log_error "Failed to push secrets to Secrets Manager"
    #         exit $EXIT_SECRETS_FAILED
    #     }
    #     log_info "Secrets pushed to Secrets Manager"
    #     return 0
    # fi

    # Option 2: Inline bash (for simpler projects)
    # CUSTOMIZE: Define your secret groups and their env var mappings
    local env_file=".env.${ENVIRONMENT}.${CUSTOMER}"

    # Example: Push API credentials
    local api_secret_name="${PROJECT_PREFIX}/${CUSTOMER}/api-credentials"
    local api_credentials="{}"

    # CUSTOMIZE: Add your secret key mappings
    # Build JSON from env vars loaded earlier
    # local api_key="${ANTHROPIC_API_KEY:-}"
    # if [ -n "$api_key" ]; then
    #     api_credentials=$(echo "$api_credentials" | jq --arg k "$api_key" '. + {"ANTHROPIC_API_KEY": $k}')
    # fi

    # Create or update the secret
    # if aws secretsmanager describe-secret --secret-id "$api_secret_name" --region "$AWS_REGION" >/dev/null 2>&1; then
    #     aws secretsmanager put-secret-value \
    #         --secret-id "$api_secret_name" \
    #         --secret-string "$api_credentials" \
    #         --region "$AWS_REGION" || {
    #             log_error "Failed to update secret: $api_secret_name"
    #             exit $EXIT_SECRETS_FAILED
    #         }
    #     log_info "Updated secret: $api_secret_name"
    # else
    #     aws secretsmanager create-secret \
    #         --name "$api_secret_name" \
    #         --secret-string "$api_credentials" \
    #         --description "API credentials for ${PROJECT_PREFIX} - ${ENVIRONMENT}/${CUSTOMER}" \
    #         --region "$AWS_REGION" || {
    #             log_error "Failed to create secret: $api_secret_name"
    #             exit $EXIT_SECRETS_FAILED
    #         }
    #     log_info "Created secret: $api_secret_name"
    # fi

    log_info "Secrets management complete"
}

# ============================================================================
# CDK Deployment
# ============================================================================

build_cdk_command() {
    local cmd="cdk deploy"

    # Add approval mode (CI-friendly)
    cmd+=" --require-approval never"

    # CUSTOMIZE: Add your CDK context variables
    cmd+=" -c environment=$ENVIRONMENT"
    cmd+=" -c customer=$CUSTOMER"
    cmd+=" -c accountId=$AWS_ACCOUNT_ID"
    cmd+=" -c region=$AWS_REGION"

    # Integration toggles
    if [ "$SLACK_ENABLED" = true ]; then
        cmd+=" -c slackEnabled=true"
    else
        cmd+=" -c slackEnabled=false"
    fi

    # CUSTOMIZE: Add additional integration toggles as needed
    # if [ "$LINDY_ENABLED" = true ]; then
    #     cmd+=" -c lindyEnabled=true"
    # fi

    # Add stack filter if provided
    if [ -n "${STACK_FILTER:-}" ]; then
        cmd+=" \"$STACK_FILTER\""
    else
        cmd+=" --all"
    fi

    echo "$cmd"
}

run_cdk_deploy() {
    log_info "Starting CDK deployment..."
    echo ""

    local cdk_cmd
    cdk_cmd=$(build_cdk_command)

    log_info "Command: $cdk_cmd"
    echo ""

    # Dry run mode - show command but don't execute
    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo "DRY RUN SUMMARY"
        echo "Would deploy to:"
        echo "  Environment: $ENVIRONMENT"
        echo "  Customer: $CUSTOMER"
        echo "  Account: $AWS_ACCOUNT_ID"
        echo "  Region: $AWS_REGION"
        echo ""
        echo "CDK command that would run:"
        echo "  $cdk_cmd"
        echo ""
        echo "Use without --dry-run to actually deploy"
        exit $EXIT_SUCCESS
    fi

    # Clean stale CDK artifacts
    rm -rf cdk.out/

    # Run deploy
    DEPLOYMENT_START_TIME=$(date +%s)

    if eval "$cdk_cmd"; then
        log_info ""
        log_info "CDK deployment completed"
        return 0
    else
        log_error ""
        log_error "CDK deployment failed"
        handle_deployment_failure "CDK deploy"
        exit $EXIT_CDK_FAILED
    fi
}

handle_deployment_failure() {
    local failed_component="$1"

    echo ""
    echo "========================================"
    echo "  DEPLOYMENT FAILED - ROLLBACK OPTIONS"
    echo "========================================"
    echo ""
    echo "The deployment failed on: $failed_component"
    echo ""
    echo "Automatic rollback:"
    echo "  CDK automatically rolls back failed stack updates."
    echo "  Check the CloudFormation console for stack status."
    echo ""
    echo "Manual rollback options:"
    echo "  1. Redeploy previous version:"
    echo "     git checkout <previous-commit>"
    echo "     ./deploy.sh -e $ENVIRONMENT -c $CUSTOMER"
    echo ""
    echo "  2. Check CloudFormation events for details:"
    echo "     aws cloudformation describe-stack-events --stack-name <stack-name>"
    echo ""
}

# ============================================================================
# Post-Deployment Verification
# ============================================================================

run_post_deployment_checks() {
    if [ "$SKIP_HEALTH_CHECK" = true ]; then
        log_info "Skipping post-deployment health checks (--skip-health-check)"
        return 0
    fi

    log_info "Running post-deployment health checks..."

    # CUSTOMIZE: Add your health check endpoints
    # Example: Lambda warm-up
    # local function_name="${PROJECT_PREFIX}-${ENVIRONMENT}-api"
    # log_info "Warming up Lambda function: $function_name"
    # if aws lambda invoke \
    #     --function-name "$function_name" \
    #     --payload '{"path": "/health", "httpMethod": "GET"}' \
    #     /dev/null > /dev/null 2>&1; then
    #     log_info "Lambda function warmed up successfully"
    # else
    #     log_error "Warning: Lambda warm-up failed"
    # fi

    # Example: API health check
    # if [ -n "${DOMAIN_NAME:-}" ]; then
    #     log_info "Checking API health endpoint..."
    #     local health_url="https://${DOMAIN_NAME}/health"
    #     if curl -sf "$health_url" > /dev/null 2>&1; then
    #         log_info "API health check passed"
    #     else
    #         log_error "Warning: API health check failed"
    #     fi
    # fi

    log_info "Post-deployment checks complete"
}

# ============================================================================
# Deployment Summary
# ============================================================================

show_deployment_summary() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - DEPLOYMENT_START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo ""
    echo "========================================"
    echo "  DEPLOYMENT COMPLETE"
    echo "========================================"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Customer: $CUSTOMER"
    echo "Account: $AWS_ACCOUNT_ID"
    echo "Region: $AWS_REGION"
    echo "Duration: ${minutes}m ${seconds}s"
    echo "Completed at: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "Deployment successful!"
    echo ""
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

run_preflight_checks() {
    log_info "Running pre-flight checks..."
    echo ""

    # Check required tools
    validate_dependencies

    # Validate arguments
    validate_required_args
    validate_environment "$ENVIRONMENT"

    # Check customer env file
    validate_customer_env_file "$CUSTOMER"

    echo ""
    log_info "All pre-flight checks passed"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    echo ""
    echo "========================================"
    echo "  ${PROJECT_NAME^^} DEPLOYMENT"
    echo "========================================"
    echo ""

    # Parse command line arguments
    parse_arguments "$@"

    # Phase 1: Pre-flight checks
    show_phase 1 "Pre-flight Checks" 7
    run_preflight_checks

    # Phase 2: Load environment
    show_phase 2 "Environment Setup" 7
    load_customer_environment "$CUSTOMER"

    # Phase 3: AWS profile and credentials
    show_phase 3 "AWS Authentication" 7
    set_aws_profile_for_account "$AWS_ACCOUNT_ID"
    verify_aws_credentials
    verify_target_account "$AWS_ACCOUNT_ID"

    # Phase 4: Pre-deployment checks
    show_phase 4 "Pre-deployment Checks" 7
    check_pending_operations
    ensure_cdk_bootstrap "$AWS_ACCOUNT_ID" "$AWS_REGION"
    confirm_production_deployment "$ENVIRONMENT" "$CUSTOMER"

    # Phase 5: Push secrets to AWS Secrets Manager
    show_phase 5 "Secrets Management" 7
    push_secrets_to_secrets_manager

    # Phase 6: CDK deployment
    show_phase 6 "CDK Deployment" 7
    run_cdk_deploy

    # Phase 7: Post-deployment verification
    show_phase 7 "Post-deployment Verification" 7
    run_post_deployment_checks

    return $EXIT_SUCCESS
}

# Run main with all arguments
main "$@"
