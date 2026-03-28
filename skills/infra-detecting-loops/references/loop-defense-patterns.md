# Loop Defense Patterns

This reference provides concrete implementation patterns for preventing infinite loops in AWS serverless architectures. Each pattern includes code examples, CDK configuration, and guidance on when to use it.

---

## 1. Flag Management Pattern

The most important defense against EventBridge schedule loops. Ensure the trigger condition is reliably changed on ALL code paths.

### Three-State Flag Pattern

Instead of a boolean `Needs Processing = True/False`, use three states:

| State | Meaning | Selected by Filter? |
|-------|---------|-------------------|
| `pending` | Ready for processing | YES |
| `processing` | Currently being handled | NO |
| `failed` | Failed after max retries | NO |

```python
# At start of processing
update_record(record_id, status="processing")

try:
    result = process(record)
    if result.is_valid:
        update_record(record_id, status="completed")
    else:
        update_record(record_id, status="failed", reason=result.error)
except Exception as e:
    retry_count = get_retry_count(record_id)
    if retry_count >= MAX_RETRIES:
        update_record(record_id, status="failed", reason=str(e))
    else:
        update_record(record_id, status="pending", retry_count=retry_count + 1)
```

### CDK Configuration (EventBridge + Lambda)

```python
from aws_cdk import (
    aws_events as events,
    aws_events_targets as targets,
    Duration,
)

# Schedule with appropriate interval
rule = events.Rule(
    self, "ProcessingSchedule",
    schedule=events.Schedule.rate(Duration.minutes(5)),
    description="Process pending items - Lambda clears 'pending' flag on all paths",
)

rule.add_target(targets.LambdaFunction(
    processing_lambda,
    retry_attempts=0,  # Do NOT retry at EventBridge level; Lambda handles its own retries
))
```

---

## 2. Concurrency Guard Pattern

Prevent multiple simultaneous executions of the same workflow.

### Step Function Execution Counter

```python
import boto3

sfn_client = boto3.client("stepfunctions")

def count_running_executions(state_machine_arn: str) -> int:
    """Count currently running executions of a state machine."""
    response = sfn_client.list_executions(
        stateMachineArn=state_machine_arn,
        statusFilter="RUNNING",
        maxResults=10,
    )
    return len(response["executions"])


def should_process(state_machine_arn: str, max_concurrent: int = 1) -> bool:
    """Check if we should start processing (no other executions running).

    IMPORTANT: Use > max_concurrent, not >= max_concurrent.
    The CURRENT execution counts as one, so if max_concurrent=1,
    we expect exactly 1 running (ourselves). Block only if > 1.
    """
    running = count_running_executions(state_machine_arn)
    if running > max_concurrent:
        logger.info(
            f"Skipping: {running} executions already running "
            f"(max concurrent: {max_concurrent})"
        )
        return False
    return True
```

### Lambda Concurrency Limits (CDK)

```python
from aws_cdk import aws_lambda as lambda_

processing_fn = lambda_.Function(
    self, "ProcessingFunction",
    # ...
    reserved_concurrent_executions=5,  # Hard limit on parallel invocations
)
```

**When to use:**
- `reserved_concurrent_executions=1` for singleton processing (one at a time)
- `reserved_concurrent_executions=5-10` for bounded parallelism
- Never leave unlimited for event-triggered Lambdas that write to shared state

---

## 3. Idempotency Pattern

Ensure that processing the same item multiple times produces the same result and does not create duplicate side effects.

### DynamoDB Conditional Write

```python
import time

def process_with_idempotency(item_id: str, data: dict) -> dict:
    """Process item only if not already processed."""
    try:
        # Atomic claim: only succeeds if not already claimed
        table.put_item(
            Item={
                "pk": f"PROCESSING#{item_id}",
                "claimed_at": int(time.time()),
                "ttl": int(time.time()) + 3600,  # Auto-expire after 1 hour
            },
            ConditionExpression="attribute_not_exists(pk)",
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.info(f"Item {item_id} already being processed, skipping")
        return {"status": "skipped", "reason": "duplicate"}

    try:
        result = do_actual_processing(data)
        return result
    except Exception:
        # On failure, remove the claim so item can be retried
        table.delete_item(Key={"pk": f"PROCESSING#{item_id}"})
        raise
```

