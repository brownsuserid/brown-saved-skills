---
name: auditing-aws-spending
description: Audits AWS spending at project or account level using Cost Explorer, Budgets, Trusted Advisor, and Cost Anomaly Detection. Identifies waste, rightsizing opportunities, and cost optimization recommendations with prioritized savings.
---

# AWS Spending Audit Skill

This skill performs comprehensive AWS cost audits using native AWS cost management tools. It identifies idle resources, rightsizing opportunities, commitment savings, and cost anomalies to reduce cloud spend.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: Determine Audit Scope

**First, establish what you're auditing before any analysis.**

### Define Audit Type

Ask or determine: **Account-level** or **Project-level** audit?

| Type | Scope | When to Use |
|------|-------|-------------|
| Account-level | All services, all projects | Monthly reviews, new accounts |
| Project-level | Resources tagged to a specific project | Project cleanup, budget tracking |

### Verify AWS Access

```bash
# Verify AWS credentials and account
aws sts get-caller-identity

# Check which profile is active
echo "Profile: ${AWS_PROFILE:-default}"

# Test Cost Explorer access
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "7 days ago" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
  --output text
```

### Discover Cost Allocation Tags

**Cost allocation tags are essential for understanding where costs really come from.** Before any analysis, discover the tagging strategy — this applies to both account-level and project-level audits.

```bash
# Check what cost allocation tags are activated in the account
aws ce get-tags --time-period Start=$START_DATE,End=$END_DATE

# Look for tagging in CDK code
rg "Tags\.of\(|cdk\.Tags" --type ts
rg "tags\s*=" **/*.py | grep -i "customer\|product\|project\|environment\|cost"

# Look for tagging in Terraform
rg "tags\s*=" *.tf -A 3

# Check what tags exist on a known project resource
aws lambda list-tags --resource arn:aws:lambda:REGION:ACCOUNT:function:FUNCTION_NAME
```

**Key business dimension tags to look for:**
- `customer` - Which customer the resource serves (e.g., `customer=acme-corp`)
- `product` - Which product/application (e.g., `product=billing-api`)
- `Environment` - dev/staging/prod
- `Project` - Project identifier
- `CostCenter` - Financial tracking code

**Document discovered tags before proceeding — these will drive cost breakdowns in the report:**
```
# Business dimensions (use these for cost attribution)
CUSTOMER_TAG_KEY="customer"
PRODUCT_TAG_KEY="product"

# Project-level filtering (for project-scoped audits)
PROJECT_TAG_KEY="Project"
PROJECT_TAG_VALUE="myproject"
ENVIRONMENT="prod"
```

Understanding cost by customer and product is just as important as cost by service — a $5,000 EC2 bill means different things depending on whether it's one customer's ML pipeline or spread across 20 customers.

### Run Resource Discovery (Project Audits)

```bash
# Discover all project resources using tags
./scripts/discover-project-resources.sh -t "Project=myproject" -t "Environment=prod"

# Or by naming prefix if tags aren't consistent
./scripts/discover-project-resources.sh -p "myproject-prod"
```

**Output: `project-resources.json`** - Use this to focus subsequent phases.

### Set Time Range

```bash
START_DATE=$(date -d "30 days ago" +%Y-%m-%d)  # Standard: 30 days
END_DATE=$(date +%Y-%m-%d)
```

**Complete project discovery guide:** See `references/project-discovery.md`

---

## Phase 2: Analyze Overall Spend

Get high-level spending overview and trends.

**For project audits:** Add `--filter` with your project tags to all queries below.

### Total Cost Summary

```bash
# Account-level: total spend
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" "AmortizedCost"

# Project-level: filter by tag
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Tags":{"Key":"Project","Values":["myproject"]}}'
```

### Cost by Service

```bash
# Top services by cost (add --filter for project audits)
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[].Groups | []' \
  --output table
```

### Cost by Customer

Break down spend by customer tag to understand which customers drive the most cost. This is critical for unit economics and identifying customers whose infrastructure costs may exceed their revenue.

```bash
# Cost by customer tag
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=customer

# Cost by customer AND service (shows what each customer uses)
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=customer Type=DIMENSION,Key=SERVICE
```

### Cost by Product

Break down spend by product tag to understand cost per product line.

```bash
# Cost by product tag
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=product

# Cost by product AND service
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=product Type=DIMENSION,Key=SERVICE
```

### Untagged Spend

