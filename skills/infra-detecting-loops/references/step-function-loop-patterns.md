# Step Function Loop Patterns

This reference catalogs infinite loop and non-terminating patterns specific to AWS Step Functions (ASL). Each pattern includes the state machine structure, detection method, and fix.

---

## Pattern 1: Choice State Cycle Without Convergence

A Choice state routes back to an earlier state, creating a cycle. The condition that would exit the cycle depends on external state that may never change.

### ASL Structure

```json
{
  "ProcessItem": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:process-item",
    "Next": "CheckResult"
  },
  "CheckResult": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.status",
        "StringEquals": "COMPLETE",
        "Next": "Done"
      }
    ],
    "Default": "ProcessItem"
  }
}
```

**Loop risk:** If `process-item` Lambda always returns `$.status = "PENDING"`, the state machine loops forever between ProcessItem and CheckResult.

### Detection

```bash
# Find Choice states
rg "\"Type\": \"Choice\"" -A 30 [SFN_FILE]

# For each Choice state, check:
# 1. Does any branch route to an EARLIER state? (creates a cycle)
# 2. Is there a Default branch?
# 3. Does the task in the cycle modify the Choice variable?
```

### Recommended Fix

```json
{
  "ProcessItem": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:process-item",
    "Next": "CheckResult",
    "Retry": [{"MaxAttempts": 3}],
    "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "HandleFailure"}]
  },
  "CheckResult": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.status",
        "StringEquals": "COMPLETE",
        "Next": "Done"
      },
      {
        "Variable": "$.retry_count",
        "NumericGreaterThanEquals": 10,
        "Next": "MaxRetriesExceeded"
      }
    ],
    "Default": "IncrementRetryAndProcess"
  },
  "IncrementRetryAndProcess": {
    "Type": "Pass",
    "Parameters": {
      "retry_count.$": "States.MathAdd($.retry_count, 1)",
      "status.$": "$.status"
    },
    "Next": "ProcessItem"
  }
}
```

Key additions:
- Counter variable (`retry_count`) incremented each loop iteration
- Choice branch that exits when counter exceeds threshold
- Catch block for task failures

---

## Pattern 2: Unbounded Retry Configuration

Task state retries indefinitely without MaxAttempts or with an unreasonably high value.

### ASL Structure (Dangerous)

```json
{
  "InvokeBrain": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:brain",
    "Retry": [
      {
        "ErrorEquals": ["States.ALL"],
        "IntervalSeconds": 1,
        "BackoffRate": 2.0
      }
    ]
  }
}
```

**Loop risk:** Missing `MaxAttempts` defaults to 3 in Step Functions, but many developers assume it retries forever. The real risk is when MaxAttempts is explicitly set very high (e.g., 100) combined with a fast BackoffRate.

### Detection

```bash
# Find Retry configurations
rg "\"Retry\"" -A 15 [SFN_FILE]

# Check for:
# 1. Missing MaxAttempts (defaults to 3, usually safe)
# 2. MaxAttempts > 10 (suspicious)
# 3. States.ALL without a Catch fallback
# 4. IntervalSeconds < 5 with low BackoffRate (retry storm)
```

### Retry Cost Calculator

```
Total retries = MaxAttempts
Total time = sum(IntervalSeconds * BackoffRate^n for n in 0..MaxAttempts-1)

Example: IntervalSeconds=1, BackoffRate=2, MaxAttempts=20
  Total time = 1 + 2 + 4 + 8 + ... + 524288 = ~6 days
  Each retry invokes the Lambda = 20 Lambda invocations
```

### Recommended Fix

```json
{
  "Retry": [
    {
      "ErrorEquals": ["States.TaskFailed", "Lambda.ServiceException"],
      "IntervalSeconds": 5,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "Next": "HandleError",
      "ResultPath": "$.error"
    }
  ]
}
```

Rules:
- Always pair Retry with Catch
- MaxAttempts <= 5 for most use cases
- IntervalSeconds >= 5 to avoid Lambda throttling
- Never retry on `States.ALL` without a Catch; use specific error types

---

## Pattern 3: Map State Output Explosion

Map state processes many items, each returning large output. Combined output exceeds the 256KB Step Functions payload limit.

### ASL Structure

```json
{
  "ProcessDeals": {
    "Type": "Map",
    "ItemsPath": "$.deals",
    "MaxConcurrency": 2,
    "Iterator": {
      "StartAt": "ProcessDeal",
      "States": {
        "ProcessDeal": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:...:process-deal",
          "End": true
        }
      }
    },
    "Next": "Summarize"
  }
}
```

**Issue:** If each deal's output is 20KB and there are 16 deals, combined output = 320KB, exceeding the 256KB limit. The execution fails with `States.DataLimitExceeded`.

This is not an infinite loop per se, but causes:
- Repeated failures on every execution
- Wasted Lambda invocations (all items process successfully, then Map fails)
- Retry of the entire Map state (re-invoking all Lambdas)

