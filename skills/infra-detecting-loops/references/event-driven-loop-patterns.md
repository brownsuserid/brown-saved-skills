# Event-Driven Loop Patterns

This reference catalogs common infinite loop patterns in AWS event-driven architectures. Each pattern includes the trigger chain, detection method, real-world example, and recommended fix.

---

## Pattern A: EventBridge Schedule -> Lambda -> Unchanged Entry Condition

**The most common serverless loop pattern.** A scheduled EventBridge rule fires periodically. The target Lambda filters records needing processing but does NOT clear the filter condition on failure (or at all). Every scheduled invocation re-processes the same records.

### Trigger Chain

```
EventBridge Rule (rate: 5 min)
  -> Lambda: filter_items (reads "Needs Processing" = True)
    -> For each item: invoke processing
      -> If processing FAILS: flag is NOT cleared
        -> Next schedule tick: same items re-selected
          -> LOOP
```

### Detection

```bash
# Find scheduled EventBridge rules
rg "Schedule\.(rate|expression|cron)" --type py --type ts -A 10

# For each target Lambda, check:
# 1. What filter condition does it use?
rg "filter.*formula\|FilterExpression\|query.*where" --type py

# 2. Does it clear the condition on SUCCESS?
rg "update.*Needs.*False\|flag.*=.*False\|processed.*=.*True" --type py

# 3. Does it clear the condition on FAILURE? (Most miss this)
rg "except.*:.*update\|finally.*:.*update\|error.*handler.*clear" --type py
```

### Real-World Example: BB-GTM Outreach Planner

- EventBridge fires every 5 minutes
- Lambda queries deals with `Needs Outreach Plan Update = True`
- Brain processes each deal and creates tasks
- If validation fails (0 tasks created), the flag was STILL cleared
- Fix: Only clear `Needs Outreach Plan Update` when tasks_found > 0

### Recommended Fix

```python
# WRONG: Clear flag regardless of outcome
try:
    result = process_item(item)
finally:
    clear_processing_flag(item)  # Clears even on failure -> no loop, but loses data

# WRONG: Never clear flag on failure
try:
    result = process_item(item)
    clear_processing_flag(item)  # Only clears on success
except Exception:
    pass  # Flag stays True -> reprocessed forever

# CORRECT: Clear flag on success, mark as failed (different state) on failure
try:
    result = process_item(item)
    if result.is_valid:
        clear_processing_flag(item)
    else:
        mark_as_failed(item)  # Different state, not re-selected by filter
except Exception:
    increment_retry_count(item)
    if item.retry_count >= MAX_RETRIES:
        mark_as_failed(item)
```

---

## Pattern B: DynamoDB Stream -> Lambda -> Same Table Write

A Lambda triggered by DynamoDB Streams writes back to the same table, generating a new stream event that triggers itself again.

### Trigger Chain

```
DynamoDB Table (Stream enabled)
  -> Lambda (stream event)
    -> Processes record
      -> Writes result BACK to same table
        -> New stream event generated
          -> Lambda triggered again
            -> LOOP
```

### Detection

```bash
# Find DynamoDB stream sources
rg "DynamoEventSource\|dynamodb.*stream\|event_source_mapping.*dynamodb" --type py --type ts

# Find the target Lambda's table writes
# Compare source table name with destination table name
rg "put_item\|update_item\|batch_write" --type py --type ts
```

### Recommended Fix

```python
# Option 1: Write to a DIFFERENT table
output_table.put_item(Item=result)  # Not the source table

# Option 2: Filter stream events by change type
def handler(event, context):
    for record in event["Records"]:
        # Only process INSERT events, ignore MODIFY from our own writes
        if record["eventName"] == "INSERT":
            process(record)

# Option 3: Use a "processed" attribute to skip self-writes
def handler(event, context):
    for record in event["Records"]:
        new_image = record["dynamodb"]["NewImage"]
        if new_image.get("_processed_by_stream", {}).get("BOOL", False):
            continue  # Skip records we wrote
        process(record)
        # When writing back, set the marker
        table.update_item(
            Key={"id": record_id},
            UpdateExpression="SET _processed_by_stream = :t",
            ExpressionAttributeValues={":t": True}
        )
```

---

## Pattern C: S3 Event -> Lambda -> Same Bucket Write

A Lambda triggered by S3 PutObject writes an output file to the same bucket, triggering itself again.

### Trigger Chain

```
S3 Bucket (PutObject notification)
  -> Lambda: process_upload
    -> Processes file
      -> Writes output to SAME bucket
        -> PutObject event fires
          -> Lambda triggered again
            -> LOOP (exponential: each invocation creates more files)
```

### Detection

```bash
# Find S3 event notifications
rg "s3.*add_event_notification\|S3EventSource\|NotificationConfiguration" --type py --type ts

# Find S3 writes in the handler
rg "put_object\|upload_file\|s3.*write" --type py --type ts

# Compare source bucket with destination bucket
```

### Recommended Fix

