# CloudWatch Investigation Report

## Summary

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Reported Issue** | Brief description of the symptom |
| **Environment** | dev / staging / prod |
| **AWS Profile** | Profile used |
| **Region** | us-east-1 / etc |
| **Severity** | Critical / High / Medium / Low |
| **Status** | Investigating / Root cause found / Resolved |

## Resources Investigated

| Resource Type | Name | Log Group |
|--------------|------|-----------|
| Lambda | function-name | /aws/lambda/function-name |
| Step Function | state-machine-name | /aws/vendedlogs/states/... |

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM:SS | First occurrence of error |
| HH:MM:SS | Key event |

## Findings

### Root Cause

Describe the root cause clearly. What went wrong and why.

### Evidence

Include relevant log entries (with noise filtered out):

```
[relevant log entries here]
```

### Lambda Metrics

| Metric | Value |
|--------|-------|
| Duration | X ms |
| Memory Used | X MB / Y MB |
| Init Duration | X ms (if cold start) |
| Billed Duration | X ms |
| Error Rate | X% over last N hours |

### LLM Call Analysis (if agent Lambda)

| Metric | Value |
|--------|-------|
| Total LLM Calls | N |
| Total Tokens | N |
| Total Cost | $X.XX |
| Looping Detected | Yes/No |

## Recommendation

### Immediate Action

What should be done right now to fix or mitigate the issue.

### Long-term Fix

What should be done to prevent recurrence.

## Cross-Reference

List any related Lambdas, Step Functions, or pipelines that were checked as part of this investigation.
