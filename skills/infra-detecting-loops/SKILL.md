---
name: infra-detecting-loops
description: Detects potential infinite loops in AWS serverless architectures when auditing CDK/CloudFormation projects. Analyzes event-driven trigger chains, Step Function cycles, Lambda re-invocation, and CloudFormation circular dependencies. Use this skill whenever the user mentions: loop detection, infinite loop, recursive Lambda, Lambda invocation spike, S3 event loop, DynamoDB stream firing repeatedly, EventBridge re-triggering, Step Function stuck or running forever, "why is my Lambda running so many times", "invocation count is spiking", circular dependency in CloudFormation, or any pre-deployment audit of event-driven architecture. Also use when the user asks to check for runaway costs from Lambda invocations, or wants to verify an architecture won't loop before deploying. If infra-cloudwatch-investigation reveals an invocation spike or runaway execution, this is the right follow-up skill.
---

# Detecting Loops in AWS Architectures

This skill systematically analyzes AWS CDK and CloudFormation projects for potential infinite loops at both the infrastructure and application layers. The focus is on event-driven trigger chains that re-fire when processing fails, Step Function cycles that never exit, and recursive Lambda invocations.

The core insight: **most loops happen on error paths, not happy paths.** A Lambda that works perfectly 99% of the time can still create an infinite loop when it fails, because the trigger condition was never cleared.

## Process Overview

Use the TodoWrite tool to track progress through these phases. Skip phases that don't apply (e.g., skip Phase 4 if there are no Step Functions).

---

## Phase 1: Project Assessment

Map the project's event-driven architecture before looking for loops.

### Map Project Structure

Identify all event-driven components:
- **EventBridge rules** — scheduled and pattern-based
- **Lambda functions** — and what triggers each one
- **Step Functions** — and their trigger mechanisms
- **DynamoDB Streams** — which tables have them, which Lambdas consume them
- **SQS queues and SNS topics** — subscription chains
- **S3 event notifications** — which buckets, which prefixes
- **API Gateway endpoints** — any that route to Lambdas

Search CDK code (`cdk/`) for these components. Also check for synthesized templates in `cdk.out/`.

### Create Architecture Inventory

Build a simple event flow graph showing how components connect:

```
EventBridge Rule (rate: 5 min) -> Lambda: process_deals -> DynamoDB: deals table
DynamoDB Stream: deals table -> Lambda: sync_deals -> External API
```

This graph is the foundation for all subsequent analysis. Every arrow is a potential loop entry point.

---

## Phase 2: CloudFormation Circular Dependency Detection

Detect infrastructure-level cycles in the resource dependency graph.

```bash
# Synthesize CDK templates
cdk synth --all --quiet --output cdk.out/

# Run cfn-lint — look for E3004 (circular dependency)
cfn-lint cdk.out/*.template.json 2>&1 | tee cfn-lint-results.txt
grep -i "E3004\|circular" cfn-lint-results.txt

# Run Checkov for structural issues
checkov -d cdk.out/ --framework cloudformation --compact 2>&1 | tee checkov-results.txt
```

CloudFormation itself rejects circular dependencies at deploy time, but catching them here avoids wasted deployment time. Cross-stack references (`Fn::ImportValue` / `CfnOutput`) are a common source.

**Reference:** See `../infra-cdk-quality/references/cdk-security-scanning.md` for full cfn-lint/Checkov setup.

---

## Phase 3: Event-Driven Trigger Chain Analysis

**This is the highest-value phase.** For every event source in the project, trace the full chain and ask these questions:

| Question | Risk if "No" |
|----------|-------------|
| Does the Lambda clear/change the trigger condition on success? | HIGH — will re-trigger |
| Does the Lambda clear/change the trigger condition on failure? | HIGH — will loop on errors |
| Is there a concurrency guard? | MEDIUM — parallel storms |
| Is there a max retry/execution limit? | MEDIUM — unbounded retries |
| Is there a DLQ for failed invocations? | MEDIUM — silent failures |

For each trigger chain found, classify it against the known loop patterns:

- **Pattern A:** EventBridge Schedule -> Lambda -> Unchanged Entry Condition (most common)
- **Pattern B:** DynamoDB Stream -> Lambda -> Same Table Write
- **Pattern C:** S3 Event -> Lambda -> Same Bucket Write
- **Pattern D:** SNS/SQS Circular Subscription
- **Pattern E:** API Gateway -> Lambda -> Self-Call via HTTP
- **Pattern F:** EventBridge Event Pattern -> Lambda -> Emits Same Event

**Reference:** See `references/event-driven-loop-patterns.md` for detailed detection methods, real-world examples, and recommended fixes for each pattern.

---

## Phase 4: Step Function Loop Detection

Analyze Step Function definitions for non-terminating state machine patterns.

### What to look for

1. **Choice State Cycles** — A Choice state routes back to an earlier state. Does the looped path change the condition that would eventually exit? If not, it loops forever.

2. **Unbounded Retry** — Task with Retry but no MaxAttempts, or MaxAttempts set very high. Missing MaxAttempts defaults to 3 (usually safe), but explicit high values combined with fast BackoffRate create retry storms.

3. **Map State Output Explosion** — Map processes many items, each returning large output. Combined output exceeds 256KB payload limit, causing repeated `States.DataLimitExceeded` failures.

