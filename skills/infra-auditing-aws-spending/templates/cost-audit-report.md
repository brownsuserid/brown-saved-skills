# AWS Cost Audit Report

**Account:** [Account ID / Alias]
**Audit Period:** [Start Date] to [End Date]
**Auditor:** [Name]
**Date:** [Audit Date]

---

## Executive Summary

**Total Spend (Audit Period):** $X,XXX.XX
**Identified Savings:** $X,XXX.XX/month
**Estimated Annual Savings:** $XX,XXX.XX

### Key Findings

1. [Top finding with impact]
2. [Second finding]
3. [Third finding]

### Recommended Actions

| Priority | Action | Monthly Savings | Effort |
|----------|--------|-----------------|--------|
| Critical | [Action] | $XXX | Low/Med/High |
| High | [Action] | $XXX | Low/Med/High |
| Medium | [Action] | $XXX | Low/Med/High |

---

## Spending Overview

### Total Cost by Service

| Service | Cost | % of Total |
|---------|------|------------|
| Amazon EC2 | $X,XXX | XX% |
| Amazon RDS | $X,XXX | XX% |
| Amazon S3 | $X,XXX | XX% |
| [Others] | $X,XXX | XX% |
| **Total** | **$X,XXX** | **100%** |

### Cost by Customer

| Customer | Cost | % of Total | MoM Change | Top Service |
|----------|------|------------|------------|-------------|
| [customer-1] | $X,XXX | XX% | +/- X% | [Service] |
| [customer-2] | $X,XXX | XX% | +/- X% | [Service] |
| [customer-3] | $X,XXX | XX% | +/- X% | [Service] |
| *(untagged)* | $X,XXX | XX% | +/- X% | [Service] |
| **Total** | **$X,XXX** | **100%** | | |

**Observations:** [Note any customers with disproportionate growth, outsized cost relative to revenue, or surprising service usage patterns]

### Cost by Product

| Product | Cost | % of Total | MoM Change | Top Service |
|---------|------|------------|------------|-------------|
| [product-1] | $X,XXX | XX% | +/- X% | [Service] |
| [product-2] | $X,XXX | XX% | +/- X% | [Service] |
| *(untagged)* | $X,XXX | XX% | +/- X% | [Service] |
| **Total** | **$X,XXX** | **100%** | | |

### Customer × Service Breakdown (Top Spenders)

For each of the top 3-5 customers, break down what they're spending on:

#### [Customer 1]

| Service | Cost | Notes |
|---------|------|-------|
| [Service] | $X,XXX | [context] |
| [Service] | $X,XXX | [context] |

#### [Customer 2]

| Service | Cost | Notes |
|---------|------|-------|
| [Service] | $X,XXX | [context] |

### Untagged Resources

| Category | Untagged Cost | % of Total | Action |
|----------|---------------|------------|--------|
| Missing `customer` tag | $X,XXX | XX% | [Tag or investigate] |
| Missing `product` tag | $X,XXX | XX% | [Tag or investigate] |

**If untagged spend exceeds 10%, improving tagging should be a priority recommendation.**

### Cost Trend

[Insert trend analysis - increasing/decreasing/stable]

| Period | Cost | Change |
|--------|------|--------|
| Month 1 | $X,XXX | - |
| Month 2 | $X,XXX | +/- X% |
| Month 3 | $X,XXX | +/- X% |

### Cost by Region

| Region | Cost | Notes |
|--------|------|-------|
| us-east-1 | $X,XXX | Primary |
| us-west-2 | $X,XXX | DR |
| [Other] | $X,XXX | [Purpose] |

---

## Idle Resources

### Summary

| Resource Type | Count | Monthly Waste |
|---------------|-------|---------------|
| Stopped EC2 Instances | X | $XXX |
| Unattached EBS Volumes | X | $XXX |
| Unused Elastic IPs | X | $XXX |
| Idle Load Balancers | X | $XXX |
| **Total Idle Waste** | - | **$XXX** |

### Detailed Findings

#### Stopped EC2 Instances

| Instance ID | Name | Type | Stopped Since | EBS Cost |
|-------------|------|------|---------------|----------|
| i-xxx | [Name] | t3.medium | YYYY-MM-DD | $XX/mo |

**Recommendation:** Terminate or snapshot and remove.

#### Unattached EBS Volumes

| Volume ID | Size | Type | Created | Monthly Cost |
|-----------|------|------|---------|--------------|
| vol-xxx | XX GB | gp3 | YYYY-MM-DD | $XX |