Resources without customer/product tags represent a visibility gap. Identify and flag them.

```bash
# Find untagged spend (resources missing the customer tag)
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=customer \
  --output json | jq '.ResultsByTime[].Groups[] | select(.Keys[0] == "customer$") | .Metrics.UnblendedCost.Amount'
```

If untagged spend is significant (>10% of total), flag it as a recommendation — untagged resources can't be attributed and create blind spots in cost management.

### Daily Spend Trend

```bash
# Daily costs to identify spikes
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[*].[TimePeriod.Start,Total.UnblendedCost.Amount]' \
  --output table
```

### Cost by Region

```bash
# Identify unexpected regional costs
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=REGION
```

**Complete analysis commands:** See `references/cost-explorer-commands.md`

---

## Phase 3: Identify Idle Resources

Find unused resources consuming budget.

**For project audits:** Filter by project tags or use resource IDs from `project-resources.json`.

### EC2 Idle Instances

```bash
# Find stopped instances still incurring costs (EBS volumes)
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=stopped" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,LaunchTime,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Check for instances with <5% CPU over 14 days (requires CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average
```

### Unattached EBS Volumes

```bash
# Find unattached volumes (100% waste)
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query 'Volumes[*].[VolumeId,Size,VolumeType,CreateTime]' \
  --output table
```

### Idle Load Balancers

```bash
# Find load balancers with no targets
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].[LoadBalancerName,DNSName,Type,State.Code]' \
  --output table

# Check target groups for empty ones
aws elbv2 describe-target-groups \
  --query 'TargetGroups[*].[TargetGroupName,TargetType]' \
  --output table
```

### Unassociated Elastic IPs

```bash
# Find unused Elastic IPs ($3.60/month each)
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==`null`].[PublicIp,AllocationId]' \
  --output table
```

### Orphaned CloudFormation Stacks

```bash
# Find stacks in failed or deprecated states
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE DELETE_FAILED \
  --query 'StackSummaries[*].[StackName,StackStatus,CreationTime,Description]' \
  --output table

# Check for stacks with "deprecated", "old", "temp", "test" in the name or description
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `deprecated`) || contains(StackName, `-old`) || contains(StackName, `-temp`)].[StackName,CreationTime]' \
  --output table
```

Orphaned stacks often contain multiple resources (Lambda, DynamoDB, SQS, SNS) that collectively waste significant budget. Deleting the stack removes all resources in one operation — much cleaner than finding them individually.

### SQS Dead Letter Queue Accumulation

```bash
# Check all queues for DLQ message accumulation
aws sqs list-queues --query 'QueueUrls' --output text | tr '\t' '\n' | while read url; do
  count=$(aws sqs get-queue-attributes --queue-url "$url" \
    --attribute-names ApproximateNumberOfMessagesVisible \
    --query 'Attributes.ApproximateNumberOfMessagesVisible' --output text)
  if [ "$count" -gt "0" ] 2>/dev/null; then
    echo "$url: $count messages"
  fi
done
```

DLQ accumulation doesn't directly cost much in SQS fees, but it signals failed processing that may indicate bigger problems (retried Lambda invocations, wasted compute). Flag any DLQ with >100 messages as an operational risk.

### CloudWatch Log Group Retention

```bash
# Find log groups with no retention policy (logs kept forever)
aws logs describe-log-groups \
  --query 'logGroups[?!retentionInDays].[logGroupName,storedBytes]' \
  --output table
```

Log groups without retention policies grow unbounded. For most Lambda functions, 14-30 days is sufficient. Flag log groups with no retention as a growing cost risk and recommend setting retention in CDK/IaC.

**Complete idle resource checks:** See `references/idle-resource-detection.md`

---

## Phase 4: Run Trusted Advisor Checks

Leverage AWS Trusted Advisor for automated recommendations.

### List Cost Optimization Checks

```bash
# List available cost checks (requires Business/Enterprise support)
aws trustedadvisor list-checks --pillar cost_optimizing \
  --query 'checkSummaries[*].[name,description]' \
  --output table 2>/dev/null || echo "Trusted Advisor API requires Business+ support"
```

### Get Cost Recommendations

```bash
# List all cost recommendations
aws trustedadvisor list-recommendations --pillar cost_optimizing \
  --query 'recommendationSummaries[*].[name,pillarSpecificAggregates.costOptimizing.estimatedMonthlySavings,status]' \
  --output table

# Get specific recommendation details
aws trustedadvisor get-recommendation \
  --recommendation-identifier <recommendation-arn>
```

