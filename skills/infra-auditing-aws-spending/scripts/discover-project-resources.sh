#!/bin/bash
#
# AWS Project Resource Discovery Script
# Discovers all AWS resources belonging to a specific project
#
# Usage: ./discover-project-resources.sh [OPTIONS]
#
# Options:
#   -p PREFIX    Resource name prefix (e.g., "myapp-prod")
#   -t TAG       Tag filter as Key=Value (e.g., "Project=myapp")
#   -s STACK     CloudFormation stack name pattern
#   -r REGION    AWS region (default: current region)
#   -o OUTPUT    Output file (default: ./project-resources.json)
#   -h           Show help
#
# Examples:
#   ./discover-project-resources.sh -p "myapp-prod"
#   ./discover-project-resources.sh -t "Project=myapp" -t "Environment=prod"
#   ./discover-project-resources.sh -s "MyApp*Stack"
#

set -euo pipefail

# Defaults
PREFIX=""
STACK_PATTERN=""
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo 'us-east-1')}"
OUTPUT_FILE="./project-resources.json"
declare -a TAGS=()

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while getopts "p:t:s:r:o:h" opt; do
  case $opt in
    p) PREFIX="$OPTARG" ;;
    t) TAGS+=("$OPTARG") ;;
    s) STACK_PATTERN="$OPTARG" ;;
    r) REGION="$OPTARG" ;;
    o) OUTPUT_FILE="$OPTARG" ;;
    h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -p PREFIX    Resource name prefix (e.g., 'myapp-prod')"
      echo "  -t TAG       Tag filter as Key=Value (can specify multiple)"
      echo "  -s STACK     CloudFormation stack name pattern"
      echo "  -r REGION    AWS region (default: current region)"
      echo "  -o OUTPUT    Output file (default: ./project-resources.json)"
      echo ""
      echo "Examples:"
      echo "  $0 -p 'myapp-prod'"
      echo "  $0 -t 'Project=myapp' -t 'Environment=prod'"
      echo "  $0 -s 'MyApp*Stack'"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Verify at least one filter provided
