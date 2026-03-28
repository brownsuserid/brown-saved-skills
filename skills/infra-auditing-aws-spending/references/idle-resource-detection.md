# Idle Resource Detection Guide

Comprehensive guide for finding unused AWS resources that are consuming budget.

## Overview

Studies show 20-30% of cloud spending is wasted on idle or over-provisioned resources. This guide covers systematic detection across common AWS services.

---

## EC2 Instances

### Stopped Instances

Stopped instances still incur costs for:
- EBS volumes attached
- Elastic IP addresses (if associated but not running)
- Reserved Instance coverage (wasted)

```bash
# Find stopped instances
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=stopped" \
  --query 'Reservations[*].Instances[*].[
    InstanceId,
    InstanceType,
    LaunchTime,
    StateTransitionReason,
    Tags[?Key==`Name`].Value|[0]
  ]' \
  --output table

# Check how long instances have been stopped
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=stopped" \
  --query 'Reservations[*].Instances[*].[InstanceId,StateTransitionReason]' \
  --output table
```

### Low Utilization Running Instances

```bash
# Get average CPU for an instance over 14 days
INSTANCE_ID="i-0123456789abcdef0"
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -d "14 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum \
  --query 'Datapoints | sort_by(@, &Timestamp)'

# Network activity check (low network = likely idle)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name NetworkIn \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Sum
```

### Thresholds for Idle Detection

| Metric | Idle Threshold | Period |
|--------|---------------|--------|
| CPU Utilization | < 5% average | 14 days |
| Network In | < 1 MB/day | 7 days |
| Disk Read/Write | < 10 ops/day | 7 days |

---

## EBS Volumes

### Unattached Volumes (100% Waste)

```bash
# Find all unattached volumes
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query 'Volumes[*].[
    VolumeId,
    Size,
    VolumeType,
    CreateTime,
    Tags[?Key==`Name`].Value|[0]
  ]' \
  --output table

# Calculate total cost of unattached volumes
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query 'Volumes[*].[VolumeType,Size]' \
  --output text | awk '
    BEGIN {total=0}
    $1=="gp3" {total += $2 * 0.08}
    $1=="gp2" {total += $2 * 0.10}
    $1=="io1" {total += $2 * 0.125}
    $1=="io2" {total += $2 * 0.125}
    $1=="st1" {total += $2 * 0.045}
    $1=="sc1" {total += $2 * 0.015}
    END {printf "Estimated monthly waste: $%.2f\n", total}'
```

### Low I/O Volumes

```bash
# Check volume read/write activity
VOLUME_ID="vol-0123456789abcdef0"
aws cloudwatch get-metric-statistics \
  --namespace AWS/EBS \
  --metric-name VolumeReadOps \
  --dimensions Name=VolumeId,Value=$VOLUME_ID \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 604800 \
  --statistics Sum
```

---

## Elastic IPs

```bash
# Find unassociated Elastic IPs ($3.60/month each when idle)
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==`null`].[
    PublicIp,
    AllocationId,
    Domain,
    Tags[?Key==`Name`].Value|[0]
  ]' \
  --output table

# Count and calculate cost
IDLE_EIPS=$(aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==`null`] | length(@)' \
  --output text)
echo "Idle Elastic IPs: $IDLE_EIPS (wasting \$$(echo "$IDLE_EIPS * 3.60" | bc)/month)"
```

---

## Load Balancers

### Find Load Balancers

```bash
# List all load balancers
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].[
    LoadBalancerName,
    Type,
    State.Code,
    CreatedTime
  ]' \
  --output table
```

### Check for Empty Target Groups

```bash
# List target groups with target count
for tg_arn in $(aws elbv2 describe-target-groups --query 'TargetGroups[*].TargetGroupArn' --output text); do
  tg_name=$(aws elbv2 describe-target-groups --target-group-arns $tg_arn --query 'TargetGroups[0].TargetGroupName' --output text)
  target_count=$(aws elbv2 describe-target-health --target-group-arn $tg_arn --query 'TargetHealthDescriptions | length(@)' --output text)
  echo "$tg_name: $target_count targets"
done
```

### Check Request Count

```bash
# Check ALB for requests over past week
LB_ARN="arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id"
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=$(echo $LB_ARN | cut -d'/' -f2-) \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 604800 \
  --statistics Sum
```

**ALB Cost:** ~$16/month minimum + data processing
**NLB Cost:** ~$16/month minimum + data processing

---

## RDS Instances

### Find Idle Databases