### Key Trusted Advisor Checks

| Check | What It Finds |
|-------|---------------|
| Low Utilization EC2 | Instances with <10% CPU |
| Idle Load Balancers | ALB/NLB with no traffic |
| Underutilized EBS | Volumes with low IOPS |
| Unassociated EIPs | Unused Elastic IPs |
| Idle RDS Instances | Databases with no connections |

**Note:** Full Trusted Advisor requires Business or Enterprise Support plan.

---

## Phase 5: Analyze Rightsizing Opportunities

Find over-provisioned resources.

### EC2 Rightsizing Recommendations

```bash
# Get Compute Optimizer recommendations (if enabled)
aws compute-optimizer get-ec2-instance-recommendations \
  --query 'instanceRecommendations[*].[instanceArn,currentInstanceType,recommendationOptions[0].instanceType,recommendationOptions[0].projectedUtilizationMetrics]' \
  --output table

# Check Cost Explorer rightsizing recommendations
aws ce get-rightsizing-recommendation \
  --service "AmazonEC2" \
  --configuration '{"RecommendationTarget":"SAME_INSTANCE_FAMILY","BenefitsConsidered":true}'
```

### RDS Rightsizing

```bash
# Find oversized RDS instances
aws rds describe-db-instances \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,AllocatedStorage,Engine]' \
  --output table

# Check RDS CloudWatch for low CPU
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=mydb \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum
```

### Lambda Memory Optimization

```bash
# Check Lambda configurations
aws lambda list-functions \
  --query 'Functions[*].[FunctionName,MemorySize,Runtime,Timeout]' \
  --output table

# For each function, check actual memory usage via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name MaxMemoryUsed \
  --dimensions Name=FunctionName,Value=FUNCTION_NAME \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Maximum
```

Compare configured memory vs peak usage. Functions using <50% of allocated memory are candidates for rightsizing. Include a 50% headroom buffer above peak when recommending new sizes.

### DynamoDB Capacity Analysis

For tables using provisioned capacity, check whether provisioned throughput matches actual consumption.

```bash
# List all DynamoDB tables with billing mode
aws dynamodb list-tables --query 'TableNames' --output text | tr '\t' '\n' | while read table; do
  aws dynamodb describe-table --table-name "$table" \
    --query 'Table.[TableName,BillingModeSummary.BillingMode,ProvisionedThroughput.ReadCapacityUnits,ProvisionedThroughput.WriteCapacityUnits]' \
    --output text
done

# Check consumed vs provisioned capacity for a specific table
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=TABLE_NAME \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum
```

Tables with provisioned capacity utilization below 40% are candidates for auto-scaling or switching to on-demand mode. Don't forget to check GSI capacity too — GSIs are billed separately and often over-provisioned.

**Complete rightsizing guide:** See `references/rightsizing-strategies.md`

---

## Phase 6: Evaluate Commitment Savings

Analyze Savings Plans and Reserved Instance opportunities.

### Current Commitments

```bash
# List active Savings Plans
aws savingsplans describe-savings-plans \
  --query 'savingsPlans[*].[savingsPlanId,savingsPlanType,commitment,state]' \
  --output table

# List Reserved Instances
aws ec2 describe-reserved-instances \
  --query 'ReservedInstances[*].[ReservedInstancesId,InstanceType,InstanceCount,State,End]' \
  --output table
```

### Savings Plan Recommendations

```bash
# Get Savings Plan recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type "COMPUTE_SP" \
  --term-in-years "ONE_YEAR" \
  --payment-option "NO_UPFRONT" \
  --lookback-period-in-days "THIRTY_DAYS"
```

### Savings Plan Coverage

```bash
# Check current Savings Plan coverage
aws ce get-savings-plans-coverage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY
```

### Potential Savings Estimate

| Commitment Type | Typical Savings |
|-----------------|-----------------|
| Compute Savings Plan (1yr, No Upfront) | 20-30% |
| Compute Savings Plan (3yr, All Upfront) | 40-50% |
| EC2 Instance Savings Plan | 30-40% |
| Reserved Instances | 30-72% |

---

## Phase 7: Check Cost Anomaly Detection

Review anomalies and set up alerts.

### List Cost Anomalies