```python
# Option 1: Use separate input/output buckets (BEST)
output_bucket.put_object(Key=output_key, Body=result)

# Option 2: Use prefix filtering
# Trigger only on "uploads/" prefix, write to "processed/" prefix
s3_event_source = S3EventSource(
    bucket,
    events=[s3.EventType.OBJECT_CREATED],
    filters=[s3.NotificationKeyFilter(prefix="uploads/")]
)
# Lambda writes to "processed/" prefix -> no re-trigger

# Option 3: Check file prefix in handler
def handler(event, context):
    key = event["Records"][0]["s3"]["object"]["key"]
    if key.startswith("processed/"):
        return  # Skip our own outputs
```

### AWS Documentation Warning

AWS explicitly warns about this pattern. S3 event notifications to the same bucket can cause cascading invocations. Always use prefix/suffix filters or separate buckets.

---

## Pattern D: SNS/SQS Circular Subscription

Lambda publishes to an SNS topic that has an SQS queue subscribed, which triggers the same (or another) Lambda that publishes back to the same topic.

### Trigger Chain

```
SNS Topic A
  -> SQS Queue
    -> Lambda
      -> Publishes to SNS Topic A
        -> LOOP
```

### Detection

```bash
# Find SNS publish calls
rg "sns.*publish\|TopicArn.*publish" --type py --type ts

# Find SQS -> Lambda triggers
rg "SqsEventSource\|event_source_mapping.*sqs" --type py --type ts

# Cross-reference: Does the Lambda's publish target match any topic
# that eventually triggers this Lambda?
```

### Recommended Fix

```python
# Option 1: Publish to a DIFFERENT topic for downstream consumers
response_topic.publish(Message=result)  # Not the source topic

# Option 2: Include a "hop count" in message attributes
def handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        hop_count = body.get("_hop_count", 0)
        if hop_count >= MAX_HOPS:
            logger.warning(f"Max hops reached, dropping message")
            return
        # Process and forward with incremented hop count
        body["_hop_count"] = hop_count + 1
        topic.publish(Message=json.dumps(body))
```

---

## Pattern E: API Gateway -> Lambda -> Self-Call via HTTP

Lambda makes an HTTP request that routes back to itself through API Gateway.

### Trigger Chain

```
API Gateway /process
  -> Lambda: process_handler
    -> Makes HTTP POST to same API Gateway /process
      -> Lambda invoked again
        -> LOOP
```

### Detection

```bash
# Find HTTP calls in Lambda handlers
rg "requests\.(get|post)|urllib3.*request|fetch\(" --type py --type ts

# Check if the URL matches the API Gateway endpoint
rg "execute-api.*amazonaws\|api\..*\.com" --type py --type ts
```

### Recommended Fix

This is almost always a design error. Use direct Lambda invocation or Step Functions for orchestration instead of HTTP self-calls.

---

## Pattern F: EventBridge Event Pattern -> Lambda -> Emits Same Event

Lambda emits a custom EventBridge event that matches the same rule that triggered it.

### Trigger Chain

```
EventBridge Rule (pattern: {"source": ["myapp"], "detail-type": ["OrderProcessed"]})
  -> Lambda: handle_order
    -> Processes order
      -> Emits event: {"source": "myapp", "detail-type": "OrderProcessed"}
        -> Rule matches again
          -> LOOP
```

### Detection

```bash
# Find EventBridge put_events calls
rg "put_events\|events.*put" --type py --type ts

# Compare Source and DetailType with the rule pattern
rg "EventPattern\|event_pattern" --type py --type ts
```

### Recommended Fix

```python
# Option 1: Use different detail-types for input vs output events
events_client.put_events(Entries=[{
    "Source": "myapp",
    "DetailType": "OrderCompleted",  # NOT "OrderProcessed"
    "Detail": json.dumps(result)
}])

# Option 2: Include processing marker in event detail
events_client.put_events(Entries=[{
    "Source": "myapp",
    "DetailType": "OrderProcessed",
    "Detail": json.dumps({**result, "_processed": True})
}])
# Rule pattern: {"detail": {"_processed": [{"exists": false}]}}
```

---

## Detection Priority Matrix

| Pattern | Frequency | Severity | Detection Difficulty |
|---------|-----------|----------|---------------------|
| A: Schedule + unchanged flag | Very Common | HIGH | Easy |
| B: DynamoDB stream + same table | Common | CRITICAL | Medium |
| C: S3 event + same bucket | Common | CRITICAL | Easy |
| D: SNS/SQS circular | Uncommon | HIGH | Medium |
| E: API Gateway self-call | Rare | MEDIUM | Easy |
| F: EventBridge event re-match | Uncommon | HIGH | Hard |

---

## General Detection Strategy

1. **Build an event flow graph:** List every event source, Lambda target, and side effect
2. **For each Lambda side effect:** Does it create an event that could trigger this or an upstream Lambda?
3. **For each filter condition:** Is it reliably changed by the Lambda on ALL code paths (success, failure, timeout)?
4. **For each retry mechanism:** Is there a maximum retry count and dead letter destination?
5. **For each concurrency guard:** Does it prevent processing or just delay it?