**Recommendation:** Delete or attach to instance.

#### Unused Elastic IPs

| Public IP | Allocation ID | Monthly Cost |
|-----------|---------------|--------------|
| X.X.X.X | eipalloc-xxx | $3.60 |

**Recommendation:** Release unused allocations.

---

## Rightsizing Opportunities

### EC2 Instances

| Instance | Current Type | Recommended | Monthly Savings |
|----------|--------------|-------------|-----------------|
| i-xxx | m5.xlarge | m5.large | $XX |
| i-xxx | c5.2xlarge | c6g.xlarge | $XX |

**Total EC2 Rightsizing Savings:** $XXX/month

### RDS Instances

| Database | Current Class | Recommended | Monthly Savings |
|----------|---------------|-------------|-----------------|
| mydb | db.r5.xlarge | db.r5.large | $XX |

**Total RDS Rightsizing Savings:** $XXX/month

### Lambda Functions

| Function | Current Memory | Recommended | Monthly Savings |
|----------|----------------|-------------|-----------------|
| func-xxx | 1024 MB | 512 MB | $XX |

---

## Commitment Opportunities

### Current Coverage

| Resource Type | On-Demand | Covered | Coverage % |
|---------------|-----------|---------|------------|
| EC2 | $X,XXX | $X,XXX | XX% |
| RDS | $X,XXX | $X,XXX | XX% |
| Lambda | $X,XXX | $X,XXX | XX% |

### Savings Plan Recommendations

| Plan Type | Commitment | Term | Monthly Savings |
|-----------|------------|------|-----------------|
| Compute SP | $XXX/hr | 1 year | $X,XXX |
| EC2 Instance SP | $XXX/hr | 1 year | $X,XXX |

**Recommended Action:** [Specific recommendation]

---

## Trusted Advisor Findings

### Cost Optimization Checks

| Check | Status | Estimated Savings |
|-------|--------|------------------|
| Low Utilization EC2 | X findings | $XXX |
| Idle Load Balancers | X findings | $XXX |
| Underutilized EBS | X findings | $XXX |
| Unassociated EIPs | X findings | $XXX |

---

## Cost Anomalies

### Recent Anomalies

| Date | Service | Expected | Actual | Impact |
|------|---------|----------|--------|--------|
| YYYY-MM-DD | [Service] | $XXX | $XXX | +$XXX |

### Anomaly Detection Status

- [ ] Anomaly monitors configured
- [ ] Alert subscriptions active
- [ ] Threshold appropriate

---

## Storage Optimization

### S3 Analysis

| Bucket | Size | Storage Class | Recommendation |
|--------|------|---------------|----------------|
| bucket-xxx | XX GB | Standard | Move to IA |

### EBS Optimization

| Recommendation | Count | Monthly Savings |
|----------------|-------|-----------------|
| gp2 to gp3 migration | X | $XXX |
| Snapshot cleanup | X | $XXX |

---

## Recommendations Summary

### Critical (Do This Week)

1. **[Action]** - $XXX/month savings
   - Resources: [List]
   - Risk: Low
   - Steps: [Brief steps]

### High Priority (Do This Sprint)

1. **[Action]** - $XXX/month savings
   - Resources: [List]
   - Risk: Medium
   - Steps: [Brief steps]

### Medium Priority (Plan for Next Sprint)

1. **[Action]** - $XXX/month savings
   - Resources: [List]

### Low Priority (Backlog)

1. **[Action]** - $XXX/month savings

---

## Total Identified Savings

| Category | Monthly Savings | Annual Savings |
|----------|-----------------|----------------|
| Idle Resources | $XXX | $X,XXX |
| Rightsizing | $XXX | $X,XXX |
| Commitments | $XXX | $X,XXX |
| Storage | $XXX | $X,XXX |
| **Total** | **$X,XXX** | **$XX,XXX** |

---

## Next Steps

1. [ ] Review findings with stakeholders
2. [ ] Prioritize actions based on risk/reward
3. [ ] Create tickets for approved actions
4. [ ] Schedule follow-up audit in 30 days
5. [ ] Set up automated monitoring

---

## Appendix

### Data Collection Commands

```bash
# Commands used for this audit
aws ce get-cost-and-usage ...
aws ec2 describe-instances ...
[etc.]
```

### Assumptions

- [Any assumptions made during analysis]

### Limitations

- [Any limitations of the analysis]