### SQS Message Deduplication

```python
from aws_cdk import aws_sqs as sqs

# FIFO queue with content-based deduplication
queue = sqs.Queue(
    self, "ProcessingQueue",
    fifo=True,
    content_based_deduplication=True,
    deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
)
```

---

## 4. Circuit Breaker Pattern

Stop processing entirely when a systemic issue causes repeated failures.

### Execution Counter with DynamoDB

```python
def check_circuit_breaker(circuit_name: str, threshold: int = 10) -> bool:
    """Check if circuit breaker is tripped.

    Returns True if processing should continue, False if circuit is open.
    """
    response = table.get_item(Key={"pk": f"CIRCUIT#{circuit_name}"})
    item = response.get("Item", {})

    failure_count = item.get("failure_count", 0)
    last_reset = item.get("last_reset", 0)

    # Auto-reset after cooldown period (e.g., 30 minutes)
    if time.time() - last_reset > 1800:
        table.update_item(
            Key={"pk": f"CIRCUIT#{circuit_name}"},
            UpdateExpression="SET failure_count = :zero, last_reset = :now",
            ExpressionAttributeValues={":zero": 0, ":now": int(time.time())},
        )
        return True

    if failure_count >= threshold:
        logger.warning(
            f"Circuit breaker OPEN for {circuit_name}: "
            f"{failure_count} failures (threshold: {threshold})"
        )
        return False

    return True


def record_failure(circuit_name: str) -> None:
    """Increment failure counter."""
    table.update_item(
        Key={"pk": f"CIRCUIT#{circuit_name}"},
        UpdateExpression="ADD failure_count :one",
        ExpressionAttributeValues={":one": 1},
    )
```

---

## 5. Dead Letter Queue Pattern

Catch messages/events that fail repeatedly and route them to a DLQ for investigation instead of retrying forever.

### SQS DLQ (CDK)

```python
from aws_cdk import aws_sqs as sqs, Duration

dlq = sqs.Queue(
    self, "ProcessingDLQ",
    retention_period=Duration.days(14),
)

processing_queue = sqs.Queue(
    self, "ProcessingQueue",
    visibility_timeout=Duration.seconds(300),  # Must be > Lambda timeout
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,  # Send to DLQ after 3 failed attempts
        queue=dlq,
    ),
)
```

### Lambda DLQ (CDK)

```python
from aws_cdk import aws_lambda as lambda_, aws_sqs as sqs

dlq = sqs.Queue(self, "LambdaDLQ")

processing_fn = lambda_.Function(
    self, "ProcessingFunction",
    # ...
    dead_letter_queue=dlq,
    dead_letter_queue_enabled=True,
    retry_attempts=2,  # Retry twice, then send to DLQ
)
```

### Lambda Event Source Mapping DLQ

```python
from aws_cdk import aws_lambda_event_sources as sources

processing_fn.add_event_source(sources.SqsEventSource(
    queue,
    batch_size=1,
    max_batching_window=Duration.seconds(0),
    report_batch_item_failures=True,  # Partial batch failure support
))
```

---

## 6. Timeout Layering Pattern

Set timeouts at every level to prevent stuck resources from accumulating.

### Recommended Timeout Hierarchy

```python
from aws_cdk import Duration

# Level 1: Lambda timeout (innermost)
processing_fn = lambda_.Function(
    self, "ProcessingFunction",
    timeout=Duration.seconds(120),  # 2 minutes
)

# Level 2: Step Function task timeout
# In ASL JSON:
# "TimeoutSeconds": 180  (Lambda timeout + buffer)

# Level 3: Step Function execution timeout
# In ASL JSON at top level:
# "TimeoutSeconds": 3600  (1 hour max for entire workflow)

# Level 4: EventBridge rule disable on alarm
alarm = cloudwatch.Alarm(
    self, "ExecutionTimeAlarm",
    metric=state_machine.metric_execution_time(),
    threshold=3600000,  # 1 hour in milliseconds
    evaluation_periods=1,
)
# Manual step: Alarm triggers SNS -> human disables rule
```

