#!/bin/bash
#
# AWS Cost Audit Script
# Performs automated cost analysis using AWS CLI
# Supports both account-level and project-level audits
#
# Usage: ./cost-audit.sh [OPTIONS]
#
# Options:
#   -d DAYS      Number of days to analyze (default: 30)
#   -p PROFILE   AWS profile to use (default: default)
#   -t TAG       Project tag filter as Key=Value (can specify multiple)
#   -o OUTPUT    Output directory (default: ./cost-audit-output)
#   -h           Show help
#
# Examples:
#   # Account-level audit
#   ./cost-audit.sh -d 30
#
#   # Project-level audit with tags
#   ./cost-audit.sh -t "Project=myapp" -t "Environment=prod"
#

set -euo pipefail

# Defaults
DAYS=30
PROFILE="${AWS_PROFILE:-default}"
OUTPUT_DIR="./cost-audit-output"
declare -a TAGS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while getopts "d:p:t:o:h" opt; do
  case $opt in
    d) DAYS="$OPTARG" ;;
    p) PROFILE="$OPTARG" ;;
    t) TAGS+=("$OPTARG") ;;
    o) OUTPUT_DIR="$OPTARG" ;;
    h)
      echo "Usage: $0 [-d DAYS] [-p PROFILE] [-t TAG] [-o OUTPUT_DIR]"
      echo ""
      echo "Options:"
      echo "  -d DAYS      Number of days to analyze (default: 30)"
      echo "  -p PROFILE   AWS profile to use (default: default)"
      echo "  -t TAG       Project tag filter as Key=Value (can specify multiple)"
      echo "  -o OUTPUT    Output directory (default: ./cost-audit-output)"
      echo ""
      echo "Examples:"
      echo "  # Account-level audit"
      echo "  $0 -d 30"
      echo ""
      echo "  # Project-level audit"
      echo "  $0 -t 'Project=myapp' -t 'Environment=prod'"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Determine audit type