```bash
# Get recent anomalies
aws ce get-anomalies \
  --date-interval Start=$(date -d "30 days ago" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --query 'Anomalies[*].[AnomalyId,AnomalyStartDate,MonitorArn,Feedback]'
```

### Review Anomaly Monitors

```bash
# List active monitors
aws ce get-anomaly-monitors \
  --query 'AnomalyMonitors[*].[MonitorName,MonitorType,MonitorSpecification]' \
  --output table
```

### Create Anomaly Monitor (if missing)

See `references/cost-explorer-commands.md` for monitor creation commands.

---

## Phase 8: Validate and Report

### Validate Top Findings Against CDK (Project Audits)

**Before reporting, review CDK code for context on top savings opportunities:**

```bash
# Find resource definition and any sizing comments
rg "RESOURCE_NAME" --type ts --type py -B 3 -A 10

# Check for scheduled/event-driven patterns (explains "idle" resources)
rg "schedule|cron|events|rule" --type ts --type py
```

| Finding | Check CDK For | May Invalidate If |
|---------|---------------|-------------------|
| Oversized Lambda | Memory comments | Cold start requirements documented |
| Idle resource | Event triggers | Scheduled job or DR/failover |
| RDS rightsizing | Peak load notes | Sized for batch processing |

**Reject recommendations that conflict with documented architecture decisions.**

### Use Report Template

Generate report using: `templates/cost-audit-report.md`

### Prioritize Findings

| Priority | Criteria | Action Timeline |
|----------|----------|-----------------|
| Critical | >$500/month waste, security risk | Immediate |
| High | $100-500/month savings | This week |
| Medium | <$100/month, optimization | This sprint |
| Low | Best practice, minor savings | Backlog |

### Calculate Total Savings

Sum up identified savings:
- Idle resource termination
- Rightsizing recommendations
- Commitment discounts
- Storage tier optimization

---

## Supporting Files Reference

### AWS Cost Specific
- `references/cost-explorer-commands.md` - Complete CLI command reference
- `references/idle-resource-detection.md` - Finding unused resources
- `references/rightsizing-strategies.md` - Instance optimization guide
- `references/project-discovery.md` - Analyzing codebases for AWS resources
- `templates/cost-audit-report.md` - Audit findings template
- `scripts/cost-audit.sh` - Automated account-level audit script
- `scripts/discover-project-resources.sh` - Project resource discovery script

---

## Key Principles

- **Scope first:** Determine account vs project audit before analysis
- **Business dimensions matter most:** Always break down costs by customer and product tags — cost-by-service alone doesn't tell the full story
- **Tags are key:** Cost allocation tags (customer, product, Project, Environment) enable meaningful attribution
- **Use native AWS tools:** Cost Explorer, Trusted Advisor, Compute Optimizer
- **Filter by tags:** For project audits, filter all queries by project tags
- **Flag untagged spend:** Resources without customer/product tags are invisible costs — flag them
- **Automate detection:** Set up Cost Anomaly Detection alerts
- **Prioritize by impact:** Focus on highest-savings items first

## Success Criteria

- [ ] Audit scope defined (account vs project)
- [ ] AWS access verified
- [ ] (Project audit) Cost allocation tags identified
- [ ] (Project audit) Resource discovery script executed
- [ ] Total spend analyzed by service/region
- [ ] Cost broken down by customer tag
- [ ] Cost broken down by product tag
- [ ] Untagged spend identified and flagged
- [ ] Idle resources identified (filtered by tags if project audit)
- [ ] Trusted Advisor checks reviewed
- [ ] Rightsizing opportunities found
- [ ] Commitment coverage evaluated
- [ ] Anomaly detection configured
- [ ] Audit report generated with savings estimate

## When to Use This Skill

- **Monthly cost reviews** - Regular financial hygiene
- **Before budget planning** - Understand current baseline
- **After project completion** - Clean up unused resources
- **Unexpected bill increases** - Investigate anomalies
- **New account onboarding** - Establish cost controls

## Common Mistakes to Avoid

**Don't:**
- Delete resources without verifying they're unused
- Purchase commitments without analyzing usage patterns
- Ignore small costs (they add up)
- Skip tagging resources
- Rely solely on automated recommendations

**Do:**
- Verify resources are truly idle before termination
- Analyze 3+ months of data before commitments
- Set up budget alerts proactively
- Implement consistent tagging strategy
- Review findings with stakeholders before action