### Timeout Sizing Rules

| Component | Timeout | Reasoning |
|-----------|---------|-----------|
| Lambda | T | Base processing time |
| SFN Task | T + 60s | Lambda timeout + SFN overhead |
| SFN Execution | N * (T + 60s) * 2 | All tasks * 2x safety margin |
| SQS Visibility | T + 30s | Lambda timeout + SQS overhead |
| API Gateway | 29s max | Hard API Gateway limit |

---

## 7. EventBridge Rule Disable Pattern

Automatically disable an EventBridge rule when repeated failures are detected.

### CloudWatch Alarm + Lambda (CDK)

```python
from aws_cdk import aws_cloudwatch as cw, aws_cloudwatch_actions as cw_actions

# Monitor Lambda errors
error_alarm = cw.Alarm(
    self, "ProcessingErrorAlarm",
    metric=processing_fn.metric_errors(),
    threshold=10,
    evaluation_periods=2,
    datapoints_to_alarm=2,
    alarm_description="Disable EventBridge rule if Lambda errors spike",
)

# Action: Invoke a "circuit breaker" Lambda that disables the rule
error_alarm.add_alarm_action(
    cw_actions.LambdaAction(circuit_breaker_fn)
)
```

Circuit breaker Lambda:

```python
import boto3

events_client = boto3.client("events")

def handler(event, context):
    """Disable the processing rule when alarm fires."""
    events_client.disable_rule(
        Name="ProcessingSchedule",
        EventBusName="default",
    )
    # Notify team via SNS/Slack
    notify_team("Processing rule disabled due to repeated failures")
```

---

## 8. DynamoDB Stream Filtering Pattern

Prevent DynamoDB stream -> same table write loops.

### CDK Event Source Filter

```python
from aws_cdk import aws_lambda_event_sources as sources

processing_fn.add_event_source(sources.DynamoEventSource(
    table,
    starting_position=lambda_.StartingPosition.LATEST,
    batch_size=10,
    retry_attempts=2,
    filters=[
        lambda_.FilterCriteria.filter({
            "eventName": lambda_.FilterRule.is_equal("INSERT"),
            # OR filter by specific attribute changes:
            "dynamodb": {
                "NewImage": {
                    "status": {
                        "S": lambda_.FilterRule.is_equal("pending")
                    }
                }
            }
        })
    ],
))
```

---

## Defense Selection Guide

| Scenario | Primary Defense | Secondary Defense |
|----------|----------------|-------------------|
| EventBridge schedule -> Lambda | Three-state flag | Concurrency guard + circuit breaker |
| DynamoDB stream -> same table | Event source filter | Processed marker attribute |
| S3 event -> same bucket | Prefix filtering | Separate output bucket |
| SQS -> Lambda -> same queue | DLQ + max receive count | Idempotency key |
| SNS circular subscription | Separate output topic | Hop counter |
| SFN retry storms | MaxAttempts + Catch | Execution timeout |
| SFN Choice cycles | Counter variable + exit condition | Execution timeout |
| Lambda self-invocation | Concurrency limit | DLQ + timeout |

---

## Pre-Deployment Checklist

For every event-driven component, verify:

- [ ] Trigger condition is cleared on ALL code paths (success, failure, timeout)
- [ ] Concurrency guard prevents parallel execution storms
- [ ] Retry has MaxAttempts and exponential backoff
- [ ] DLQ configured for failed messages/invocations
- [ ] Timeouts set at Lambda, SFN task, and SFN execution levels
- [ ] Idempotency handling prevents duplicate processing
- [ ] Circuit breaker stops processing during systemic failures
- [ ] CloudWatch alarms monitor for invocation/error spikes
