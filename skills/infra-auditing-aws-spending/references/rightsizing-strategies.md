# Rightsizing Strategies Guide

Comprehensive guide for identifying and implementing rightsizing opportunities across AWS services.

## Overview

Rightsizing matches instance types and sizes to actual workload requirements. AWS reports that rightsizing alone can reduce costs by 20-40% for many organizations.

---

## EC2 Rightsizing

### AWS Compute Optimizer

AWS Compute Optimizer analyzes utilization metrics and provides recommendations.

```bash
# Check if Compute Optimizer is enabled
aws compute-optimizer get-enrollment-status

# Enable Compute Optimizer (if not enabled)
aws compute-optimizer update-enrollment-status --status Active

# Get EC2 recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --query 'instanceRecommendations[*].[
    instanceArn,
    currentInstanceType,
    finding,
    recommendationOptions[0].instanceType,
    recommendationOptions[0].projectedUtilizationMetrics
  ]' \
  --output table
```

### Cost Explorer Rightsizing

```bash
# EC2 rightsizing recommendations
aws ce get-rightsizing-recommendation \
  --service "AmazonEC2" \
  --configuration '{
    "RecommendationTarget": "SAME_INSTANCE_FAMILY",
    "BenefitsConsidered": true
  }' \
  --query 'RightsizingRecommendations[*].[
    CurrentInstance.ResourceId,
    CurrentInstance.InstanceType,
    RightsizingType,
    ModifyRecommendationDetail.TargetInstances[0].ResourceDetails.EC2ResourceDetails.InstanceType,
    ModifyRecommendationDetail.TargetInstances[0].EstimatedMonthlySavings
  ]'
```

### Manual Analysis

```bash
# Get instance utilization metrics
INSTANCE_ID="i-0123456789abcdef0"

# CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -d "30 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum p99

# Memory utilization (requires CloudWatch agent)
aws cloudwatch get-metric-statistics \
  --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum
```

### Rightsizing Thresholds

| Metric | Oversized If | Consider |
|--------|--------------|----------|
| CPU Average | < 20% | Downsize |
| CPU Maximum | < 40% | Downsize |
| Memory Average | < 30% | Downsize |
| Network | < 20% capacity | Downsize |

### Instance Family Transitions

| Current | Recommended Alternative | Savings |
|---------|------------------------|---------|
| m5.large | m5.medium | 50% |
| m5.xlarge | m6i.large | 15-20% |
| c5.xlarge | c6i.large | 10-15% |
| r5.xlarge | r6i.large | 10-15% |
| Any Intel | Graviton (m6g, c6g, r6g) | 20-40% |

---

## Graviton Migration

Graviton (ARM) instances offer 20-40% better price-performance.

### Compatibility Check

```bash
# List current instance types
aws ec2 describe-instances \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,Platform]' \
  --output table
```

### Graviton Equivalents

| Intel/AMD | Graviton | Savings |
|-----------|----------|---------|
| m5.large | m6g.large | ~20% |
| c5.xlarge | c6g.xlarge | ~20% |
| r5.2xlarge | r6g.2xlarge | ~20% |
| t3.medium | t4g.medium | ~20% |

### Migration Considerations

**Compatible workloads:**
- Python, Node.js, Go, Rust
- Java 11+ (check JDK compatibility)
- .NET Core 3.1+, .NET 5+
- Containerized workloads

**Requires testing:**
- Native binaries (must be ARM-compiled)
- Java < 11
- Windows workloads (not supported)
- x86-specific optimizations

---

## RDS Rightsizing

### Get Current Utilization

```bash
DB_IDENTIFIER="mydb"

# CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_IDENTIFIER \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum

# Memory usage (Freeable Memory)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_IDENTIFIER \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Minimum

# Connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_IDENTIFIER \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum
```

### RDS Rightsizing Matrix

| Current | If CPU < 20%, Memory > 50% free | Savings |
|---------|--------------------------------|---------|
| db.r5.large | db.r5.medium or db.t3.medium | 50% |
| db.r5.xlarge | db.r5.large | 50% |
| db.m5.large | db.t3.medium | 40-60% |

### Consider Aurora Serverless v2

For variable workloads, Aurora Serverless v2 scales automatically:

```bash
# Check if workload is variable (high variance)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_IDENTIFIER \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Minimum Maximum \
  --query 'Datapoints | {min: min_by(@, &Minimum).Minimum, max: max_by(@, &Maximum).Maximum}'
```

