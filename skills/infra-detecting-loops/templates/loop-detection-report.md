# Loop Detection Report

**Project:** [Project name]
**Date:** [Date]
**Auditor:** Claude Code + [User]
**Scope:** [Stacks/services analyzed]

---

## Executive Summary

**Overall Risk Level:** [CRITICAL / HIGH / MEDIUM / LOW]

| Category | Findings | Critical | High | Medium | Low |
|----------|----------|----------|------|--------|-----|
| CloudFormation Dependencies | | | | | |
| Event-Driven Trigger Chains | | | | | |
| Step Function Cycles | | | | | |
| Lambda Re-invocation | | | | | |
| **Total** | | | | | |

---

## Architecture Overview

### Event Flow Diagram

```
[Describe the event flow graph for the project]

EventBridge Rule (schedule/pattern)
  -> Lambda: [name]
    -> [side effect: writes to table/publishes event/etc.]
      -> [Does this trigger another component?]
```

### Components Inventoried

| Component | Type | Trigger | Target | Loop Risk |
|-----------|------|---------|--------|-----------|
| | EventBridge Rule | | | |
| | Lambda Function | | | |
| | Step Function | | | |
| | DynamoDB Stream | | | |
| | SQS Queue | | | |

---

## Findings

### Finding 1: [Title]

**Severity:** [CRITICAL / HIGH / MEDIUM / LOW / INFO]
**Category:** [Event-Driven / SFN / Lambda / CloudFormation]
**Location:** [file:line]

**Trigger Chain:**
```
[Event source] -> [Lambda] -> [Side effect] -> [Re-trigger?]
```

**Root Cause:**
[Why this could loop]

**Existing Defenses:**
- [List any safeguards already in place]

**Blast Radius:**
- Cost impact: [Estimate per hour if looping]
- Data impact: [Duplicates? Corruption?]
- Downstream: [What else breaks?]

**Recommended Fix:**
```python
# Specific code change
```

**Effort:** [S / M / L]

---

### Finding 2: [Title]

[Repeat structure for each finding]

---

## Defense Mechanism Audit

### Existing Defenses

| Defense | Present? | Location | Adequate? |
|---------|----------|----------|-----------|
| Concurrency guard | | | |
| Idempotency check | | | |
| DLQ configured | | | |
| Lambda timeout set | | | |
| SFN execution timeout | | | |
| Retry MaxAttempts | | | |
| Circuit breaker | | | |
| Flag management (3-state) | | | |
| CloudWatch alarms | | | |

### Missing Defenses

| Defense | Priority | Effort | Recommendation |
|---------|----------|--------|----------------|
| | | | |

---

## Tool Scan Results

### cfn-lint

```
[Paste cfn-lint output, especially E3004 circular dependency results]
```

**Circular dependencies found:** [count]

### Checkov

```
[Paste Checkov summary]
```

### cdk-nag

```
[Paste cdk-nag warnings/errors if applicable]
```

---

## Remediation Plan

### Immediate (This Sprint)

| # | Finding | Fix | Owner | Effort |
|---|---------|-----|-------|--------|
| 1 | | | | |

### Short-Term (Next Sprint)

| # | Finding | Fix | Owner | Effort |
|---|---------|-----|-------|--------|
| 1 | | | | |

### Long-Term (Backlog)

| # | Finding | Fix | Owner | Effort |
|---|---------|-----|-------|--------|
| 1 | | | | |

---

## Appendix: Detection Commands Run

```bash
# List all commands executed during this audit
```