```bash
# List all RDS instances
aws rds describe-db-instances \
  --query 'DBInstances[*].[
    DBInstanceIdentifier,
    DBInstanceClass,
    Engine,
    DBInstanceStatus,
    AllocatedStorage
  ]' \
  --output table

# Check database connections
DB_IDENTIFIER="mydb"
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_IDENTIFIER \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Maximum
```

### Stopped Databases

RDS supports stopping instances for up to 7 days (auto-restarts after).

```bash
aws rds describe-db-instances \
  --query 'DBInstances[?DBInstanceStatus==`stopped`].[
    DBInstanceIdentifier,
    DBInstanceClass,
    Engine
  ]' \
  --output table
```

---

## S3 Buckets

### Check for Empty or Rarely-Accessed Buckets

```bash
# List buckets with size metrics
for bucket in $(aws s3api list-buckets --query 'Buckets[*].Name' --output text); do
  size=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/S3 \
    --metric-name BucketSizeBytes \
    --dimensions Name=BucketName,Value=$bucket Name=StorageType,Value=StandardStorage \
    --start-time $(date -d "1 day ago" -u +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Average \
    --query 'Datapoints[0].Average' \
    --output text 2>/dev/null)
  echo "$bucket: $size bytes"
done
```

### Check Storage Class Opportunities

S3 Intelligent-Tiering can automatically move data to cheaper storage.

```bash
# Get S3 inventory for storage analysis
aws s3api list-buckets --query 'Buckets[*].Name' --output text | \
  xargs -I {} aws s3api get-bucket-analytics-configuration --bucket {} --id inventory 2>/dev/null
```

---

## NAT Gateways

NAT Gateways cost ~$32/month + data processing.

```bash
# List NAT Gateways
aws ec2 describe-nat-gateways \
  --query 'NatGateways[?State==`available`].[
    NatGatewayId,
    SubnetId,
    VpcId,
    CreateTime
  ]' \
  --output table

# Check bytes processed
NAT_GW_ID="nat-0123456789abcdef0"
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --dimensions Name=NatGatewayId,Value=$NAT_GW_ID \
  --start-time $(date -d "7 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 604800 \
  --statistics Sum
```

---

## Lambda Functions

```bash
# Find Lambda functions with no invocations
for func in $(aws lambda list-functions --query 'Functions[*].FunctionName' --output text); do
  invocations=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=$func \
    --start-time $(date -d "30 days ago" -u +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 2592000 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text 2>/dev/null)
  if [ "$invocations" == "None" ] || [ "$invocations" == "0" ]; then
    echo "UNUSED: $func"
  fi
done
```

---

## CloudWatch Log Groups

```bash
# Find log groups with retention set to never expire
aws logs describe-log-groups \
  --query 'logGroups[?retentionInDays==`null`].[logGroupName,storedBytes]' \
  --output table

# Calculate storage cost ($0.03/GB/month)
aws logs describe-log-groups \
  --query 'sum(logGroups[].storedBytes)' \
  --output text | awk '{printf "Log storage: %.2f GB ($%.2f/month)\n", $1/1024/1024/1024, $1/1024/1024/1024*0.03}'
```

---

## Snapshots

```bash
# Find old EBS snapshots (older than 90 days)
CUTOFF_DATE=$(date -d "90 days ago" +%Y-%m-%d)
aws ec2 describe-snapshots \
  --owner-ids self \
  --query "Snapshots[?StartTime<='${CUTOFF_DATE}'].[
    SnapshotId,
    VolumeId,
    VolumeSize,
    StartTime,
    Description
  ]" \
  --output table

# Calculate snapshot storage cost
aws ec2 describe-snapshots \
  --owner-ids self \
  --query 'sum(Snapshots[].VolumeSize)' \
  --output text | awk '{printf "Snapshot storage: %d GB ($%.2f/month)\n", $1, $1*0.05}'
```

---

## Summary Checklist

| Resource | Check | Cost Impact |
|----------|-------|-------------|
| EC2 Stopped | `instance-state-name=stopped` | EBS + EIP |
| EC2 Low CPU | CloudWatch < 5% | Full instance cost |
| EBS Unattached | `status=available` | $0.08-0.125/GB/month |
| Elastic IP | No AssociationId | $3.60/month each |
| ALB/NLB Idle | No request count | ~$16+/month |
| RDS Idle | No connections | Full instance cost |
| NAT Gateway | Low bytes | $32+/month |
| Lambda Unused | 0 invocations | Minimal (storage) |
| Log Groups | No retention | $0.03/GB/month |
| Snapshots | > 90 days old | $0.05/GB/month |
