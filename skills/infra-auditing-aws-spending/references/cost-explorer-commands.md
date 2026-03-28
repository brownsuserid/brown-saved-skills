# Cost Explorer CLI Command Reference

Complete reference for AWS Cost Explorer CLI commands used in spending audits.

## Prerequisites

```bash
# Required IAM permissions
# - ce:GetCostAndUsage
# - ce:GetCostAndUsageWithResources
# - ce:GetRightsizingRecommendation
# - ce:GetSavingsPlansPurchaseRecommendation
# - ce:GetSavingsPlansCoverage
# - ce:GetAnomalies
# - ce:GetAnomalyMonitors
```

---

## Basic Cost Queries

### Get Total Cost

```bash
# Total cost for a period
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost"

# Multiple metrics
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" "BlendedCost" "AmortizedCost" "UsageQuantity"
```

### Metrics Explained

| Metric | Description | When to Use |
|--------|-------------|-------------|
| UnblendedCost | Actual cost per resource | Single account analysis |
| BlendedCost | Averaged cost across org | Organization comparison |
| AmortizedCost | Spreads upfront costs | Commitment analysis |
| UsageQuantity | Resource consumption | Usage optimization |

---

## Grouping and Filtering

### Group by Service

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Group by Multiple Dimensions

```bash
# Service and region
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE Type=DIMENSION,Key=REGION
```

### Group by Tags

```bash
# By cost allocation tag
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=Project
```

### Available Dimensions

- `SERVICE` - AWS service name
- `REGION` - AWS region
- `LINKED_ACCOUNT` - Member account in org
- `USAGE_TYPE` - Resource usage type
- `INSTANCE_TYPE` - EC2 instance type
- `OPERATION` - API operation
- `PURCHASE_TYPE` - On-demand, Reserved, etc.

---

## Filtering Costs

### Filter by Service

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Elastic Compute Cloud - Compute", "Amazon RDS Service"]
    }
  }'
```

### Filter by Tag

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "Tags": {
      "Key": "Environment",
      "Values": ["production"]
    }
  }'
```

### Complex Filters

```bash
# AND filter
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "And": [
      {"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}},
      {"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}
    ]
  }'

# OR filter
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{
    "Or": [
      {"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}},
      {"Dimensions": {"Key": "REGION", "Values": ["us-west-2"]}}
    ]
  }'
```

---

## Granularity Options

### Daily Breakdown

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-08 \
  --granularity DAILY \
  --metrics "UnblendedCost"
```

### Hourly Breakdown (Last 14 days only)

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-20,End=2025-01-21 \
  --granularity HOURLY \
  --metrics "UnblendedCost"
```

---

## Cost Forecasting

### Forecast Next Month

```bash
aws ce get-cost-forecast \
  --time-period Start=$(date -d "first day of next month" +%Y-%m-%d),End=$(date -d "last day of next month" +%Y-%m-%d) \
  --granularity MONTHLY \
  --metric UNBLENDED_COST
```

### Forecast with Prediction Intervals

```bash
aws ce get-cost-forecast \
  --time-period Start=2025-02-01,End=2025-03-01 \
  --granularity MONTHLY \
  --metric UNBLENDED_COST \
  --prediction-interval-level 80
```

---

## Cost with Resources

### Get Resource-Level Costs

```bash
# Requires more permissions, limited to 14 days
aws ce get-cost-and-usage-with-resources \
  --time-period Start=2025-01-15,End=2025-01-22 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Elastic Compute Cloud - Compute"]
    }
  }' \
  --group-by Type=DIMENSION,Key=RESOURCE_ID
```

---

## Savings Plans Analysis

### Check Coverage

```bash
aws ce get-savings-plans-coverage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY
```

### Check Utilization

```bash
aws ce get-savings-plans-utilization \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY
```

### Get Recommendations

```bash
# Compute Savings Plan
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type "COMPUTE_SP" \
  --term-in-years "ONE_YEAR" \
  --payment-option "NO_UPFRONT" \
  --lookback-period-in-days "THIRTY_DAYS"

# EC2 Instance Savings Plan
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type "EC2_INSTANCE_SP" \
  --term-in-years "ONE_YEAR" \
  --payment-option "NO_UPFRONT" \
  --lookback-period-in-days "THIRTY_DAYS"
```

---

## Reserved Instance Analysis

### RI Coverage

```bash
aws ce get-reservation-coverage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY
```

### RI Utilization

```bash
aws ce get-reservation-utilization \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY
```

### RI Recommendations

```bash
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Elastic Compute Cloud - Compute" \
  --lookback-period-in-days "THIRTY_DAYS" \
  --term-in-years "ONE_YEAR" \
  --payment-option "NO_UPFRONT"
```

---

## Output Formatting

### Table Format

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output table
```

### JQ Queries for Processing

```bash
# Top 10 services by cost
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output json | jq -r '
    .ResultsByTime[].Groups
    | sort_by(.Metrics.UnblendedCost.Amount | tonumber)
    | reverse
    | .[0:10]
    | .[]
    | [.Keys[0], .Metrics.UnblendedCost.Amount]
    | @tsv'
```

### Query Specific Fields

```bash
# Just the total
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
  --output text
```

---

## Common Patterns

### Month-over-Month Comparison

```bash
# This month
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "first day of this month" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
  --output text

# Last month
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "first day of last month" +%Y-%m-%d),End=$(date -d "last day of last month" +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
  --output text
```

### Project Cost Attribution

```bash
# Requires consistent tagging with "Project" tag
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=Project \
  --filter '{
    "Tags": {
      "Key": "Project",
      "MatchOptions": ["PRESENT"]
    }
  }'
```

---

## Summary

| Task | Command |
|------|---------|
| Total cost | `get-cost-and-usage` with MONTHLY granularity |
| Cost by service | `get-cost-and-usage` grouped by SERVICE |
| Daily trend | `get-cost-and-usage` with DAILY granularity |
| Forecast | `get-cost-forecast` |
| Rightsizing | `get-rightsizing-recommendation` |
| Savings Plan recs | `get-savings-plans-purchase-recommendation` |
| RI analysis | `get-reservation-coverage/utilization` |