if [ ${#TAGS[@]} -gt 0 ]; then
  AUDIT_TYPE="PROJECT"
else
  AUDIT_TYPE="ACCOUNT"
fi

# Build Cost Explorer filter from tags
build_ce_filter() {
  if [ ${#TAGS[@]} -eq 0 ]; then
    echo ""
    return
  fi

  if [ ${#TAGS[@]} -eq 1 ]; then
    local key="${TAGS[0]%%=*}"
    local value="${TAGS[0]#*=}"
    echo "--filter {\"Tags\":{\"Key\":\"$key\",\"Values\":[\"$value\"]}}"
  else
    # Multiple tags - use And filter
    local filters=""
    for tag in "${TAGS[@]}"; do
      local key="${tag%%=*}"
      local value="${tag#*=}"
      if [ -n "$filters" ]; then
        filters="$filters,"
      fi
      filters="$filters{\"Tags\":{\"Key\":\"$key\",\"Values\":[\"$value\"]}}"
    done
    echo "--filter {\"And\":[$filters]}"
  fi
}

# Build EC2 tag filter for describe commands
build_ec2_tag_filter() {
  if [ ${#TAGS[@]} -eq 0 ]; then
    echo ""
    return
  fi

  local filters=""
  for tag in "${TAGS[@]}"; do
    local key="${tag%%=*}"
    local value="${tag#*=}"
    filters="$filters Name=tag:$key,Values=$value"
  done
  echo "$filters"
}

CE_FILTER=$(build_ce_filter)
EC2_TAG_FILTER=$(build_ec2_tag_filter)

# Calculate date range
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  START_DATE=$(date -v-${DAYS}d +%Y-%m-%d)
  END_DATE=$(date +%Y-%m-%d)
else
  # Linux
  START_DATE=$(date -d "$DAYS days ago" +%Y-%m-%d)
  END_DATE=$(date +%Y-%m-%d)
fi

# Setup
export AWS_PROFILE="$PROFILE"
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              AWS Cost Audit Script                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Audit Type: ${GREEN}$AUDIT_TYPE${NC}"
echo -e "Profile:    ${GREEN}$PROFILE${NC}"
echo -e "Period:     ${GREEN}$START_DATE to $END_DATE${NC}"
[ ${#TAGS[@]} -gt 0 ] && echo -e "Tags:       ${GREEN}${TAGS[*]}${NC}"
echo -e "Output:     ${GREEN}$OUTPUT_DIR${NC}"
echo ""

# Verify AWS access
echo -e "${YELLOW}Verifying AWS access...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
  echo -e "${RED}Error: Unable to access AWS. Check credentials.${NC}"
  exit 1
}
echo -e "Account:    ${GREEN}$ACCOUNT_ID${NC}"
echo ""

# Save audit metadata
cat > "$OUTPUT_DIR/audit-metadata.json" << EOF
{
  "audit_type": "$AUDIT_TYPE",
  "account_id": "$ACCOUNT_ID",
  "profile": "$PROFILE",
  "start_date": "$START_DATE",
  "end_date": "$END_DATE",
  "days": $DAYS,
  "tags": [$(printf '"%s",' "${TAGS[@]}" | sed 's/,$//')]
}
EOF

#------------------------------------------------------------------------------
# Section 1: Overall Spending
#------------------------------------------------------------------------------
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Section 1: Spending Analysis${NC}"
[ "$AUDIT_TYPE" == "PROJECT" ] && echo -e "${BLUE}           (Filtered by project tags)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Fetching total cost..."
if [ -n "$CE_FILTER" ]; then
  eval aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    $CE_FILTER \
    > "$OUTPUT_DIR/total-cost.json"
else
  aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    > "$OUTPUT_DIR/total-cost.json"
fi

TOTAL_COST=$(jq -r '.ResultsByTime[].Total.UnblendedCost.Amount // 0' "$OUTPUT_DIR/total-cost.json" | awk '{sum+=$1} END {printf "%.2f", sum}')
echo -e "Total spend: ${GREEN}\$${TOTAL_COST}${NC}"

echo "Fetching cost by service..."
if [ -n "$CE_FILTER" ]; then
  eval aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --group-by Type=DIMENSION,Key=SERVICE \
    $CE_FILTER \
    > "$OUTPUT_DIR/cost-by-service.json"
else
  aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --group-by Type=DIMENSION,Key=SERVICE \
    > "$OUTPUT_DIR/cost-by-service.json"
fi

echo -e "\nTop 10 Services by Cost:"
jq -r '.ResultsByTime[].Groups[]? | [.Keys[0], .Metrics.UnblendedCost.Amount] | @tsv' "$OUTPUT_DIR/cost-by-service.json" 2>/dev/null | \
  sort -t$'\t' -k2 -rn | head -10 | \
  awk -F'\t' '{printf "  %-50s $%8.2f\n", $1, $2}' || echo "  No service breakdown available"

echo "Fetching cost by region..."
if [ -n "$CE_FILTER" ]; then
  eval aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --group-by Type=DIMENSION,Key=REGION \
    $CE_FILTER \
    > "$OUTPUT_DIR/cost-by-region.json"
else
  aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --group-by Type=DIMENSION,Key=REGION \
    > "$OUTPUT_DIR/cost-by-region.json"
fi

#------------------------------------------------------------------------------
# Section 2: Idle Resources
#------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Section 2: Idle Resource Detection${NC}"
[ "$AUDIT_TYPE" == "PROJECT" ] && echo -e "${BLUE}           (Filtered by project tags)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Stopped EC2 instances
echo "Checking for stopped EC2 instances..."
if [ -n "$EC2_TAG_FILTER" ]; then
  eval aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=stopped" $EC2_TAG_FILTER \
    --query "'Reservations[*].Instances[*].[InstanceId,InstanceType,Tags[?Key==\`Name\`].Value|[0]]'" \
    --output json > "$OUTPUT_DIR/stopped-instances.json"
else
  aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=stopped" \
    --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,Tags[?Key==`Name`].Value|[0]]' \
    --output json > "$OUTPUT_DIR/stopped-instances.json"
fi

STOPPED_COUNT=$(jq 'flatten | length' "$OUTPUT_DIR/stopped-instances.json")
echo -e "Stopped EC2 instances: ${YELLOW}$STOPPED_COUNT${NC}"

# Unattached EBS volumes (filter by tags if project audit)
echo "Checking for unattached EBS volumes..."
if [ -n "$EC2_TAG_FILTER" ]; then
  eval aws ec2 describe-volumes \
    --filters "Name=status,Values=available" $EC2_TAG_FILTER \
    --query "'Volumes[*].[VolumeId,Size,VolumeType]'" \
    --output json > "$OUTPUT_DIR/unattached-volumes.json"
else
  aws ec2 describe-volumes \
    --filters "Name=status,Values=available" \
    --query 'Volumes[*].[VolumeId,Size,VolumeType]' \
    --output json > "$OUTPUT_DIR/unattached-volumes.json"
fi

UNATTACHED_COUNT=$(jq 'length' "$OUTPUT_DIR/unattached-volumes.json")
UNATTACHED_SIZE=$(jq '[.[]?[1]] | add // 0' "$OUTPUT_DIR/unattached-volumes.json")
UNATTACHED_COST=$(echo "$UNATTACHED_SIZE * 0.08" | bc)
echo -e "Unattached EBS volumes: ${YELLOW}$UNATTACHED_COUNT${NC} (${UNATTACHED_SIZE} GB, ~\$${UNATTACHED_COST}/month)"

# Unused Elastic IPs (filter by tags if project audit)
echo "Checking for unused Elastic IPs..."
if [ -n "$EC2_TAG_FILTER" ]; then
  eval aws ec2 describe-addresses \
    --filters $EC2_TAG_FILTER \
    --query "'Addresses[?AssociationId==\`null\`].[PublicIp,AllocationId]'" \
    --output json > "$OUTPUT_DIR/unused-eips.json"
else
  aws ec2 describe-addresses \
    --query 'Addresses[?AssociationId==`null`].[PublicIp,AllocationId]' \
    --output json > "$OUTPUT_DIR/unused-eips.json"
fi

UNUSED_EIP_COUNT=$(jq 'length' "$OUTPUT_DIR/unused-eips.json")
UNUSED_EIP_COST=$(echo "$UNUSED_EIP_COUNT * 3.60" | bc)
echo -e "Unused Elastic IPs: ${YELLOW}$UNUSED_EIP_COUNT${NC} (~\$${UNUSED_EIP_COST}/month)"

# Load balancers
echo "Checking load balancers..."
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].[LoadBalancerName,Type,State.Code]' \
  --output json > "$OUTPUT_DIR/load-balancers.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/load-balancers.json"

# Filter load balancers by tag if project audit
if [ "$AUDIT_TYPE" == "PROJECT" ] && [ ${#TAGS[@]} -gt 0 ]; then
  # Get LB ARNs and filter by tags
  LB_ARNS=$(jq -r '.[0]?' "$OUTPUT_DIR/load-balancers.json" 2>/dev/null || echo "")
  # Note: Full LB tag filtering requires additional API calls - showing all for now
  echo -e "${YELLOW}Note: Load balancer tag filtering requires manual review${NC}"
fi

LB_COUNT=$(jq 'length' "$OUTPUT_DIR/load-balancers.json")
echo -e "Load balancers found: ${GREEN}$LB_COUNT${NC} (manual review recommended)"

#------------------------------------------------------------------------------
# Section 3: Rightsizing Recommendations
#------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Section 3: Rightsizing Recommendations${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Fetching EC2 rightsizing recommendations..."
aws ce get-rightsizing-recommendation \
  --service "AmazonEC2" \
  --configuration '{"RecommendationTarget":"SAME_INSTANCE_FAMILY","BenefitsConsidered":true}' \
  > "$OUTPUT_DIR/rightsizing-recommendations.json" 2>/dev/null || echo '{"RightsizingRecommendations":[]}' > "$OUTPUT_DIR/rightsizing-recommendations.json"

# Filter rightsizing recommendations by project tags if applicable
if [ "$AUDIT_TYPE" == "PROJECT" ] && [ ${#TAGS[@]} -gt 0 ]; then
  # Get instance IDs from project resources if available
  if [ -f "./project-resources.json" ]; then
    PROJECT_INSTANCES=$(jq -r '.ec2_instances[]?[0] // empty' ./project-resources.json 2>/dev/null | tr '\n' '|' | sed 's/|$//')
    if [ -n "$PROJECT_INSTANCES" ]; then
      jq --arg instances "$PROJECT_INSTANCES" '
        .RightsizingRecommendations |= [.[] | select(.CurrentInstance.ResourceId | test($instances))]
      ' "$OUTPUT_DIR/rightsizing-recommendations.json" > "$OUTPUT_DIR/rightsizing-recommendations-filtered.json"
      mv "$OUTPUT_DIR/rightsizing-recommendations-filtered.json" "$OUTPUT_DIR/rightsizing-recommendations.json"
    fi
  fi
fi

RIGHTSIZE_COUNT=$(jq '.RightsizingRecommendations | length' "$OUTPUT_DIR/rightsizing-recommendations.json")
echo -e "Rightsizing recommendations: ${YELLOW}$RIGHTSIZE_COUNT${NC}"

if [ "$RIGHTSIZE_COUNT" -gt 0 ]; then
  echo -e "\nTop recommendations:"
  jq -r '.RightsizingRecommendations[:5][] | "  \(.CurrentInstance.ResourceId): \(.CurrentInstance.InstanceType) -> \(.ModifyRecommendationDetail.TargetInstances[0].ResourceDetails.EC2ResourceDetails.InstanceType // "Terminate")"' "$OUTPUT_DIR/rightsizing-recommendations.json" 2>/dev/null || true
fi

#------------------------------------------------------------------------------
# Section 4: Savings Plans Analysis
#------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Section 4: Savings Plans Analysis${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "Checking current Savings Plans..."
aws savingsplans describe-savings-plans \
  --query 'savingsPlans[*].[savingsPlanId,savingsPlanType,commitment,state]' \
  --output json > "$OUTPUT_DIR/savings-plans.json" 2>/dev/null || echo '[]' > "$OUTPUT_DIR/savings-plans.json"

SP_COUNT=$(jq 'length' "$OUTPUT_DIR/savings-plans.json")
echo -e "Active Savings Plans: ${GREEN}$SP_COUNT${NC}"

echo "Fetching Savings Plan recommendations..."
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type "COMPUTE_SP" \
  --term-in-years "ONE_YEAR" \
  --payment-option "NO_UPFRONT" \
  --lookback-period-in-days "THIRTY_DAYS" \
  > "$OUTPUT_DIR/sp-recommendations.json" 2>/dev/null || echo '{}' > "$OUTPUT_DIR/sp-recommendations.json"

#------------------------------------------------------------------------------
# Section 5: Lambda Analysis (for project audits)
#------------------------------------------------------------------------------
if [ "$AUDIT_TYPE" == "PROJECT" ]; then
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}Section 5: Lambda Function Analysis${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  # Get Lambda functions from project-resources.json if available
  if [ -f "./project-resources.json" ]; then
    echo "Analyzing Lambda functions from project resources..."
    LAMBDA_FUNCTIONS=$(jq -r '.lambda_functions[]?[0] // empty' ./project-resources.json 2>/dev/null)

    if [ -n "$LAMBDA_FUNCTIONS" ]; then
      echo "$LAMBDA_FUNCTIONS" | while read -r func; do
        [ -z "$func" ] && continue
        config=$(aws lambda get-function-configuration --function-name "$func" --query '[FunctionName,MemorySize,Timeout,Runtime]' --output json 2>/dev/null || echo '[]')
        echo "  $func: $(echo "$config" | jq -r '.[1]')MB, $(echo "$config" | jq -r '.[2]')s timeout"
      done | head -10

      LAMBDA_COUNT=$(echo "$LAMBDA_FUNCTIONS" | wc -l | tr -d ' ')
      echo -e "\nTotal Lambda functions: ${GREEN}$LAMBDA_COUNT${NC}"
    else
      echo "No Lambda functions found in project-resources.json"
    fi
  else
    echo -e "${YELLOW}Run discover-project-resources.sh first for Lambda analysis${NC}"
  fi
fi

#------------------------------------------------------------------------------
# Summary
#------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

IDLE_WASTE=$(echo "$UNATTACHED_COST + $UNUSED_EIP_COST" | bc)

echo ""
echo -e "Audit Type: ${GREEN}$AUDIT_TYPE${NC}"
[ "$AUDIT_TYPE" == "PROJECT" ] && echo -e "Project Tags: ${GREEN}${TAGS[*]}${NC}"
echo -e "Total Spend (${DAYS} days): ${GREEN}\$$TOTAL_COST${NC}"
echo -e "Identified Idle Resource Waste: ${YELLOW}\$$IDLE_WASTE/month${NC}"
echo ""
echo -e "Findings:"
echo -e "  - Stopped EC2 instances: $STOPPED_COUNT"
echo -e "  - Unattached EBS volumes: $UNATTACHED_COUNT ($UNATTACHED_SIZE GB)"
echo -e "  - Unused Elastic IPs: $UNUSED_EIP_COUNT"
echo -e "  - Rightsizing opportunities: $RIGHTSIZE_COUNT"
echo ""
echo -e "Output files saved to: ${GREEN}$OUTPUT_DIR/${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Review the JSON files in $OUTPUT_DIR for detailed findings."
echo -e "Use the cost-audit-report.md template to create a formal report."
if [ "$AUDIT_TYPE" == "PROJECT" ]; then
  echo -e "${YELLOW}Remember: Validate findings against CDK code before acting.${NC}"
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