if [ -z "$PREFIX" ] && [ ${#TAGS[@]} -eq 0 ] && [ -z "$STACK_PATTERN" ]; then
  echo -e "${RED}Error: At least one filter (-p, -t, or -s) is required${NC}"
  echo "Use -h for help"
  exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AWS Project Resource Discovery                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Region:     ${GREEN}$REGION${NC}"
[ -n "$PREFIX" ] && echo -e "Prefix:     ${GREEN}$PREFIX${NC}"
[ ${#TAGS[@]} -gt 0 ] && echo -e "Tags:       ${GREEN}${TAGS[*]}${NC}"
[ -n "$STACK_PATTERN" ] && echo -e "Stack:      ${GREEN}$STACK_PATTERN${NC}"
echo -e "Output:     ${GREEN}$OUTPUT_FILE${NC}"
echo ""

# Initialize results
RESULTS='{}'

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

add_resources() {
  local resource_type="$1"
  local resources="$2"
  RESULTS=$(echo "$RESULTS" | jq --arg type "$resource_type" --argjson resources "$resources" '. + {($type): $resources}')
}

filter_by_prefix() {
  local json="$1"
  local name_field="$2"
  if [ -n "$PREFIX" ]; then
    echo "$json" | jq --arg prefix "$PREFIX" "[.[] | select($name_field | startswith(\$prefix))]"
  else
    echo "$json"
  fi
}

#------------------------------------------------------------------------------
# CloudFormation Stacks (if pattern provided)
#------------------------------------------------------------------------------

if [ -n "$STACK_PATTERN" ]; then
  echo -e "${YELLOW}Discovering CloudFormation stacks...${NC}"
  STACKS=$(aws cloudformation describe-stacks \
    --region "$REGION" \
    --query "Stacks[?contains(StackName, '${STACK_PATTERN//\*/}')].[StackName,StackStatus,CreationTime]" \
    --output json 2>/dev/null || echo '[]')

  STACK_COUNT=$(echo "$STACKS" | jq 'length')
  echo -e "  Found: ${GREEN}$STACK_COUNT stacks${NC}"

  # Get resources from matching stacks
  if [ "$STACK_COUNT" -gt 0 ]; then
    STACK_RESOURCES='[]'
    for stack_name in $(echo "$STACKS" | jq -r '.[].0' 2>/dev/null || echo "$STACKS" | jq -r '.[][0]'); do
      resources=$(aws cloudformation describe-stack-resources \
        --region "$REGION" \
        --stack-name "$stack_name" \
        --query 'StackResources[*].[ResourceType,LogicalResourceId,PhysicalResourceId,ResourceStatus]' \
        --output json 2>/dev/null || echo '[]')
      STACK_RESOURCES=$(echo "$STACK_RESOURCES $resources" | jq -s 'add')
    done
    add_resources "cloudformation_resources" "$STACK_RESOURCES"
  fi
fi

#------------------------------------------------------------------------------
# Lambda Functions
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering Lambda functions...${NC}"
LAMBDAS=$(aws lambda list-functions \
  --region "$REGION" \
  --query 'Functions[*].[FunctionName,Runtime,MemorySize,Timeout,LastModified]' \
  --output json 2>/dev/null || echo '[]')

LAMBDAS=$(filter_by_prefix "$LAMBDAS" '.[0]')

# Filter by tags if provided
if [ ${#TAGS[@]} -gt 0 ]; then
  FILTERED_LAMBDAS='[]'
  for func in $(echo "$LAMBDAS" | jq -r '.[0]' 2>/dev/null || echo "$LAMBDAS" | jq -r '.[][0]'); do
    [ -z "$func" ] || [ "$func" == "null" ] && continue
    func_tags=$(aws lambda list-tags --resource "arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):function:$func" --query 'Tags' --output json 2>/dev/null || echo '{}')

    match=true
    for tag in "${TAGS[@]}"; do
      key="${tag%%=*}"
      value="${tag#*=}"
      tag_value=$(echo "$func_tags" | jq -r --arg k "$key" '.[$k] // ""')
      if [ "$tag_value" != "$value" ]; then
        match=false
        break
      fi
    done

    if [ "$match" = true ]; then
      func_info=$(echo "$LAMBDAS" | jq --arg name "$func" '[.[] | select(.[0] == $name)][0]')
      FILTERED_LAMBDAS=$(echo "$FILTERED_LAMBDAS" | jq --argjson info "$func_info" '. + [$info]')
    fi
  done
  LAMBDAS="$FILTERED_LAMBDAS"
fi

LAMBDA_COUNT=$(echo "$LAMBDAS" | jq 'length')
echo -e "  Found: ${GREEN}$LAMBDA_COUNT functions${NC}"
add_resources "lambda_functions" "$LAMBDAS"

#------------------------------------------------------------------------------
# DynamoDB Tables
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering DynamoDB tables...${NC}"
TABLES=$(aws dynamodb list-tables \
  --region "$REGION" \
  --query 'TableNames' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  TABLES=$(echo "$TABLES" | jq --arg prefix "$PREFIX" '[.[] | select(startswith($prefix))]')
fi

TABLE_DETAILS='[]'
for table in $(echo "$TABLES" | jq -r '.[]'); do
  detail=$(aws dynamodb describe-table \
    --region "$REGION" \
    --table-name "$table" \
    --query 'Table.[TableName,TableStatus,ItemCount,TableSizeBytes,BillingModeSummary.BillingMode]' \
    --output json 2>/dev/null || echo '[]')
  TABLE_DETAILS=$(echo "$TABLE_DETAILS" | jq --argjson d "$detail" '. + [$d]')
done

TABLE_COUNT=$(echo "$TABLE_DETAILS" | jq 'length')
echo -e "  Found: ${GREEN}$TABLE_COUNT tables${NC}"
add_resources "dynamodb_tables" "$TABLE_DETAILS"

#------------------------------------------------------------------------------
# S3 Buckets
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering S3 buckets...${NC}"
BUCKETS=$(aws s3api list-buckets \
  --query 'Buckets[*].Name' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  BUCKETS=$(echo "$BUCKETS" | jq --arg prefix "$PREFIX" '[.[] | select(startswith($prefix))]')
fi

BUCKET_COUNT=$(echo "$BUCKETS" | jq 'length')
echo -e "  Found: ${GREEN}$BUCKET_COUNT buckets${NC}"
add_resources "s3_buckets" "$BUCKETS"

#------------------------------------------------------------------------------
# RDS Instances
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering RDS instances...${NC}"
RDS=$(aws rds describe-db-instances \
  --region "$REGION" \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,Engine,DBInstanceStatus,AllocatedStorage]' \
  --output json 2>/dev/null || echo '[]')

RDS=$(filter_by_prefix "$RDS" '.[0]')

RDS_COUNT=$(echo "$RDS" | jq 'length')
echo -e "  Found: ${GREEN}$RDS_COUNT instances${NC}"
add_resources "rds_instances" "$RDS"

#------------------------------------------------------------------------------
# ElastiCache Clusters
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering ElastiCache clusters...${NC}"
CACHE=$(aws elasticache describe-cache-clusters \
  --region "$REGION" \
  --query 'CacheClusters[*].[CacheClusterId,CacheNodeType,Engine,CacheClusterStatus,NumCacheNodes]' \
  --output json 2>/dev/null || echo '[]')

CACHE=$(filter_by_prefix "$CACHE" '.[0]')

CACHE_COUNT=$(echo "$CACHE" | jq 'length')
echo -e "  Found: ${GREEN}$CACHE_COUNT clusters${NC}"
add_resources "elasticache_clusters" "$CACHE"

#------------------------------------------------------------------------------
# API Gateway APIs
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering API Gateway APIs...${NC}"
APIS=$(aws apigatewayv2 get-apis \
  --region "$REGION" \
  --query 'Items[*].[Name,ApiId,ProtocolType,ApiEndpoint]' \
  --output json 2>/dev/null || echo '[]')

APIS=$(filter_by_prefix "$APIS" '.[0]')

# Also check REST APIs
REST_APIS=$(aws apigateway get-rest-apis \
  --region "$REGION" \
  --query 'items[*].[name,id,"REST"]' \
  --output json 2>/dev/null || echo '[]')

REST_APIS=$(filter_by_prefix "$REST_APIS" '.[0]')

ALL_APIS=$(echo "$APIS $REST_APIS" | jq -s 'add')
API_COUNT=$(echo "$ALL_APIS" | jq 'length')
echo -e "  Found: ${GREEN}$API_COUNT APIs${NC}"
add_resources "api_gateway" "$ALL_APIS"

#------------------------------------------------------------------------------
# EC2 Instances
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering EC2 instances...${NC}"

# Build tag filter
TAG_FILTERS=""
if [ ${#TAGS[@]} -gt 0 ]; then
  for tag in "${TAGS[@]}"; do
    key="${tag%%=*}"
    value="${tag#*=}"
    TAG_FILTERS="$TAG_FILTERS Name=tag:$key,Values=$value"
  done
fi

if [ -n "$TAG_FILTERS" ]; then
  EC2=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters $TAG_FILTERS \
    --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output json 2>/dev/null || echo '[]')
else
  EC2=$(aws ec2 describe-instances \
    --region "$REGION" \
    --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output json 2>/dev/null || echo '[]')
fi

EC2=$(echo "$EC2" | jq 'flatten(1)')

if [ -n "$PREFIX" ]; then
  EC2=$(echo "$EC2" | jq --arg prefix "$PREFIX" '[.[] | select(.[3] != null and (.[3] | startswith($prefix)))]')
fi

EC2_COUNT=$(echo "$EC2" | jq 'length')
echo -e "  Found: ${GREEN}$EC2_COUNT instances${NC}"
add_resources "ec2_instances" "$EC2"

#------------------------------------------------------------------------------
# ECS Clusters and Services
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering ECS clusters...${NC}"
ECS_CLUSTERS=$(aws ecs list-clusters \
  --region "$REGION" \
  --query 'clusterArns' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  ECS_CLUSTERS=$(echo "$ECS_CLUSTERS" | jq --arg prefix "$PREFIX" '[.[] | select(contains($prefix))]')
fi

ECS_COUNT=$(echo "$ECS_CLUSTERS" | jq 'length')
echo -e "  Found: ${GREEN}$ECS_COUNT clusters${NC}"
add_resources "ecs_clusters" "$ECS_CLUSTERS"

#------------------------------------------------------------------------------
# Step Functions
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering Step Functions...${NC}"
SFN=$(aws stepfunctions list-state-machines \
  --region "$REGION" \
  --query 'stateMachines[*].[name,stateMachineArn,type]' \
  --output json 2>/dev/null || echo '[]')

SFN=$(filter_by_prefix "$SFN" '.[0]')

SFN_COUNT=$(echo "$SFN" | jq 'length')
echo -e "  Found: ${GREEN}$SFN_COUNT state machines${NC}"
add_resources "step_functions" "$SFN"

#------------------------------------------------------------------------------
# SQS Queues
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering SQS queues...${NC}"
SQS=$(aws sqs list-queues \
  --region "$REGION" \
  --query 'QueueUrls' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  SQS=$(echo "$SQS" | jq --arg prefix "$PREFIX" '[.[] | select(contains($prefix))]')
fi

SQS_COUNT=$(echo "$SQS" | jq 'length')
echo -e "  Found: ${GREEN}$SQS_COUNT queues${NC}"
add_resources "sqs_queues" "$SQS"

#------------------------------------------------------------------------------
# SNS Topics
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering SNS topics...${NC}"
SNS=$(aws sns list-topics \
  --region "$REGION" \
  --query 'Topics[*].TopicArn' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  SNS=$(echo "$SNS" | jq --arg prefix "$PREFIX" '[.[] | select(contains($prefix))]')
fi

SNS_COUNT=$(echo "$SNS" | jq 'length')
echo -e "  Found: ${GREEN}$SNS_COUNT topics${NC}"
add_resources "sns_topics" "$SNS"

#------------------------------------------------------------------------------
# Secrets Manager
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering Secrets Manager secrets...${NC}"
SECRETS=$(aws secretsmanager list-secrets \
  --region "$REGION" \
  --query 'SecretList[*].[Name,ARN]' \
  --output json 2>/dev/null || echo '[]')

SECRETS=$(filter_by_prefix "$SECRETS" '.[0]')

SECRET_COUNT=$(echo "$SECRETS" | jq 'length')
echo -e "  Found: ${GREEN}$SECRET_COUNT secrets${NC}"
add_resources "secrets" "$SECRETS"

#------------------------------------------------------------------------------
# CloudWatch Log Groups
#------------------------------------------------------------------------------

echo -e "${YELLOW}Discovering CloudWatch Log Groups...${NC}"
LOGS=$(aws logs describe-log-groups \
  --region "$REGION" \
  --query 'logGroups[*].[logGroupName,storedBytes,retentionInDays]' \
  --output json 2>/dev/null || echo '[]')

if [ -n "$PREFIX" ]; then
  LOGS=$(echo "$LOGS" | jq --arg prefix "$PREFIX" '[.[] | select(.[0] | contains($prefix))]')
fi

LOG_COUNT=$(echo "$LOGS" | jq 'length')
echo -e "  Found: ${GREEN}$LOG_COUNT log groups${NC}"
add_resources "cloudwatch_logs" "$LOGS"

#------------------------------------------------------------------------------
# Summary & Output
#------------------------------------------------------------------------------

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Count totals
TOTAL=$(echo "$RESULTS" | jq '[.[] | length] | add')

echo -e "\nTotal resources discovered: ${GREEN}$TOTAL${NC}"
echo ""
echo "$RESULTS" | jq -r 'to_entries[] | "  \(.key): \(.value | length)"'

# Save to file
echo "$RESULTS" | jq '.' > "$OUTPUT_FILE"
echo ""
echo -e "Results saved to: ${GREEN}$OUTPUT_FILE${NC}"

# Generate resource IDs for filtering
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Resource IDs for Cost Filtering${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Lambda functions:"
echo "$RESULTS" | jq -r '.lambda_functions[]?[0] // empty' | head -5
[ $LAMBDA_COUNT -gt 5 ] && echo "  ... and $(($LAMBDA_COUNT - 5)) more"

echo ""
echo "DynamoDB tables:"
echo "$RESULTS" | jq -r '.dynamodb_tables[]?[0] // empty' | head -5

echo ""
echo "Use these resource names to filter Cost Explorer queries."
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