### Detection

```bash
# Find Map states
rg "\"Type\": \"Map\"" -A 20 [SFN_FILE]

# Check:
# 1. Is there a ResultPath or ResultSelector to trim output?
# 2. What does the iterator Lambda return? (Full objects or just IDs?)
# 3. How many items could be in ItemsPath?
```

### Recommended Fix

```json
{
  "ProcessDeals": {
    "Type": "Map",
    "ItemsPath": "$.deals",
    "MaxConcurrency": 2,
    "ResultSelector": {
      "processed_count.$": "States.ArrayLength($)"
    },
    "Iterator": {
      "StartAt": "ProcessDeal",
      "States": {
        "ProcessDeal": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:...:process-deal",
          "ResultSelector": {
            "deal_id.$": "$.deal_id",
            "status.$": "$.status"
          },
          "End": true
        }
      }
    }
  }
}
```

Key: Use `ResultSelector` to keep only essential fields from each iteration. If the downstream state does not need the Map output at all, use `"ResultPath": null`.

---

## Pattern 4: Parallel State Without Timeout

A Parallel state contains branches that may run indefinitely (e.g., waiting for an external callback).

### Detection

```bash
# Find Parallel states
rg "\"Type\": \"Parallel\"" -A 30 [SFN_FILE]

# Check:
# 1. Does any branch contain a Wait state with no timeout?
# 2. Does any branch use .waitForTaskToken without HeartbeatSeconds?
# 3. Is there a TimeoutSeconds on the Parallel state itself?
```

### Recommended Fix

```json
{
  "ParallelProcessing": {
    "Type": "Parallel",
    "TimeoutSeconds": 600,
    "Branches": [...]
  }
}
```

Always set `TimeoutSeconds` on Parallel states. For `.waitForTaskToken` patterns, also set `HeartbeatSeconds` on the Task state.

---

## Pattern 5: Express vs Standard Workflow Mismatch

Express Step Functions have a 5-minute maximum duration. If a workflow can exceed this (e.g., due to Wait states, slow Lambdas, or retries), it will time out and may be re-triggered by the caller.

### Detection

```bash
# Check workflow type in CDK
rg "StateMachineType\|state_machine_type\|EXPRESS" --type py --type ts

# Calculate maximum execution time:
# Sum of all possible Wait + Task timeouts along the longest path
```

### Recommended Fix

- Use Standard workflows for anything that might exceed 5 minutes
- If using Express for cost savings, ensure all paths complete within 5 minutes
- Set explicit `TimeoutSeconds` on the state machine definition

---

## Pattern 6: Distributed Map Without Bounds

Distributed Map (introduced 2022) can process millions of items from S3. Without proper bounds, this can create massive Lambda invocation storms.

### Detection

```bash
# Find Distributed Map
rg "\"ItemReader\"|\"S3ObjectsItemReader\"|DISTRIBUTED" [SFN_FILE]

# Check for MaxConcurrency and ToleratedFailurePercentage
```

### Recommended Fix

```json
{
  "Type": "Map",
  "ItemProcessor": {
    "ProcessorConfig": {
      "Mode": "DISTRIBUTED",
      "ExecutionType": "STANDARD"
    }
  },
  "MaxConcurrency": 40,
  "ToleratedFailurePercentage": 10,
  "Label": "ProcessItems"
}
```

Always set `MaxConcurrency` for distributed Maps. Consider `ToleratedFailurePercentage` to stop processing if too many items fail (which may indicate a systemic issue).

---

## Step Function Cycle Detection Algorithm

To systematically detect cycles in a state machine definition:

```
1. Parse the ASL JSON
2. Build a directed graph: State -> [NextStates]
   - For Task/Pass/Wait states: add edge to "Next"
   - For Choice states: add edges to all branch targets + Default
   - For Map/Parallel: add edges to Iterator/Branch start states
3. Run depth-first search (DFS) from StartAt
4. Any back-edge (visiting a node already on the current path) = CYCLE
5. For each cycle found:
   a. Identify the Choice state that creates the back-edge
   b. Check if the cycle path modifies the Choice variable
   c. Check for an exit condition (counter, max attempts, timeout)
   d. If no exit condition found -> flag as potential infinite loop
```

---

## SFN Timeout Hierarchy

Step Functions have multiple timeout levels. Missing any one creates risk:

| Level | Setting | Default | Risk |
|-------|---------|---------|------|
| Execution | `TimeoutSeconds` on StateMachine | None (runs until completion or 1 year) | Stuck executions accumulate |
| State | `TimeoutSeconds` on Task state | None | Single state blocks forever |
| Heartbeat | `HeartbeatSeconds` on Task | None | Callback tasks never complete |
| Retry | `MaxAttempts` in Retry config | 3 | Reasonable default |
| Map | `MaxConcurrency` on Map | 0 (unlimited) | Lambda throttling storm |

**Recommendation:** Set explicit timeouts at execution AND state level. Never rely on defaults for production workflows.