4. **Missing Timeouts** — No `TimeoutSeconds` at execution or state level. Standard workflows can run up to 1 year by default.

5. **Parallel State Without Timeout** — Branches using `.waitForTaskToken` without `HeartbeatSeconds`.

6. **Distributed Map Without Bounds** — No `MaxConcurrency` set, creating massive Lambda invocation storms.

### Cycle Detection Approach

Build a directed graph of state transitions from the ASL definition:
- For Task/Pass/Wait states: edge to `Next`
- For Choice states: edges to all branch targets + Default
- For Map/Parallel: edges to Iterator/Branch start states

Any back-edge (visiting a state already on the current path) = potential cycle. For each cycle, check if the loop path modifies the Choice variable to eventually exit.

**Reference:** See `references/step-function-loop-patterns.md` for detailed ASL patterns, the cycle detection algorithm, and the SFN timeout hierarchy.

---

## Phase 5: Lambda Re-invocation Pattern Detection

Detect Lambdas that directly or indirectly invoke themselves.

### What to check

- **Direct self-invocation:** Lambda calls `lambda_client.invoke()` with its own function name
- **Indirect re-invocation via events:** Lambda publishes an event (EventBridge, SNS, SQS) that matches a rule targeting itself
- **Recursive chains:** Lambda A triggers Lambda B which triggers Lambda A

### Defense Mechanism Audit

For each Lambda in the project, check for these safeguards:

- [ ] `reserved_concurrent_executions` set (not unlimited)
- [ ] Dead letter queue configured
- [ ] Timeout set appropriately (not 900s default)
- [ ] Idempotency handling (checks if already processed)
- [ ] Circuit breaker pattern (max execution counter)

---

## Phase 6: Defense Mechanism Assessment

Evaluate existing safeguards across the entire project and recommend improvements.

For each loop risk found in Phases 3-5, recommend specific mitigations:

| Risk | Recommended Defense |
|------|-------------------|
| EventBridge re-trigger | Three-state flag (pending/processing/failed) |
| DynamoDB stream loop | Event source filter on INSERT only + processed marker |
| S3 event loop | Separate input/output buckets or prefix filtering |
| Unbounded SFN retry | MaxAttempts + Catch with fallback state |
| Lambda self-invocation | Concurrency limit + DLQ + idempotency key |
| Map state explosion | MaxConcurrency + ResultSelector to trim output |
| SQS retry storm | Visibility timeout > Lambda timeout + DLQ after N retries |

**Reference:** See `references/loop-defense-patterns.md` for concrete implementation patterns with CDK and Python code examples.

---

## Phase 7: Generate Findings Report

Compile all findings into a prioritized, actionable report using the template at `templates/loop-detection-report.md`.

Only include sections relevant to what was found — skip empty sections (e.g., if no Step Functions exist, omit that section entirely).

### Severity Classification

| Severity | Definition | Example |
|----------|-----------|---------|
| CRITICAL | Active or near-certain loop with no defense | EventBridge -> Lambda that never clears flag |
| HIGH | Likely loop under failure conditions | DynamoDB stream handler writes to same table on error |
| MEDIUM | Possible loop, some defenses present | SFN retry without MaxAttempts but has Catch |
| LOW | Theoretical risk, adequate defenses | Lambda with concurrency limit and DLQ |
| INFO | Observation, no action needed | Scheduled rule with proper idempotency |

### For Each Finding Include

1. **Location:** File path and line number
2. **Trigger chain:** Full event flow diagram (A -> B -> C -> A)
3. **Root cause:** Why this could loop
4. **Existing defenses:** What safeguards exist
5. **Blast radius:** Cost per hour if looping, data corruption risk, downstream impact
6. **Recommended fix:** Specific code/config change with example
7. **Effort estimate:** S/M/L

### Quality Check

After generating the report, run the scanner to validate completeness:

```bash
python infra-detecting-loops/scripts/scan_loop_detection.py <report-file>
```

---

## Key Principles

- **Trace full chains:** Follow event -> Lambda -> side effect -> event for every trigger
- **Failure paths matter:** Most loops manifest during error handling, not happy paths
- **Defense in depth:** No single safeguard is sufficient; layer concurrency + idempotency + timeouts
- **Blast radius first:** Prioritize by impact (cost, data corruption) not just likelihood
- **Assume Lambdas fail:** Every Lambda will eventually error; does the error path loop?

## Common Mistakes to Avoid

- Checking only the happy path (most loops happen on error paths)
- Ignoring DynamoDB stream -> same-table-write patterns
- Assuming CloudFormation rejects all circular dependencies (it catches resource-level, not event-level)
- Setting Lambda timeout to 900s "just in case" (amplifies loop cost by 15x vs 60s timeout)
- Relying solely on concurrency limits (they throttle, not prevent)
- Forgetting that EventBridge scheduled rules fire regardless of previous execution status

## Related Skills

- `../infra-cloudwatch-investigation/` — If a loop is already happening, investigate via CloudWatch logs first, then use this skill to find the root cause and fix it
- `../infra-cdk-quality/` — CDK quality and security scanning (cfn-lint, Checkov, cdk-nag)
- `../dev-reviewing-code/` — Code review with Deep Scan mode for anti-pattern detection