If max/min ratio > 4:1, consider serverless.

---

## Lambda Rightsizing

Lambda pricing is based on memory * duration.

### Find Over-Provisioned Functions

```bash
# List functions with high memory
aws lambda list-functions \
  --query 'Functions[?MemorySize>`512`].[FunctionName,MemorySize,Timeout]' \
  --output table
```

### Analyze Memory Usage

```bash
FUNCTION_NAME="my-function"

# Get duration metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum p99
```

### Lambda Power Tuning

Use AWS Lambda Power Tuning tool to find optimal memory:
- https://github.com/alexcasalboni/aws-lambda-power-tuning

### Memory/Duration Trade-offs

| Memory | CPU | Typical Use Case |
|--------|-----|------------------|
| 128 MB | Minimal | Simple transformations |
| 256-512 MB | 0.25-0.5 vCPU | API handlers |
| 1024 MB | 0.5 vCPU | Data processing |
| 2048 MB | 1 vCPU | Heavy compute |
| 3008+ MB | 2+ vCPU | ML inference |

---

## EBS Volume Rightsizing

### Check Volume Types

```bash
# List volumes with type and performance
aws ec2 describe-volumes \
  --query 'Volumes[*].[
    VolumeId,
    VolumeType,
    Size,
    Iops,
    Throughput,
    State,
    Attachments[0].InstanceId
  ]' \
  --output table
```

### Volume Type Comparison

| Type | IOPS | Throughput | Cost/GB | Best For |
|------|------|------------|---------|----------|
| gp3 | 3,000 base | 125 MB/s | $0.08 | General purpose |
| gp2 | 3 per GB | Varies | $0.10 | Legacy |
| io2 | Up to 64,000 | 1,000 MB/s | $0.125+ | High IOPS |
| st1 | 500 | 500 MB/s | $0.045 | Throughput |
| sc1 | 250 | 250 MB/s | $0.015 | Cold storage |

### Migration from gp2 to gp3

gp3 is almost always cheaper with better performance.

```bash
# Find gp2 volumes to migrate
aws ec2 describe-volumes \
  --filters "Name=volume-type,Values=gp2" \
  --query 'Volumes[*].[VolumeId,Size,Iops]' \
  --output table

# Modify to gp3
aws ec2 modify-volume \
  --volume-id vol-xxx \
  --volume-type gp3 \
  --iops 3000 \
  --throughput 125
```

---

## ElastiCache Rightsizing

```bash
# List cache clusters
aws elasticache describe-cache-clusters \
  --query 'CacheClusters[*].[
    CacheClusterId,
    CacheNodeType,
    Engine,
    NumCacheNodes
  ]' \
  --output table

# Check memory utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name DatabaseMemoryUsagePercentage \
  --dimensions Name=CacheClusterId,Value=mycluster \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum
```

If memory usage < 30%, consider downsizing.

---

## Implementation Best Practices

### Before Rightsizing

1. **Analyze 2-4 weeks of data** - Don't make decisions on short periods
2. **Check for peak usage** - Consider batch jobs, monthly reports
3. **Test in non-production first** - Validate performance
4. **Have rollback plan** - Know how to upsize quickly

### Safe Rightsizing Process

```bash
# 1. Create snapshot/backup
aws ec2 create-image --instance-id i-xxx --name "pre-rightsize-backup"

# 2. Stop instance
aws ec2 stop-instances --instance-ids i-xxx

# 3. Change instance type
aws ec2 modify-instance-attribute \
  --instance-id i-xxx \
  --instance-type "{\"Value\": \"t3.medium\"}"

# 4. Start instance
aws ec2 start-instances --instance-ids i-xxx

# 5. Monitor for 24-48 hours
# 6. Roll back if issues
```

### Automation

Use AWS Instance Scheduler for non-production:
- Stop dev/test instances outside business hours
- 65%+ savings for 8x5 workloads

---

## Summary

| Service | Tool | Potential Savings |
|---------|------|------------------|
| EC2 | Compute Optimizer | 20-40% |
| EC2 | Graviton migration | 20-40% |
| RDS | Manual analysis | 30-50% |
| Lambda | Power Tuning | 10-40% |
| EBS | gp2 to gp3 | 10-20% |
| ElastiCache | Manual analysis | 30-50% |
